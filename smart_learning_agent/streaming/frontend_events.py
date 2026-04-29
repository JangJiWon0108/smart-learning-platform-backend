"""
ADK Runner 이벤트 스트림을 프론트엔드용 이벤트(dict)로 변환.

프로젝트 초기에는 프론트가 특정 포맷의 SSE payload를 기대하므로,
여기서 최소한의 정규화만 수행합니다.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any


async def iter_frontend_events(
    events: Any,
    current_state: Callable[[], Awaitable[dict[str, Any]]],
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Args:
        events: ADK runner.run_async(...)가 생성하는 이벤트 async-iterator
        current_state: 세션 state를 조회하는 coroutine 함수

    Yields:
        프론트엔드에서 처리할 수 있는 이벤트 dict
    """
    async for event in events:
        # ADK Event 객체는 런타임마다 표현이 조금씩 달라 문자열/속성 방식을 모두 지원합니다.
        payload: dict[str, Any] = {}

        # 1) 노드 진행 이벤트(가능하면 state로 동기화)
        node_name = getattr(event, "node", None) or getattr(event, "agent_name", None)
        if node_name:
            payload = {"type": "state", "node": str(node_name)}
            # 일부 UI는 최신 state를 같이 원하므로 붙여줍니다(비용이 커지면 제거 가능).
            try:
                payload["state"] = await current_state()
            except Exception:
                payload["state"] = {}
            yield payload
            continue

        # 2) 최종 응답 텍스트 이벤트
        if hasattr(event, "is_final_response") and callable(getattr(event, "is_final_response")):
            if event.is_final_response() and getattr(event, "content", None):
                text_chunks: list[str] = []
                for part in getattr(event.content, "parts", []) or []:
                    t = getattr(part, "text", None)
                    if t:
                        text_chunks.append(str(t))
                if text_chunks:
                    yield {"type": "text", "text": "".join(text_chunks)}
                continue

        # 3) 기본 fallback: 문자열화해서 텍스트로 전달
        yield {"type": "raw", "text": str(event)}

"""
ADK Event를 프론트엔드 SSE 계약에 맞는 dict 이벤트로 변환합니다.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

STREAM_NODES = {
    "solver_agent",
    "fallback_agent",
    "curator_intro_agent",
    "tracer_intro_agent",
}


def build_curation_payload(state: dict[str, Any]) -> dict[str, Any] | None:
    """상태 정보 기반 큐레이션 페이로드 생성."""
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


def _state_value_to_dict(value: Any) -> dict[str, Any] | None:
    """Pydantic 모델/일반 dict를 payload용 dict로 정규화합니다."""
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else None
    return None


def build_tracer_payload(state: dict[str, Any]) -> dict[str, Any] | None:
    """상태 정보 기반 코드 실행 흐름 payload 또는 원인별 오류 payload를 생성합니다."""
    if state.get("current_route") != "visualization":
        return None

    tracer_output = _state_value_to_dict(state.get("tracer_output"))
    if tracer_output and tracer_output.get("steps"):
        return {
            "type": "tracer",
            "route": state.get("current_route"),
            "data": tracer_output,
        }

    tracer_error = state.get("tracer_error")
    if isinstance(tracer_error, str) and tracer_error.strip():
        message = tracer_error.strip()
    elif not str(state.get("tracer_code") or "").strip():
        message = "분석할 코드를 찾지 못했습니다. 코드블록이나 실행 가능한 코드를 함께 보내주세요."
    else:
        message = "코드 실행 흐름 결과를 만들지 못했습니다. 코드를 조금 더 작게 나누거나 실행 가능한 형태로 다시 보내주세요."

    return {
        "type": "error",
        "message": message,
    }


async def iter_frontend_events(
    events: AsyncIterator[Any],
    get_state: Callable[[], Awaitable[dict[str, Any]]],
    emit_final: bool = True,
) -> AsyncIterator[dict[str, Any]]:
    """ADK Event stream을 현재 프론트가 처리하는 JSON 이벤트로 변환합니다."""
    emitted_nodes: set[str] = set()
    streamed_text_nodes: set[str] = set()
    streaming_node: str | None = None
    prev_node: str | None = None

    async for event in events:
        node_info = getattr(event, "node_info", None)
        node_name = getattr(node_info, "name", None) if node_info else None
        is_stream_node = node_name in STREAM_NODES if node_name else False

        if (
            prev_node is not None
            and streaming_node is not None
            and node_name != prev_node
            and streaming_node == prev_node
        ):
            yield {"type": "stream_end"}
            streaming_node = None
        prev_node = node_name

        if node_name and node_name not in emitted_nodes:
            emitted_nodes.add(node_name)
            yield {"type": "state", "node": node_name}

        if is_stream_node and event.content:
            for part in event.content.parts:
                if part.text and not getattr(part, "function_call", None):
                    if event.partial:
                        streaming_node = node_name
                        streamed_text_nodes.add(node_name)
                        yield {"type": "chunk", "text": part.text}
                    elif node_name not in streamed_text_nodes:
                        streaming_node = node_name
                        streamed_text_nodes.add(node_name)
                        yield {"type": "chunk", "text": part.text}

        if is_stream_node and streaming_node == node_name and not event.partial:
            yield {"type": "stream_end"}
            streaming_node = None

    if streaming_node is not None:
        yield {"type": "stream_end"}

    if not emit_final:
        return

    state = await get_state()
    curation = build_curation_payload(state)
    if curation:
        yield curation

    tracer = build_tracer_payload(state)
    if tracer:
        yield tracer

