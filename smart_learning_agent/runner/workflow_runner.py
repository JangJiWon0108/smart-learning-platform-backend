"""
Google ADK 에이전트 실행 및 세션 관리 모듈

FastAPI 엔드포인트 호출을 통한 에이전트 워크플로우 실행 및 원본 결과 이벤트 반환

현재 구현은 Google ADK `App`에 `root_agent`를 등록하고,
`InMemoryRunner`로 워크플로우를 실행합니다.

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

# API 사용자 식별용 고정 ID
USER_ID = "api_user"

# ─── ADK 어플리케이션 구성 ───────────────────────────────────────────────────
_app = App(
    name=root_agent.name,
    root_agent=root_agent,
)

# ─── ADK 러너 인스턴스 구성 ───────────────────────────────────────────────────
workflow_runner = InMemoryRunner(app=_app)


# ─── 세션 및 요청 데이터 처리 유틸리티 ──────────────────────────────────────────────
async def prepare_content(
    query: str,
    image: UploadFile | None,
    session_id: str,
) -> types.Content:
    """사용자 요청 데이터 기반 ADK Content 객체 생성 및 세션 초기화"""
    session = await workflow_runner.session_service.get_session(
        app_name=workflow_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
    )
    if session is None:
        await workflow_runner.session_service.create_session(
            app_name=workflow_runner.app_name,
            user_id=USER_ID,
            session_id=session_id,
            state={"has_image": image is not None},
        )
    else:
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
        await save_image_artifact(workflow_runner, USER_ID, session_id, image_bytes, mime_type)
        parts.append(
            types.Part(inline_data=types.Blob(data=image_bytes, mime_type=mime_type))
        )

    if not parts:
        parts.append(types.Part(text=""))

    return types.Content(role="user", parts=parts)


async def get_session_state(session_id: str) -> dict:
    """특정 세션의 현재 상태 정보 조회"""
    session = await workflow_runner.session_service.get_session(
        app_name=workflow_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
    )
    if session and session.state:
        return session.state
    return {}


# ─── 에이전트 실행 로직 ───────────────────────────────────────────────────────
async def execute_agent(session_id: str, content: types.Content):
    """비스트리밍 모드 기반 ADK 에이전트 실행 및 원본 이벤트 반환"""
    async for event in workflow_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
        run_config=RunConfig(max_llm_calls=30),
    ):
        yield event


async def execute_agent_stream(session_id: str, content: types.Content):
    """스트리밍 모드 기반 ADK 에이전트 실행 및 원본 이벤트 반환.

    LLM 호출이 60초를 초과하면 TimeoutError가 발생하며,
    호출부(app.py event_generator)에서 error 이벤트로 변환해 프론트로 전달합니다.
    """
    log.info(f"[Workflow] 실행 시작 - Session: {session_id}")
    try:
        async for event in workflow_runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
            run_config=RunConfig(
                streaming_mode=StreamingMode.SSE,
                max_llm_calls=30,
            ),
        ):
            node_info = getattr(event, "node_info", None)
            if node_info:
                log.info(f"[Workflow] Node: {node_info.name} (type: {type(event).__name__})")
            yield event
    except TimeoutError:
        log.error(f"[Workflow] 60초 타임아웃 초과 - Session: {session_id}")
        raise
    except Exception as e:
        log.error(f"[Workflow] 실행 중 오류 발생: {str(e)}")
        raise
    finally:
        log.info(f"[Workflow] 실행 종료 - Session: {session_id}")
