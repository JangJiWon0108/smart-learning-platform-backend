"""
Route 단위 ADK Workflow 실행기.

A2A route 서비스는 메인 오케스트레이터가 넘긴 state를 세션에 주입한 뒤
기존 route workflow를 실행합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps.app import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from smart_learning_agent.agent import (
    fallback_route_agent,
    recommendation_route_agent,
    solver_route_agent,
    visualization_route_agent,
)
from smart_learning_agent.artifacts import save_image_artifact

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# LLM·MCP 포함 route 동시 실행 상한(429 완화). 설정 승격 가능
_ROUTE_CONCURRENCY_LIMITS: dict[str, int] = {
    "solver": 2,
    "recommendation": 1,
    "visualization": 1,
    "other": 4,
}

# route별 ADK max_llm_calls. recommendation은 필터·검색·소개·정제·재시도로 호출 다수
_MAX_LLM_CALLS_BY_ROUTE: dict[str, int] = {
    "solver": 15,
    "recommendation": 30,
    "visualization": 20,
    "other": 10,
}

_ROUTE_SEMAPHORES: dict[str, asyncio.Semaphore] = {
    route: asyncio.Semaphore(limit) for route, limit in _ROUTE_CONCURRENCY_LIMITS.items()
}

_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT_SESSIONS: set[tuple[str, str]] = set()  # (route, session_id)


# ─── 런타임 구성 ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RouteRuntime:
    """Route workflow와 InMemoryRunner 1:1 묶음."""

    route: str
    runner: InMemoryRunner


_ROUTE_AGENTS = {
    "solver": solver_route_agent,
    "recommendation": recommendation_route_agent,
    "visualization": visualization_route_agent,
    "other": fallback_route_agent,
}

_ROUTE_RUNTIMES = {
    route: RouteRuntime(
        route=route,
        runner=InMemoryRunner(
            app=App(
                name=agent.name,
                root_agent=agent,
            )
        ),
    )
    for route, agent in _ROUTE_AGENTS.items()
}

_ROUTE_STATE_KEYS = {
    "solver": {"solver_query", "solver_output"},
    "recommendation": {
        "vertex_filter_output",
        "rec_search_results",
        "rec_query",
        "rec_subject",
        "rec_filter_expression",
        "curator_intro",
        "curator_output",
        "refine_output",
        "problem_cards",
    },
    "visualization": {
        "tracer_input",
        "tracer_code",
        "tracer_code_numbered",
        "detected_language",
        "tracer_intro",
        "tracer_output",
        "tracer_error",
    },
    "other": {"fallback_output"},
}


# ─── 공개 함수 ─────────────────────────────────────────────────────────────
def get_route_agent(route: str):
    """A2A에 노출할 route 루트 workflow 반환."""
    return _ROUTE_AGENTS[route]


def get_route_runner(route: str) -> InMemoryRunner:
    """route 전용 InMemoryRunner 반환."""
    return _ROUTE_RUNTIMES[route].runner


async def prepare_route_content(
    route: str,
    session_id: str,
    user_id: str,
    query: str,
    state: dict[str, Any],
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> types.Content:
    """
    세션 state 초기화 후 사용자 메시지용 Content 구성.

    Args:
        route: 실행할 route 키
        session_id: ADK 세션 ID
        user_id: 사용자 ID
        query: 폼에서 받은 질문 본문
        state: 클라이언트가 넘긴 초기 state(dict)
        image_bytes: 첨부 이미지(선택)
        image_mime_type: 이미지 MIME(선택)

    Returns:
        ADK `run_async`에 넘길 user role Content
    """
    runner = get_route_runner(route)
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    initial_state = dict(state)
    initial_state["current_route"] = route
    # 라우팅 워크플로 미경유: recommendation 필터가 rewritten_query 단독 의존 시 빈 필터 가능
    # rewritten_query 없을 때 query로 original·rewritten 기본값 보장
    q = (query or "").strip()
    if q:
        initial_state.setdefault("original_query", q)
        initial_state.setdefault("rewritten_query", q)
    if image_bytes is not None:
        initial_state["has_image"] = True

    if session is None:
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
            state=initial_state,
        )
    else:
        for key in _ROUTE_STATE_KEYS[route]:
            session.state.pop(key, None)
        session.state.update(initial_state)

    parts: list[types.Part] = []
    if query.strip():
        parts.append(types.Part(text=query.strip()))

    if image_bytes is not None:
        mime_type = image_mime_type or "image/jpeg"
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=415, detail=f"지원하지 않는 이미지 형식입니다: {mime_type}")
        await save_image_artifact(runner, user_id, session_id, image_bytes, mime_type)
        parts.append(types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type)))

    if not parts:
        parts.append(types.Part(text=query or state.get("rewritten_query", "")))

    return types.Content(role="user", parts=parts)


async def get_route_state(route: str, session_id: str, user_id: str) -> dict[str, Any]:
    """세션에 남아 있는 state dict 스냅샷 반환. 없으면 빈 dict."""
    runner = get_route_runner(route)
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session and session.state:
        return session.state
    return {}


async def execute_route_stream(route: str, session_id: str, user_id: str, content: types.Content):
    """route workflow를 SSE 스트리밍 모드로 실행. 이벤트 스트림 yield."""
    runner = get_route_runner(route)
    log.info("[Route:%s] 실행 시작 - Session: %s", route, session_id)
    try:
        inflight_key = (route, session_id)
        async with _INFLIGHT_LOCK:
            if inflight_key in _INFLIGHT_SESSIONS:
                raise HTTPException(status_code=409, detail="이미 처리 중인 요청입니다. 잠시 후 다시 시도해 주세요.")
            _INFLIGHT_SESSIONS.add(inflight_key)

        semaphore = _ROUTE_SEMAPHORES.get(route) or _ROUTE_SEMAPHORES.setdefault(route, asyncio.Semaphore(1))
        wait_started = time.monotonic()
        async with semaphore:
            waited_ms = int((time.monotonic() - wait_started) * 1000)
            if waited_ms > 50:
                log.info("[Route:%s] 세마포어 대기 %dms - Session: %s", route, waited_ms, session_id)
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
                run_config=RunConfig(
                    streaming_mode=StreamingMode.SSE,
                    max_llm_calls=_MAX_LLM_CALLS_BY_ROUTE.get(route, 10),
                ),
            ):
                yield event
    finally:
        async with _INFLIGHT_LOCK:
            _INFLIGHT_SESSIONS.discard((route, session_id))
        log.info("[Route:%s] 실행 종료 - Session: %s", route, session_id)
