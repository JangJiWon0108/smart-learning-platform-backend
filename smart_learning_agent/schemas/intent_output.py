"""
의도 분류 에이전트의 출력 스키마.

사용자의 질문이 어떤 의도인지 분류한 결과를 담습니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from typing import Literal

from pydantic import BaseModel, Field


# ─── 스키마 정의 ───────────────────────────────────────────────────────────
class IntentOutput(BaseModel):
    """
    의도 분류 결과.

    Attributes:
        intent: 분류된 의도 (4가지 중 하나)
    """

    intent: Literal["solver", "recommendation", "visualization", "other"] = Field(
        ...,
        description=(
            "분류된 의도. "
            "'solver' = 문제 해설 요청, "
            "'recommendation' = 유사 문제 추천 요청, "
            "'visualization' = 코드 실행 흐름 시각화 요청, "
            "'other' = 해당 없음"
        ),
    )

