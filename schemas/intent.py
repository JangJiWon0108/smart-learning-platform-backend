from typing import Literal

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
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
    confidence: float = Field(..., description="분류 신뢰도 (0.0 ~ 1.0)")

