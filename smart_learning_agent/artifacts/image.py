"""
이미지 아티팩트 저장 유틸리티.

Google ADK artifact_service를 사용해 업로드된 이미지를 세션에 저장합니다.
solver_agent가 이미지를 직접 볼 수 있도록 Content에도 포함됩니다.

현재 Runner는 `InMemoryRunner`이므로 artifact_service도 인메모리 기반입니다.
저장된 이미지 아티팩트는 서버 프로세스 메모리에 보관되며,
서버 재시작 또는 다중 인스턴스 환경에서는 공유·영속화되지 않습니다.
"""

from google.adk.runners import InMemoryRunner
from google.genai import types

IMAGE_ARTIFACT_KEY = "uploaded_image.jpg"


async def save_image_artifact(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    image_bytes: bytes,
    mime_type: str,
) -> None:
    await runner.artifact_service.save_artifact(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        filename=IMAGE_ARTIFACT_KEY,
        artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
    )
