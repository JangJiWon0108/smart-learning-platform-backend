"""
문제 추천 결과를 CuratorOutput 형태로 변환하는 노드.

Vertex AI Search 결과를 LLM 추론 없이 후속 정제 에이전트가 사용할 수 있는
구조화된 추천 문제 목록으로 변환합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator
from typing import Any

from google.adk import Event

from smart_learning_agent.schemas.curator_output import CuratorOutput, Problem


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _problem_id(problem: dict[str, Any], index: int) -> str:
    """검색 결과의 메타데이터로 안정적인 문제 ID를 생성합니다."""
    year = problem.get("year") or "unknown"
    round_number = problem.get("round") or "unknown"
    question_number = problem.get("question_number") or index + 1
    return f"{year}_{round_number}_{question_number}"


def _to_problem(problem: dict[str, Any], index: int, rec_subject: str) -> Problem:
    """Vertex AI Search 결과 1개를 추천 문제 스키마로 변환합니다."""
    subject = str(problem.get("question_type") or rec_subject or "전체")

    return Problem(
        id=_problem_id(problem, index),
        subject=subject,
        question_number=problem.get("question_number"),
        question=str(problem.get("question") or ""),
        answer=str(problem.get("answer") or ""),
        explanation=str(problem.get("explanation") or ""),
        year=int(problem.get("year") or 0),
        round=int(problem.get("round") or 0),
        similarity_score=float(problem.get("score") or 0.0),
    )


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def build_curator_output_func(
    rec_search_results: list[dict[str, Any]] | None = None,
    rec_query: str = "",
    rec_subject: str = "전체",
) -> Generator[Event, None, None]:
    """
    Vertex AI Search 결과를 CuratorOutput state로 변환합니다.

    Args:
        rec_search_results: Vertex AI Search에서 파싱한 문제 목록
        rec_query: 검색에 사용한 재작성 질문
        rec_subject: 검색한 문제 유형 표시값

    Yields:
        curator_output을 포함하는 Event

    state에 저장되는 값:
        - curator_output: 추천 문제 목록과 추천 이유를 담은 구조화 출력
    """
    results = rec_search_results or []
    problems = [
        _to_problem(problem, index, rec_subject)
        for index, problem in enumerate(results[:3])
        if isinstance(problem, dict)
    ]

    if problems:
        reason = f"'{rec_query}' 검색 결과와 메타 필터에 맞는 문제를 추천했습니다."
    else:
        reason = f"'{rec_query}' 조건에 맞는 추천 문제를 찾지 못했습니다."

    curator_output = CuratorOutput(
        query_keywords=[rec_query] if rec_query else [],
        recommended_problems=problems,
        recommendation_reason=reason,
    )

    yield Event(state={"curator_output": curator_output.model_dump()})
