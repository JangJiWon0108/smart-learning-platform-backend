"""
문제 풀이(solver) 에이전트의 출력 스키마.

현재 solver_agent는 자유 텍스트로 응답하므로
이 스키마는 참고용입니다.
"""

from pydantic import BaseModel, Field


class SolverOutput(BaseModel):
    """
    문제 풀이 결과.

    Attributes:
        subject:           과목명
        explanation:       단계별 풀이 해설 (마크다운 사용 가능)
        answer:            최종 정답
        key_concepts:      핵심 개념 키워드 목록
        related_topics:    연관해서 공부하면 좋은 주제
        search_references: 참고한 웹 검색 URL 목록
    """

    subject: str = Field(..., description="과목명 (예: 프로그래밍 언어 활용, 데이터베이스 활용)")
    explanation: str = Field(..., description="문제 해설 (마크다운 가능)")
    answer: str = Field(..., description="최종 정답 또는 핵심 결론")
    key_concepts: list[str] = Field(..., description="핵심 개념 키워드 목록")
    related_topics: list[str] = Field(default_factory=list, description="연관 학습 주제")
    search_references: list[str] = Field(default_factory=list, description="참고한 웹 검색 출처 URL")
