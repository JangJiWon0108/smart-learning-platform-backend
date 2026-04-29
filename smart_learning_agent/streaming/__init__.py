from .frontend_events import iter_frontend_events

__all__ = ["iter_frontend_events"]

"""
프론트엔드 SSE 계약용 이벤트 변환(ADK Event -> frontend event dict).

이 패키지는 API 서버(`/chat/stream`)와 A2A route service(`/stream`)가 공통으로 사용하는
스트리밍 변환 로직을 제공합니다.
"""

from .frontend_events import (
    STREAM_NODES,
    build_curation_payload,
    build_tracer_payload,
    iter_frontend_events,
)

__all__ = [
    "STREAM_NODES",
    "iter_frontend_events",
    "build_curation_payload",
    "build_tracer_payload",
]

