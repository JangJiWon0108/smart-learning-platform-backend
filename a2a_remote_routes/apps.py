"""
Route 단위 A2A 원격 서비스 앱 빌더.

책임
- route별 ADK A2A 앱 생성(`to_a2a`)
- A2A discovery용 AgentCard 연결
- 프론트엔드 호환 `/stream` + `/health` 엔드포인트 추가
"""

from __future__ import annotations

from typing import Any

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from starlette.requests import Request
from starlette.responses import JSONResponse

from smart_learning_agent.runner.route_runner import get_route_agent, get_route_runner

from .cards import build_agent_card
from .stream_bridge import make_stream_endpoint


def build_route_app(route: str, host: str = "localhost", port: int = 0) -> Any:
    """
    route별 A2A 앱 인스턴스를 생성합니다.

    이 앱은 두 가지 사용자를 동시에 지원합니다.
    - A2A 표준 RPC: `to_a2a(...)`가 제공하는 엔드포인트
    - 프론트엔드 호환 스트리밍: `/stream` (multipart form) → `text/event-stream`(SSE)
    """
    # NOTE: route 유효성 검사는 cards.build_agent_card에서 한 번 더 체크합니다.
    agent = get_route_agent(route)
    agent_card = build_agent_card(route, host, port, agent)
    app = to_a2a(
        agent,
        host=host,
        port=port,
        agent_card=agent_card,
        runner=get_route_runner(route),
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "route": route})

    app.add_route("/stream", make_stream_endpoint(route), methods=["POST"])
    app.add_route("/health", health, methods=["GET"])
    return app


def build_solver_app() -> Any:
    """Solver route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8101)"""
    return build_route_app("solver", port=8101)


def build_recommendation_app() -> Any:
    """Recommendation route용 A2A ASGI 앱 생성. (AgentCard 포트: 8102)"""
    return build_route_app("recommendation", port=8102)


def build_visualization_app() -> Any:
    """Visualization route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8103)"""
    return build_route_app("visualization", port=8103)


def build_fallback_app() -> Any:
    """Fallback(other) route용 A2A 앱 인스턴스를 생성합니다. (AgentCard 포트: 8104)"""
    return build_route_app("other", port=8104)


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

