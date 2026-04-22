from typing import Literal

from pydantic import BaseModel, Field


class KeywordOutput(BaseModel):
    keywords: list[str] = Field(..., description="추출된 핵심 키워드 목록")
    subject: str = Field(default="", description="추정 과목 (없으면 빈 문자열)")


class WeaknessOutput(BaseModel):
    weakness_type: str = Field(..., description="취약 유형 설명 (예: C 포인터 연산, SQL JOIN)")
    difficulty_preference: Literal["easy", "medium", "hard", "any"] = Field(
        default="any", description="추천 난이도"
    )


class Problem(BaseModel):
    id: str
    subject: str
    difficulty: Literal["easy", "medium", "hard"]
    question_number: int | None = Field(default=None, description="문항 번호 (없으면 None)")
    question: str
    answer: str
    explanation: str
    year: int
    round: int
    similarity_score: float = Field(default=0.0, description="키워드 유사도 점수 (0.0~1.0)")



class VertexFilterOutput(BaseModel):
    query_text: str = Field(..., description="시맨틱 검색에 사용할 텍스트")
    years: list[int] = Field(default_factory=list, description="특정 연도 필터")
    rounds: list[int] = Field(default_factory=list, description="특정 회차 필터")
    question_types: list[str] = Field(
        default_factory=list,
        description="문제 유형 필터 (concept | java | c | python | sql)",
    )
    year_min: int | None = Field(default=None, description="최소 연도")
    year_max: int | None = Field(default=None, description="최대 연도")
    question_numbers: list[int] = Field(default_factory=list, description="문제 번호 필터")


class CuratorOutput(BaseModel):
    query_keywords: list[str] = Field(..., description="검색에 사용된 키워드")
    weakness_type: str = Field(..., description="분석된 취약 유형")
    recommended_problems: list[Problem] = Field(..., description="추천 문제 목록")
    recommendation_reason: str = Field(..., description="추천 이유 설명")

