from google.adk import Event
from google.adk.tools import ToolContext

IMAGE_ARTIFACT_KEY = "uploaded_image.jpg"


async def image_preprocess_func(tool_context: ToolContext):
    """아티팩트 서비스에서 업로드된 이미지를 로드하고 state에 has_image 플래그를 설정한다."""
    try:
        artifact = await tool_context.load_artifact(IMAGE_ARTIFACT_KEY)
        if artifact and artifact.inline_data:
            yield Event(state={"has_image": True})
            return
    except ValueError:
        # artifact_service 미설정 환경(CLI 실행 등)에서는 이미지 없음으로 처리
        pass
    yield Event(state={"has_image": False})
