"""
Google ADK 에이전트 실행 및 세션 관리 모듈

FastAPI 엔드포인트 호출을 통한 에이전트 워크플로우 실행 및 원본 결과 이벤트 반환

`session_service`는 `InMemoryRunner`에 포함된 인메모리 세션 서비스를 사용합니다.
따라서 세션과 `session.state`는 서버 프로세스 메모리에 저장되며,
서버 재시작 또는 다중 인스턴스 환경에서는 공유·영속화되지 않습니다.

이미지 업로드 시에는 ADK `artifact_service`로 세션 아티팩트를 저장하고,
동시에 `types.Part(inline_data=...)`로 현재 요청 Content에도 포함합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import logging

from fastapi import HTTPException, UploadFile
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps.app import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from smart_learning_agent.agent import root_agent
from smart_learning_agent.artifacts import save_image_artifact

# ─── 상수 정의 및 로거 설정 ───────────────────────────────────────────────────
log = logging.getLogger(__name__)

# 허용 가능 이미지 MIME 타입 정의
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_REQUEST_STATE_KEYS = {
    "current_route",
    "original_query",
    "rewritten_query",
    "intent_output",
    "solver_query",
    "solver_output",
    "vertex_filter_output",
    "rec_search_results",
    "rec_query",
    "rec_subject",
    "curator_intro",
    "curator_output",
    "refine_output",
    "problem_cards",
    "tracer_input",
    "tracer_code",
    "tracer_code_numbered",
    "detected_language",
    "tracer_intro",
    "tracer_output",
    "tracer_error",
    "fallback_output",
}

# API 사용자 식별용 고정 ID
USER_ID = "api_user"

# ─── ADK 어플리케이션 구성 ───────────────────────────────────────────────────
routing_app = App(
    name=root_agent.name,
    root_agent=root_agent,
)

# ─── ADK 러너 인스턴스 구성 ───────────────────────────────────────────────────
routing_runner = InMemoryRunner(app=routing_app)


# ─── 세션 및 요청 데이터 처리 유틸리티 ──────────────────────────────────────────────
async def _prepare_content_for_runner(
    target_runner: InMemoryRunner,
    query: str,
    image: UploadFile | None,
    session_id: str,
) -> types.Content:
    """사용자 요청 데이터 기반 ADK Content 객체 생성 및 세션 초기화"""
    session = await target_runner.session_service.get_session(
        app_name=target_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
    )
    if session is None:
        await target_runner.session_service.create_session(
            app_name=target_runner.app_name,
            user_id=USER_ID,
            session_id=session_id,
            state={"has_image": image is not None},
        )
    else:
        for key in _REQUEST_STATE_KEYS:
            session.state.pop(key, None)
        session.state["has_image"] = image is not None

    parts: list[types.Part] = []

    if query.strip():
        parts.append(types.Part(text=query.strip()))

    if image is not None:
        mime_type = image.content_type or "image/jpeg"

        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"지원하지 않는 이미지 형식입니다: {mime_type}",
            )

        image_bytes = await image.read()
        await save_image_artifact(target_runner, USER_ID, session_id, image_bytes, mime_type)
        parts.append(
            types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type))
        )

    if not parts:
        parts.append(types.Part(text=""))

    return types.Content(role="user", parts=parts)


async def prepare_routing_content(
    query: str,
    image: UploadFile | None,
    session_id: str,
) -> types.Content:
    """공통 라우팅 workflow용 ADK Content를 생성합니다."""
    return await _prepare_content_for_runner(routing_runner, query, image, session_id)


async def get_routing_state(session_id: str) -> dict:
    """공통 라우팅 workflow 세션 state를 조회합니다."""
    session = await routing_runner.session_service.get_session(
        app_name=routing_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
    )
    if session and session.state:
        return session.state
    return {}


async def execute_routing_stream(session_id: str, content: types.Content):
    """공통 라우팅 workflow를 스트리밍 모드로 실행합니다."""
    log.info(f"[Routing] 실행 시작 - Session: {session_id}")
    try:
        async for event in routing_runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
            # 라우팅은 (질문 재작성 + 의도 분류)로 보통 2회 수준이지만,
            # 네트워크/429 등으로 재시도가 발생하면 호출 수가 늘 수 있어 여유를 둡니다.
            run_config=RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=15),
        ):
            yield event
    finally:
        log.info(f"[Routing] 실행 종료 - Session: {session_id}")
