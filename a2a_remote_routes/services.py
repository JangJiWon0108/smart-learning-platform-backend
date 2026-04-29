"""
Route 단위 A2A 원격 서비스 엔트리포인트.

각 route는 Google ADK A2A 앱으로 노출되며, 기존 프론트 SSE UX 보존을 위해
동일 앱에 `/stream` bridge도 함께 제공합니다.

주요 책임.
- AgentCard(discovery) 구성 및 A2A 앱 생성
- 프론트엔드 호환 `/stream` 엔드포인트 제공(멀티파트 폼 입력 → SSE 출력)
- route 실행기(`smart_learning_agent.runner.route_runner`) 스트리밍 이벤트를 프론트 이벤트로 변환
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import AsyncGenerator
import json
import logging
import time
import uuid
from typing import Any

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from smart_learning_agent.runner.route_runner import (
    execute_route_stream,
    get_route_agent,
    get_route_runner,
    get_route_state,
    prepare_route_content,
)
from smart_learning_agent.streaming import iter_frontend_events

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
USER_ID = "route_service_user"
log = logging.getLogger(__name__)

_ROUTE_DESCRIPTIONS = {
    "solver": "정보처리기사 실기 문제 풀이와 개념 설명 route",
    "recommendation": "정보처리기사 실기 유사 문제 추천 route",
    "visualization": "코드 실행 흐름 시각화 route",
    "other": "지원 범위 밖 질문 안내 route",
}


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _error_message(exc: Exception) -> str:
    """사용자 노출용 에러 메시지 생성."""
    msg = str(exc).strip()
    if "timeout" in type(exc).__name__.lower() or "timeout" in msg.lower():
        return "응답 시간이 초과되었습니다 (60초). 잠시 후 다시 시도해 주세요."
    # Google ADK/Gemini/Vertex: 429 RESOURCE_EXHAUSTED (rate/quota exceeded)
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
        parsed = json.loads(raw_state)
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


def _build_agent_card(route: str, host: str, port: int, agent: Any) -> AgentCard:
    """A2A discovery용 AgentCard 구성."""
    rpc_url = f"http://{host}:{port}/" if port else f"http://{host}/"
    return AgentCard(
        name=agent.name,
        description=_ROUTE_DESCRIPTIONS[route],
        url=rpc_url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id=f"{route}_route",
                name=f"{route} route",
                description=_ROUTE_DESCRIPTIONS[route],
                tags=["smart-learning", route],
            )
        ],
    )


# ─── A2A 앱 빌더 ───────────────────────────────────────────────────────────
def build_route_app(route: str, host: str = "localhost", port: int = 0) -> Any:
    """
    route별 A2A 앱 인스턴스를 생성합니다.

    이 앱은 두 가지 사용자를 동시에 지원합니다.
    - A2A 표준 RPC: `to_a2a(...)`가 제공하는 엔드포인트
    - 프론트엔드 호환 스트리밍: `/stream` (multipart form) → `text/event-stream`(SSE)

    Args:
        route: `solver` | `recommendation` | `visualization` | `other`
        host: AgentCard URL 구성에 사용할 호스트
        port: AgentCard URL 구성에 사용할 포트(0이면 생략)

    Returns:
        Starlette 라우트를 포함하는 A2A ASGI 앱
    """
    agent = get_route_agent(route)
    agent_card = _build_agent_card(route, host, port, agent)
    app = to_a2a(
        agent,
        host=host,
        port=port,
        agent_card=agent_card,
        runner=get_route_runner(route),
    )

    async def stream(request: Request) -> StreamingResponse:
        """
        프론트엔드 호환 SSE 브릿지 엔드포인트.

        입력은 `multipart/form-data`를 사용합니다.
        - `query`: 사용자 질문(문자열)
        - `session_id`: 세션 식별자(없으면 서버에서 생성)
        - `state`: JSON 문자열(dict만 허용)
        - `image`: 업로드 이미지 파일(선택)

        출력은 프론트 이벤트 포맷의 SSE 스트림입니다.
        """
        form = await request.form()
        query = str(form.get("query") or "")
        session_id = str(form.get("session_id") or uuid.uuid4())
        state = _parse_state(form.get("state"))
        image_bytes, image_mime_type = await _read_image(form.get("image"))

        async def event_generator() -> AsyncGenerator[str, None]:
            started = time.monotonic()
            last_node: str | None = None
            llm_node_count = 0
            try:
                content = await prepare_route_content(
                    route=route,
                    session_id=session_id,
                    user_id=USER_ID,
                    query=query,
                    state=state,
                    image_bytes=image_bytes,
                    image_mime_type=image_mime_type,
                )
                events = execute_route_stream(route, session_id, USER_ID, content)

                async def current_state() -> dict[str, Any]:
                    return await get_route_state(route, session_id, USER_ID)

                async for frontend_event in iter_frontend_events(events, current_state):
                    # state 이벤트: 노드명·대략적 LLM 호출 횟수 계측
                    if frontend_event.get("type") == "state":
                        node = str(frontend_event.get("node") or "")
                        if node:
                            last_node = node
                            if node.endswith("_agent") or node.endswith("_workflow"):
                                # workflow 루트 제외, agent 단위만 LLM 호출 근사치로 카운트
                                excluded = {
                                    "recommendation_route_workflow",
                                    "solver_route_workflow",
                                    "visualization_route_workflow",
                                    "fallback_route_workflow",
                                }
                                if node not in excluded:
                                    llm_node_count += 1
                    yield _sse_data(frontend_event)
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                log.exception(
                    "A2A route stream failed: route=%s session_id=%s last_node=%s llm_nodes=%s elapsed_ms=%s",
                    route,
                    session_id,
                    last_node,
                    llm_node_count,
                    elapsed_ms,
                )
                yield _sse_data({"type": "error", "message": _error_message(exc)})
            finally:
                yield _sse_data({"type": "done"})

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    async def health(_: Request) -> JSONResponse:
        """헬스체크 엔드포인트."""
        return JSONResponse({"status": "ok", "route": route})

    app.add_route("/stream", stream, methods=["POST"])
    app.add_route("/health", health, methods=["GET"])
    return app


def build_solver_app() -> Any:
    """Solver route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8101)"""
    return build_route_app("solver", port=8101)


def build_recommendation_app() -> Any:
    """
    Recommendation route용 A2A ASGI 앱 생성.

    Returns:
        유사 문제 추천 workflow(MCP 검색 포함)가 연결된 앱. AgentCard 포트 8102.
    """
    return build_route_app("recommendation", port=8102)


def build_visualization_app() -> Any:
    """Visualization route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8103)"""
    return build_route_app("visualization", port=8103)


def build_fallback_app() -> Any:
    """Fallback(other) route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8104)"""
    return build_route_app("other", port=8104)


# ─── 앱 인스턴스 ───────────────────────────────────────────────────────────
solver_app = build_solver_app()
recommendation_app = build_recommendation_app()
visualization_app = build_visualization_app()
fallback_app = build_fallback_app()

__all__ = [
    "build_route_app",
    "build_solver_app",
    "build_recommendation_app",
    "build_visualization_app",
    "build_fallback_app",
    "solver_app",
    "recommendation_app",
    "visualization_app",
    "fallback_app",
]
