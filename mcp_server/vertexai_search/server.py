"""
Vertex AI Search용 FastMCP 서버.

`search_exam_questions` 등록. ADK `McpToolset`은 `streamable-http`로 본 프로세스에 연결.
모듈 직접 실행 시 `VERTEXAI_SEARCH_MCP_URL`의 host·port에 바인드한 뒤 동일 트랜스포트로 기동.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from typing import Any

from mcp.server.fastmcp import FastMCP

from .search import search_exam_questions as search_exam_questions_impl

# ─── MCP 서버 인스턴스 ─────────────────────────────────────────────────────
# stdio·HTTP 공통 FastMCP 엔트리
mcp = FastMCP("vertexai-search")


# ─── MCP Tool 정의 ────────────────────────────────────────────────────────
@mcp.tool()
def search_exam_questions(
    search_query: str,
    years: list[int] | None = None,
    rounds: list[int] | None = None,
    question_types: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    question_numbers: list[int] | None = None,
    page_size: int = 3,
    user_pseudo_id: str | None = None,
    relevance_threshold: str | None = None,
    semantic_relevance_threshold: float | None = None,
) -> dict[str, Any]:
    """
    기출 검색 MCP 경계. Discovery 호출·파싱 결과 dict 반환.

    Args:
        search_query: 시맨틱 검색어
        years: 연도 필터
        rounds: 회차 필터
        question_types: 문제 유형 필터
        year_min: 최소 연도
        year_max: 최대 연도
        question_numbers: 문항 번호 필터
        page_size: 결과 개수 상한
        user_pseudo_id: Discovery userPseudoId
        relevance_threshold: 키워드 관련도 임계치
        semantic_relevance_threshold: 시맨틱 관련도 임계치

    Returns:
        `results`, `query`, `filter_expression` 키를 가진 dict
    """
    return search_exam_questions_impl(
        search_query=search_query,
        years=years,
        rounds=rounds,
        question_types=question_types,
        year_min=year_min,
        year_max=year_max,
        question_numbers=question_numbers,
        page_size=page_size,
        user_pseudo_id=user_pseudo_id,
        relevance_threshold=relevance_threshold,
        semantic_relevance_threshold=semantic_relevance_threshold,
    )


if __name__ == "__main__":
    # Agent toolset과 동일 URL 기준으로 리슨 주소 확정 (포트 생략 시 8200)
    from urllib.parse import urlparse

    from config.properties import Settings

    settings = Settings()
    parsed = urlparse(settings.VERTEXAI_SEARCH_MCP_URL)
    mcp.settings.host = parsed.hostname or "127.0.0.1"
    mcp.settings.port = parsed.port if parsed.port is not None else 8200
    mcp.run(transport="streamable-http") # MCP 서버 실행 (8200포트)
