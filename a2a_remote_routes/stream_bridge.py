"""
프론트엔드 호환 `/stream` SSE 브릿지.

책임
- multipart/form-data 입력 파싱(query, session_id, state, image)
- route_runner 스트리밍 이벤트를 `iter_frontend_events`로 프론트 이벤트로 변환
- 프론트 포맷 SSE(`text/event-stream`)로 출력
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
import json
import logging
import time
import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import StreamingResponse

from smart_learning_agent.runner.route_runner import (
    execute_route_stream,
    get_route_state,
    prepare_route_content,
)
from smart_learning_agent.streaming import iter_frontend_events

USER_ID = "route_service_user"
log = logging.getLogger(__name__)

# state 이벤트에서 LLM 노드 카운팅 시 제외할 workflow 루트들
_EXCLUDED_LLM_NODES = {
    "recommendation_route_workflow",
    "solver_route_workflow",
    "visualization_route_workflow",
    "fallback_route_workflow",
}


@dataclass(frozen=True)
class StreamRequest:
    """
    `/stream`에서 받는 입력을 파이썬 타입으로 정리한 값.

    초보 입장에서 request.form() 결과는 타입이 섞여 읽기 어려워서,
    한 번 여기로 모아두고 아래 로직은 "정리된 값"만 보도록 합니다.
    """

    query: str
    session_id: str
    state: dict[str, Any]
    image_bytes: bytes | None
    image_mime_type: str | None


def _error_message(exc: Exception) -> str:
    """사용자 노출용 에러 메시지 생성."""
    msg = str(exc).strip()
    if "timeout" in type(exc).__name__.lower() or "timeout" in msg.lower():
        return "응답 시간이 초과되었습니다 (60초). 잠시 후 다시 시도해 주세요."
    if (
        "RESOURCE_EXHAUSTED" in msg
        or "429" in msg
        or "Too Many Requests" in msg
        or "Resource exhausted" in msg
    ):
        return "AI 서비스 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
    return msg if msg else f"오류가 발생했습니다 ({type(exc).__name__})."


def _parse_state(raw_state: Any) -> dict[str, Any]:
    """폼 입력의 `state`를 dict로 파싱."""
    if raw_state is None:
        return {}
    if isinstance(raw_state, str) and raw_state.strip():
        # 프론트/호출자 오류로 state가 깨졌을 때 전체 스트림이 죽지 않도록 안전하게 처리합니다.
        try:
            parsed = json.loads(raw_state)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def _read_image(image: Any) -> tuple[bytes | None, str | None]:
    """폼 입력의 이미지 파일을 bytes로 로드."""
    if image is None or not hasattr(image, "read"):
        return None, None
    image_bytes = await image.read()
    if not image_bytes:
        return None, None
    return image_bytes, getattr(image, "content_type", None)


def _sse_data(payload: dict[str, Any]) -> str:
    """SSE `data:` 프레임 문자열 생성."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _parse_stream_request(request: Request) -> StreamRequest:
    """multipart form 입력을 읽어 StreamRequest로 정규화."""
    form = await request.form()

    query = str(form.get("query") or "")
    session_id = str(form.get("session_id") or uuid.uuid4())
    state = _parse_state(form.get("state"))
    image_bytes, image_mime_type = await _read_image(form.get("image"))

    return StreamRequest(
        query=query,
        session_id=session_id,
        state=state,
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
    )


def make_stream_endpoint(route: str) -> Callable[[Request], Awaitable[StreamingResponse]]:
    """
    route별 `/stream` SSE 엔드포인트 핸들러를 생성합니다.

    Args:
        route: `solver` | `recommendation` | `visualization` | `other`
    """

    async def stream(request: Request) -> StreamingResponse:
        req = await _parse_stream_request(request)

        async def event_generator() -> AsyncGenerator[str, None]:
            started = time.monotonic()
            last_node: str | None = None
            llm_node_count = 0
            try:
                content = await prepare_route_content(
                    route=route,
                    session_id=req.session_id,
                    user_id=USER_ID,
                    query=req.query,
                    state=req.state,
                    image_bytes=req.image_bytes,
                    image_mime_type=req.image_mime_type,
                )
                events = execute_route_stream(route, req.session_id, USER_ID, content)

                async def current_state() -> dict[str, Any]:
                    return await get_route_state(route, req.session_id, USER_ID)

                async for frontend_event in iter_frontend_events(events, current_state):
                    if frontend_event.get("type") == "state":
                        node = str(frontend_event.get("node") or "")
                        if node:
                            last_node = node
                            if node.endswith("_agent") or node.endswith("_workflow"):
                                # 대략적인 LLM 호출 횟수를 보기 위한 보조 지표입니다.
                                if node not in _EXCLUDED_LLM_NODES:
                                    llm_node_count += 1
                    yield _sse_data(frontend_event)
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                log.exception(
                    "A2A route stream failed: route=%s session_id=%s last_node=%s llm_nodes=%s elapsed_ms=%s",
                    route,
                    req.session_id,
                    last_node,
                    llm_node_count,
                    elapsed_ms,
                )
                yield _sse_data({"type": "error", "message": _error_message(exc)})
            finally:
                yield _sse_data({"type": "done"})

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return stream

