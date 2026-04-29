"""
FastAPI 서버 진입점

프론트엔드 HTTP 요청 수신 및 에이전트 실행 응답 반환

실행 방법
  uv run uvicorn api.app:app --reload --app-dir .

엔드포인트 목록
  POST /chat/stream - SSE 스트리밍 (텍스트를 실시간으로 전송)
  GET  /health      - 서버 상태 확인
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import json
import logging
import traceback
import uuid
from typing import AsyncGenerator

import httpx
from config.properties import Settings
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from smart_learning_agent import runner
from smart_learning_agent.streaming import iter_frontend_events

# ─── 환경 설정 및 로거 구성 ───────────────────────────────────────────────────
log = logging.getLogger("api")
settings = Settings()

app = FastAPI(title="Smart Learning Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # ADK 래핑 quota 오류 시 클래스명이 Google·Vertex 패턴 아님 가능
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


def _route_service_url(route: str) -> str:
    """라우트명에 맞는 A2A route service stream URL을 반환합니다."""
    base_urls = {
        "solver": settings.SOLVER_A2A_URL,
        "recommendation": settings.RECOMMENDATION_A2A_URL,
        "visualization": settings.VISUALIZATION_A2A_URL,
        "other": settings.FALLBACK_A2A_URL,
    }
    return f"{base_urls[route].rstrip('/')}/stream"


# ─── API 엔드포인트 정의 ───────────────────────────────────────────────────────
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
        route_stream_completed = False

        try:
            content = await runner.prepare_routing_content(query, image, session_id)
            routing_events = runner.execute_routing_stream(session_id, content)

            async def routing_state():
                return await runner.get_routing_state(session_id)

            async for frontend_event in iter_frontend_events(
                routing_events,
                routing_state,
                emit_final=False,
            ):
                yield f"data: {json.dumps(frontend_event, ensure_ascii=False)}\n\n"

            state = await runner.get_routing_state(session_id)
            route = state.get("current_route")
            if route not in {"solver", "recommendation", "visualization", "other"}:
                raise ValueError(f"알 수 없는 라우트입니다: {route}")

            data = {
                "query": state.get("rewritten_query") or query,
                "session_id": session_id,
                "state": json.dumps(state, ensure_ascii=False),
            }
            files = None
            if image is not None:
                await image.seek(0)
                image_bytes = await image.read()
                if image_bytes:
                    files = {
                        "image": (
                            image.filename or "upload",
                            image_bytes,
                            image.content_type or "application/octet-stream",
                        )
                    }

            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    _route_service_url(route),
                    data=data,
                    files=files,
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if chunk:
                            yield chunk
            route_stream_completed = True
            return

        except Exception as exc:
            log.error("event_generator 예외 [%s]: %s\n%s", type(exc).__name__, exc, traceback.format_exc())
            error_msg = _classify_error(exc)
            # error 조건:
            # 준비·실행·최종 결과 단계 예외 시 사용자용 오류 메시지 SSE
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"

        finally:
            # done 조건:
            # 성공·실패 무관 전체 /chat/stream 요청 종료(done) 신호
            if not route_stream_completed:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """서버 헬스체크 엔드포인트"""
    return {"status": "ok"}
