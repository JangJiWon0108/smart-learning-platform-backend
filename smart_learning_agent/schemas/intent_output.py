"""
의도 분류 에이전트의 출력 스키마.

사용자의 질문이 어떤 의도인지 분류한 결과를 담습니다.
"""

from typing import Literal

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
    """
    의도 분류 결과.

    Attributes:
        intent:     분류된 의도 (4가지 중 하나)
        confidence: 분류 신뢰도 (0.0 = 확신 없음, 1.0 = 완전 확신)
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

    confidence: float = Field(
        ...,
        description="분류 신뢰도 (0.0 ~ 1.0)",
    )
