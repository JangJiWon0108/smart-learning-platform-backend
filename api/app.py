"""
FastAPI 서버 진입점.

클라이언트(프론트엔드)의 HTTP 요청을 받아서
스마트 학습 에이전트를 실행하고 응답을 반환합니다.

실행 방법:
  uv run uvicorn api.app:app --reload --app-dir .

엔드포인트:
  POST /chat        - 일반 요청/응답 (전체 결과를 한 번에 반환)
  POST /chat/stream - SSE 스트리밍 (텍스트를 실시간으로 전송)
  GET  /health      - 서버 상태 확인
"""

# ─── 임포트 ──────────────────────────────────────────────────────────────
import json
import logging
import traceback
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from smart_learning_agent import runner

# ─── 설정 및 로거 ────────────────────────────────────────────────────────
log = logging.getLogger("api")

# FastAPI 앱 객체 초기화
app = FastAPI(title="Smart Learning Platform API")

# CORS 설정: 개발 환경 대응 (모든 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 스트리밍 모드에서 텍스트를 실시간 전송할 에이전트 이름 목록
# 이 에이전트들의 출력만 청크(chunk) 이벤트로 스트리밍됩니다
_STREAM_NODES = {
    "solver_agent",
    "tracer_intro_agent",
    "curator_intro_agent",
    "fallback_agent",
}


# ─── 내부 헬퍼 함수 ──────────────────────────────────────────────────────
def _build_curation_payload(state: dict) -> dict | None:
    """state에서 문제 카드 목록을 추출하여 큐레이션 페이로드를 생성합니다."""
    # build_curation_callback이 problem_cards를 state에 미리 저장해둠
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


# ─── API 엔드포인트 ──────────────────────────────────────────────────────
@app.post("/chat")
async def chat(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
):
    """일반 채팅 엔드포인트 (비스트리밍)."""
    # 1단계: 유효성 검사 (텍스트 또는 이미지 중 하나는 필수)
    if not query.strip() and image is None:
        raise HTTPException(
            status_code=400,
            detail="query 또는 image 중 하나는 필수입니다.",
        )

    # 2단계: 요청용 고유 세션 ID 및 콘텐츠 준비
    session_id = str(uuid.uuid4())
    content = await runner.prepare_content(query, image, session_id)

    # 3단계: 에이전트 실행 및 결과 획득 (비스트리밍)
    response_text = None
    async for event in runner.execute_agent(session_id, content):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_text = part.text

    # 4단계: 최종 state 확인 및 응답 타입 결정 (큐레이션, 코드추적, 일반텍스트 순)
    state = await runner.get_session_state(session_id)

    # 4.1 추천 경로 확인
    curation = _build_curation_payload(state)
    if curation:
        return curation

    # 4.2 코드 추적 경로 확인
    if "tracer_output" in state:
        return {
            "type": "tracer",
            "route": state.get("current_route"),
            "data": state["tracer_output"],
        }

    # 4.3 일반 텍스트 응답
    return {
        "type": "text",
        "route": state.get("current_route"),
        "response": response_text or "응답을 생성하지 못했습니다.",
    }


@app.post("/chat/stream")
async def chat_stream(
    query: str = Form(default=""),
    image: UploadFile | None = File(default=None),
):
    """SSE(Server-Sent Events) 스트리밍 채팅 엔드포인트."""
    # 1단계: 유효성 검사
    if not query.strip() and image is None:
        raise HTTPException(
            status_code=400,
            detail="query 또는 image 중 하나는 필수입니다.",
        )

    # 2단계: 요청 준비
    session_id = str(uuid.uuid4())
    content = await runner.prepare_content(query, image, session_id)

    # 3단계: 스트리밍 이벤트 생성기 정의
    async def event_generator() -> AsyncGenerator[str, None]:
        emitted_nodes: set[str] = set()

        try:
            # 3.1 워크플로우 실행 및 이벤트 수신
            async for event in runner.execute_agent_stream(session_id, content):
                node_info = getattr(event, "node_info", None)
                node_name = getattr(node_info, "name", None) if node_info else None

                # 처리 노드 변경 시 state 이벤트 전송
                if node_name and node_name not in emitted_nodes:
                    emitted_nodes.add(node_name)
                    state_event = json.dumps({"type": "state", "node": node_name})
                    yield f"data: {state_event}\n\n"

                if not event.partial or not event.content:
                    continue

                # 허용된 노드의 텍스트 청크만 전송
                if node_name not in _STREAM_NODES:
                    continue

                for part in event.content.parts:
                    is_function_call = getattr(part, "function_call", None)
                    if part.text and not is_function_call:
                        chunk_event = json.dumps({"type": "chunk", "text": part.text})
                        yield f"data: {chunk_event}\n\n"

            # 4단계: 실행 완료 후 최종 결과(비정형 데이터) 전송
            state = await runner.get_session_state(session_id)

            # 4.1 추천 결과
            curation = _build_curation_payload(state)
            if curation:
                yield f"data: {json.dumps(curation, ensure_ascii=False)}\n\n"

            # 4.2 코드 추적 결과
            if "tracer_output" in state:
                tracer_event = {
                    "type": "tracer",
                    "route": state.get("current_route"),
                    "data": state["tracer_output"],
                }
                yield f"data: {json.dumps(tracer_event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            log.error("event_generator 예외: %s\n%s", exc, traceback.format_exc())
            error_event = json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

        finally:
            # 5단계: 완료 신호 전송
            done_event = json.dumps({"type": "done"})
            yield f"data: {done_event}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """서버 상태 확인 엔드포인트."""
    return {"status": "ok"}
