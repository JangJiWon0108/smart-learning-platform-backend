"""
추천 문제 정제(refine) 에이전트의 출력 스키마.

검색으로 가져온 원시 문제 텍스트에서
아티팩트(태그, 노이즈 등)를 제거하고 깔끔하게 정제한 결과를 담습니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from pydantic import BaseModel, Field


# ─── 스키마 정의 ───────────────────────────────────────────────────────────
class RefinedProblem(BaseModel):
    """
    정제된 문제 1개의 정보.

    원본 문제 텍스트에서:
    - [문제], [cs], colored by 같은 노이즈 제거
    - 코드/테이블은 refined_code로 분리
    - 들여쓰기/포맷 정규화
    """

    # 원본 문제의 ID (Problem.id와 동일)
    id: str = Field(..., description="문제 ID")

    # 정제된 문제 지문 (코드/테이블 제외, 아티팩트 제거)
    refined_question: str = Field(
        ...,
        description="정제된 문제 지문. [cs], colored by 등 아티팩트 제거. 코드/테이블은 여기서 제외.",
    )

    # 정제된 코드 또는 테이블 (없으면 None)
    refined_code: str | None = Field(
        default=None,
        description="정제된 코드 또는 SQL 테이블 문자열. 없으면 None.",
    )

    # 코드 언어 식별자 (없으면 None)
    code_language: str | None = Field(
        default=None,
        description="코드 언어 식별자. java | c | python | sql 중 하나. 없으면 None.",
    )


class RefineOutput(BaseModel):
    """정제된 문제 목록 (최대 3개)."""

    refined_problems: list[RefinedProblem] = Field(..., description="정제된 문제 목록")
