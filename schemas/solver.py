from pydantic import BaseModel, Field


class SolverOutput(BaseModel):
    subject: str = Field(..., description="과목명 (예: 프로그래밍 언어 활용, 데이터베이스 활용)")
    explanation: str = Field(..., description="문제 해설 (마크다운 가능)")
    answer: str = Field(..., description="최종 정답 또는 핵심 결론")
    key_concepts: list[str] = Field(..., description="핵심 개념 키워드 목록")
    related_topics: list[str] = Field(default_factory=list, description="연관 학습 주제")
    search_references: list[str] = Field(default_factory=list, description="참고한 웹 검색 출처 URL")

