"""
문제 추천(curator) 관련 스키마 모음.

추천 에이전트의 입력(검색 필터)과 출력(추천 문제 목록)을 정의합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from pydantic import BaseModel, Field


# ─── 스키마 정의 ───────────────────────────────────────────────────────────
class KeywordOutput(BaseModel):
    """사용자 질문에서 추출한 키워드와 과목 정보."""

    keywords: list[str] = Field(..., description="추출된 핵심 키워드 목록")
    subject: str = Field(default="", description="추정 과목 (없으면 빈 문자열)")


class Problem(BaseModel):
    """
    추천할 기출 문제 1개의 정보.

    Vertex AI Search에서 검색된 결과를 이 형태로 담습니다.
    """

    id: str
    subject: str
    question_number: int | None = Field(default=None, description="문항 번호 (없으면 None)")
    question: str
    answer: str
    explanation: str
    year: int
    round: int
    similarity_score: float = Field(default=0.0, description="키워드 유사도 점수 (0.0~1.0)")


class VertexFilterOutput(BaseModel):
    """
    Vertex AI Search 검색에 사용할 메타 필터 조건.

    filter_agent가 사용자 질문을 분석해서 검색 범위를 좁히는 필터만 출력합니다.
    실제 검색어는 rewritten_query를 그대로 사용합니다.
    """

    years: list[int] = Field(default_factory=list, description="특정 연도 필터 (예: [2023, 2024])")
    rounds: list[int] = Field(default_factory=list, description="특정 회차 필터 (예: [1, 2])")
    question_types: list[str] = Field(
        default_factory=list,
        description="문제 유형 필터 (concept | java | c | python | sql)",
    )
    year_min: int | None = Field(default=None, description="최소 연도 (이 연도 이후)")
    year_max: int | None = Field(default=None, description="최대 연도 (이 연도 이전)")
    question_numbers: list[int] = Field(default_factory=list, description="문제 번호 필터 (1~20)")


class CuratorOutput(BaseModel):
    """
    문제 추천 에이전트의 최종 출력.

    검색 결과를 분석해서 추천 문제 목록과 추천 이유를 담습니다.
    """

    query_keywords: list[str] = Field(..., description="검색에 사용된 키워드")
    recommended_problems: list[Problem] = Field(..., description="추천 문제 목록 (최대 3개)")
    recommendation_reason: str = Field(..., description="이 문제들을 추천하는 이유 설명")
