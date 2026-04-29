"""
A2A route services 패키지.

route별 ASGI 앱 인스턴스는 `a2a_remote_routes.services`에서 생성합니다.
"""

from .services import (  # noqa: F401
    fallback_app,
    recommendation_app,
    solver_app,
    visualization_app,
)

__all__ = [
    "solver_app",
    "recommendation_app",
    "visualization_app",
    "fallback_app",
]

"""
Route 단위 A2A 원격 서비스 패키지.

각 route workflow를 Google ADK A2A 앱으로 노출하는 엔트리포인트를 제공합니다.
"""

from .services import (
    build_fallback_app,
    build_recommendation_app,
    build_route_app,
    build_solver_app,
    build_visualization_app,
    fallback_app,
    recommendation_app,
    solver_app,
    visualization_app,
)

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
