"""
Google ADK 에이전트 실행 및 세션 관리를 담당하는 모듈.

FastAPI 엔드포인트에서 호출되어 실제 에이전트 워크플로우를 실행하고
가공되지 않은 원본 결과 이벤트를 반환합니다.
"""

# ─── 임포트 ──────────────────────────────────────────────────────────────
import logging
from typing import AsyncGenerator

from fastapi import HTTPException, UploadFile
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from smart_learning_agent.agent import root_agent
from smart_learning_agent.artifacts import save_image_artifact

# ─── 상수 및 로거 설정 ───────────────────────────────────────────────────
log = logging.getLogger(__name__)

# 허용하는 이미지 MIME 타입 목록
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# 고정 API 사용자 ID (단일 사용자 또는 세션 기반 식별용)
USER_ID = "api_user"

# ─── ADK 앱 설정 ────────────────────────────────────────────────────────
# App으로 감싸서 컨텍스트 캐싱과 이벤트 컴팩션을 활성화합니다.
_app = App(
    name=root_agent.name,
    root_agent=root_agent,
    # 컨텍스트 캐싱: 대형 instruction(시스템 프롬프트)을 재사용해 LLM 비용 절감
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,     # 2048 토큰 이상 요청에만 캐시 적용
        ttl_seconds=600,     # 캐시 TTL 10분
        cache_intervals=5,   # 5회 invocation마다 캐시 갱신
    ),
    # 이벤트 컴팩션: 장기 세션의 이벤트 기록을 LLM으로 요약해 컨텍스트 윈도우 절약
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,   # 새 invocation 5회마다 슬라이딩 윈도우 컴팩션 트리거
        overlap_size=1,          # 이전 컴팩션과 1 invocation 오버랩 유지
        token_threshold=8000,    # 누적 토큰 8K 초과 시 즉시 토큰 기반 컴팩션 선실행
        event_retention_size=10, # 마지막 10개 이벤트는 요약 없이 원문 유지
    ),
)

# ─── ADK 러너 인스턴스 설정 ──────────────────────────────────────────────
workflow_runner = InMemoryRunner(app=_app)


# ─── 세션 및 콘텐츠 헬퍼 함수 ─────────────────────────────────────────────
async def prepare_content(
    query: str,
    image: UploadFile | None,
    session_id: str,
) -> types.Content:
    """사용자 요청(텍스트/이미지)을 기반으로 ADK Content 객체를 생성하고 세션을 초기화합니다."""
    # 1단계: 세션 생성 및 초기 상태 설정 (이미지 포함 여부 등)
    await workflow_runner.session_service.create_session(
        app_name=workflow_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
        state={"has_image": image is not None},
    )

    parts: list[types.Part] = []

    # 2단계: 텍스트 질문 처리
    if query.strip():
        parts.append(types.Part(text=query.strip()))

    # 3단계: 이미지 파일 처리 (검증 및 아티팩트 저장)
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

    # 4단계: 빈 요청인 경우 기본 텍스트 추가 (ADK 요구사항 대응)
    if not parts:
        parts.append(types.Part(text=""))

    return types.Content(role="user", parts=parts)


async def get_session_state(session_id: str) -> dict:
    """지정된 세션의 현재 상태(state)를 가져옵니다."""
    session = await workflow_runner.session_service.get_session(
        app_name=workflow_runner.app_name,
        user_id=USER_ID,
        session_id=session_id,
    )

    if session and session.state:
        return session.state
    return {}


# ─── 에이전트 실행 함수 ───────────────────────────────────────────────────
async def execute_agent(session_id: str, content: types.Content):
    """비스트리밍 모드로 ADK 에이전트를 실행하고 raw 이벤트를 yield 합니다."""
    async for event in workflow_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        yield event


async def execute_agent_stream(session_id: str, content: types.Content):
    """스트리밍 모드로 ADK 에이전트를 실행하고 raw 이벤트를 yield 합니다."""
    async for event in workflow_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        yield event
