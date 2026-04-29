"""
Route 단위 A2A 원격 서비스 패키지.

외부에서는 기존대로 `a2a_remote_routes.services` 또는 본 패키지에서
`build_*_app`, `*_app`을 import할 수 있습니다.
"""

from .services import (  # noqa: F401
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
