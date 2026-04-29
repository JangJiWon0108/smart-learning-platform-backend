"""
Vertex AI Search MCP 응답용 Pydantic 스키마.

MCP tool 구조화 응답과 동일 형태의 모델 정의.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from pydantic import BaseModel, Field


# ─── 스키마 정의 ───────────────────────────────────────────────────────────
class ExamSearchResult(BaseModel):
    """파싱된 기출 1건."""

    question: str = Field(default="", description="문제 지문")
    answer: str = Field(default="", description="정답 텍스트")
    explanation: str = Field(default="", description="해설 텍스트")
    year: int | None = Field(default=None, description="기출 연도")
    round: int | None = Field(default=None, description="기출 회차")
    question_type: str = Field(default="", description="문제 유형 (concept | java | c | python | sql)")
    question_number: int | None = Field(default=None, description="문항 번호")
    score: float = Field(default=0.0, description="Vertex AI Search 관련도 점수")


class SearchExamQuestionsResponse(BaseModel):
    """`search_exam_questions` tool 응답 본문."""

    results: list[ExamSearchResult] = Field(default_factory=list, description="검색 결과 목록")
    query: str = Field(default="", description="검색에 사용한 시맨틱 검색어")
    filter_expression: str | None = Field(default=None, description="Discovery Engine filter expression")
