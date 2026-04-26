"""
Google ADK 아티팩트 유틸리티 공개 API.

현재 이미지 업로드 파일은 Runner의 `artifact_service`를 통해
세션 아티팩트로 저장됩니다.
"""

from .image import IMAGE_ARTIFACT_KEY, save_image_artifact

__all__ = ["IMAGE_ARTIFACT_KEY", "save_image_artifact"]
