"""
코드 실행 흐름 시각화 전처리 출력 스키마.

사용자 질문에서 추출한 코드와 감지된 언어를 담습니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from typing import Literal

from pydantic import BaseModel, Field


# ─── 스키마 정의 ───────────────────────────────────────────────────────────
class TracerInputOutput(BaseModel):
    """
    코드 추적 전처리 결과.

    Attributes:
        tracer_code: 사용자 질문에서 추출한 실행 대상 코드
        detected_language: 감지된 프로그래밍 언어
    """

    tracer_code: str = Field(..., description="사용자 질문에서 추출한 실행 대상 코드")
    detected_language: Literal["c", "java", "python"] = Field(
        ...,
        description="감지된 프로그래밍 언어",
    )
