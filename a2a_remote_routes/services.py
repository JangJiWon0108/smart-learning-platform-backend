"""
Route 단위 A2A 원격 서비스 엔트리포인트.

이 모듈은 기존 import 경로를 깨지 않기 위해 남겨 둔 "재-export" 레이어입니다.
실제 구현은 아래 모듈로 분리되었습니다.
- `a2a_remote_routes.apps`: 앱 빌더 / 앱 인스턴스
- `a2a_remote_routes.cards`: AgentCard 구성
- `a2a_remote_routes.stream_bridge`: `/stream` SSE 브릿지
"""

from .apps import (  # noqa: F401
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
