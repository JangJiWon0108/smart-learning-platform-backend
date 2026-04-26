"""
FastAPI 서버 진입점

프론트엔드 HTTP 요청 수신 및 에이전트 실행 응답 반환

실행 방법
  uv run uvicorn api.app:app --reload --app-dir .

엔드포인트 목록
  POST /chat        - 일반 요청/응답 (전체 결과를 한 번에 반환)
  POST /chat/stream - SSE 스트리밍 (텍스트를 실시간으로 전송)
  GET  /health      - 서버 상태 확인
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import json
import logging
import traceback
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from smart_learning_agent import runner

# ─── 환경 설정 및 로거 구성 ───────────────────────────────────────────────────
log = logging.getLogger("api")

app = FastAPI(title="Smart Learning Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 실시간 스트리밍 대상 에이전트 목록
_STREAM_NODES = {
    "solver_agent",
    "fallback_agent",
    "curator_intro_agent",
    "tracer_intro_agent",
}


# ─── 내부 유틸리티 함수 ───────────────────────────────────────────────────────
def _classify_error(exc: Exception) -> str:
    """예외 종류에 따라 사용자 친화적인 오류 메시지를 반환합니다."""
    cls = type(exc).__name__
    msg = str(exc).strip()

    # FastAPI HTTPException (이미지 형식 오류 등)
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return detail if isinstance(detail, str) else str(detail)

    # 타임아웃
    if isinstance(exc, TimeoutError) or "timeout" in cls.lower() or "timeout" in msg.lower():
        return "응답 시간이 초과되었습니다 (60초). 잠시 후 다시 시도해 주세요."

    # 네트워크 / 연결 오류
    if isinstance(exc, (ConnectionError, OSError)) or "connection" in cls.lower():
        return "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인하고 다시 시도해 주세요."

    # ADK가 래핑한 quota 오류는 Google/Vertex 클래스명이 아닐 수 있습니다.
    if "quota" in msg.lower() or "resource_exhausted" in msg.lower() or "429" in msg:
        return "AI 서비스 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."

    # Google / Vertex AI API 오류
    if any(k in cls for k in ("Google", "Vertex", "ApiCore", "ClientError", "ServerError")):
        if "quota" in msg.lower() or "429" in msg:
            return "AI 서비스 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
        if "permission" in msg.lower() or "403" in msg:
            return "AI 서비스 인증에 문제가 있습니다. 서버 설정을 확인해 주세요."
        if "not found" in msg.lower() or "404" in msg:
            return "요청한 AI 모델을 찾을 수 없습니다. 모델 설정을 확인해 주세요."
        if "unavailable" in msg.lower() or "503" in msg:
            return "AI 서비스가 일시적으로 이용 불가 상태입니다. 잠시 후 다시 시도해 주세요."
        return f"AI 서비스 오류: {msg}" if msg else "AI 서비스 오류가 발생했습니다."

    # 잘못된 입력값
    if isinstance(exc, (ValueError, TypeError)):
        return f"잘못된 요청입니다: {msg}" if msg else "잘못된 요청 형식입니다."

    # 기타 — 메시지가 있으면 그대로, 없으면 클래스명 포함
    return msg if msg else f"오류가 발생했습니다 ({cls})."


def _build_curation_payload(state: dict) -> dict | None:
    """상태 정보 기반 큐레이션 페이로드 생성"""
    problem_cards = state.get("problem_cards")
    if problem_cards is None:
        return None

    return {
        "type": "curation",
        "route": state.get("current_route"),
        "title": "맞춤 추천 문제 카드",
        "problemCards": problem_cards,
        "message": None if problem_cards else "지금 조건에 맞는 추천 문제가 없어요.",
    }


# ─── API 엔드포인트 정의 ───────────────────────────────────────────────────────
@app.post("/chat")
async def chat(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
    session_id: str = Form(default=""),
):
    """일반 채팅 엔드포인트 (비스트리밍 방식)"""
    if not query.strip() and image is None:
        raise HTTPException(
            status_code=400,
            detail="query 또는 image 중 하나는 필수입니다.",
        )

    session_id = session_id.strip() or str(uuid.uuid4())
    content = await runner.prepare_content(query, image, session_id)

    response_text = None
    async for event in runner.execute_agent(session_id, content):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_text = part.text

    state = await runner.get_session_state(session_id)

    curation = _build_curation_payload(state)
    if curation:
        return curation

    tracer_output = state.get("tracer_output")
    if isinstance(tracer_output, dict) and tracer_output.get("steps"):
        return {
            "type": "tracer",
            "route": state.get("current_route"),
            "data": tracer_output,
        }

    return {
        "type": "text",
        "route": state.get("current_route"),
        "response": response_text or "응답을 생성하지 못했습니다.",
    }


@app.post("/chat/stream")
async def chat_stream(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
    session_id: str = Form(default=""),
):
    """SSE(Server-Sent Events) 기반 스트리밍 채팅 엔드포인트"""
    if not query.strip() and image is None:
        raise HTTPException(
            status_code=400,
            detail="query 또는 image 중 하나는 필수입니다.",
        )

    session_id = session_id.strip() or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        emitted_nodes: set[str] = set()
        streamed_text_nodes: set[str] = set()
        streaming_node: str | None = None

        try:
            # prepare_content도 try 안에서 실행해 모든 초기화 오류를 SSE error로 전달
            content = await runner.prepare_content(query, image, session_id)

            prev_node: str | None = None
            async for event in runner.execute_agent_stream(session_id, content):
                node_info = getattr(event, "node_info", None)
                node_name = getattr(node_info, "name", None) if node_info else None
                is_stream_node = node_name in _STREAM_NODES if node_name else False

                # 스트리밍 노드에서 다른 노드로 전환될 때 stream_end 신호 전송
                if (
                    prev_node is not None
                    and streaming_node is not None
                    and node_name != prev_node
                    and streaming_node == prev_node
                ):
                    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                    streaming_node = None
                prev_node = node_name

                if node_name and node_name not in emitted_nodes:
                    emitted_nodes.add(node_name)
                    yield f"data: {json.dumps({'type': 'state', 'node': node_name})}\n\n"

                if is_stream_node and event.content:
                    for part in event.content.parts:
                        if part.text and not getattr(part, "function_call", None):
                            # ADK는 partial 조각 이후 같은 노드의 최종 완성본을 다시 보낼 수 있습니다.
                            # partial을 이미 보낸 노드라면 최종 완성본은 중복 전송하지 않습니다.
                            if event.partial:
                                streaming_node = node_name
                                streamed_text_nodes.add(node_name)
                                yield f"data: {json.dumps({'type': 'chunk', 'text': part.text})}\n\n"
                            elif node_name not in streamed_text_nodes:
                                streaming_node = node_name
                                streamed_text_nodes.add(node_name)
                                yield f"data: {json.dumps({'type': 'chunk', 'text': part.text})}\n\n"

                # partial=False 종료 이벤트가 들어오면 즉시 stream_end 전송
                # (다음 노드 이벤트를 기다리지 않게 해서 프론트 대기 말풍선 지연 제거)
                if is_stream_node and streaming_node == node_name and not event.partial:
                    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                    streaming_node = None

            # 스트림 노드 종료 이벤트가 누락된 경우 방어적으로 마무리 신호 전송
            if streaming_node is not None:
                yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                streaming_node = None

            # 정상 완료 시 최종 데이터 전송
            state = await runner.get_session_state(session_id)

            curation = _build_curation_payload(state)
            if curation:
                yield f"data: {json.dumps(curation, ensure_ascii=False)}\n\n"

            tracer_output = state.get("tracer_output")
            if isinstance(tracer_output, dict) and tracer_output.get("steps"):
                yield f"data: {json.dumps({'type': 'tracer', 'route': state.get('current_route'), 'data': tracer_output}, ensure_ascii=False)}\n\n"
            elif state.get("current_route") == "visualization":
                yield f"data: {json.dumps({'type': 'error', 'message': '코드 실행 흐름 분석에 실패했습니다. 다시 시도해 주세요.'}, ensure_ascii=False)}\n\n"

        except Exception as exc:
            log.error("event_generator 예외 [%s]: %s\n%s", type(exc).__name__, exc, traceback.format_exc())
            error_msg = _classify_error(exc)
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"

        finally:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """서버 헬스체크 엔드포인트"""
    return {"status": "ok"}
