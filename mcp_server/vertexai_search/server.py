"""
Vertex AI Search 기능을 노출하는 MCP 서버.

ADK `McpToolset`은 streamable-http(`--transport streamable-http`)로 연결합니다.
검색 tool과 filter expression 생성 tool을 등록합니다.

CLI 기본은 stdio(테스트·레거시 클라이언트용)이며, 운영 시에는 HTTP 트랜스포트를 사용합니다.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import argparse
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .filter_extraction import extract_vertex_filter_output
from .search import (
    VertexExamSearchMetadata,
    build_vertex_exam_filter_expression,
    search_exam_questions as search_exam_questions_impl,
)

# ─── MCP 서버 인스턴스 ─────────────────────────────────────────────────────
# FastMCP: stdio(ADK 서브프로세스)·HTTP 트랜스포트 공통 엔트리
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
    Vertex AI Search에서 기출 문제를 검색하고 추천용 결과로 반환합니다.

    Args:
        search_query: Vertex AI Search에 전달할 시맨틱 검색어
        years: 특정 연도 필터
        rounds: 특정 회차 필터
        question_types: 문제 유형 필터
        year_min: 최소 연도 필터
        year_max: 최대 연도 필터
        question_numbers: 특정 문항 번호 필터
        page_size: 검색 결과 개수
        user_pseudo_id: Discovery Engine 개인화/추적용 사용자 식별자
        relevance_threshold: 키워드 검색 관련도 임계치
        semantic_relevance_threshold: 시맨틱 검색 관련도 임계치

    Returns:
        검색 결과와 검색어, filter expression을 담은 dict
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


@mcp.tool()
def build_filter_expression(
    years: list[int] | None = None,
    rounds: list[int] | None = None,
    question_types: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    question_numbers: list[int] | None = None,
) -> dict[str, Any]:
    """
    입력된 메타 필터를 Discovery Engine filter expression으로 변환합니다.

    Args:
        years: 특정 연도 필터
        rounds: 특정 회차 필터
        question_types: 문제 유형 필터
        year_min: 최소 연도 필터
        year_max: 최대 연도 필터
        question_numbers: 특정 문항 번호 필터

    Returns:
        `filter_expression` 값을 담은 dict
    """
    metadata = VertexExamSearchMetadata(
        years=tuple(years or ()) or None,
        rounds=tuple(rounds or ()) or None,
        question_types=tuple(question_types or ()) or None,
        year_min=year_min,
        year_max=year_max,
        question_numbers=tuple(question_numbers or ()) or None,
    )
    return {"filter_expression": build_vertex_exam_filter_expression(metadata)}


@mcp.tool()
def extract_vertex_filter(
    rewritten_query: str,
) -> dict[str, Any]:
    """
    rewritten_query에서 추천 검색용 메타 필터를 추출합니다.

    Returns:
        VertexFilterOutput 호환 dict
    """
    return extract_vertex_filter_output(rewritten_query)


# ─── CLI 진입점 ────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    """MCP 서버 기동. 기본 transport stdio(ADK 서브프로세스와 동일)."""
    parser = argparse.ArgumentParser(prog="mcp_server.vertexai_search.server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="stdio: ADK·클라이언트 파이프용(기본). sse / streamable-http: HTTP에서 host·port 사용",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="sse·streamable-http 바인드 호스트(기본 127.0.0.1)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8200,
        metavar="PORT",
        help="sse·streamable-http 리슨 포트(기본 8200, 메인 API 8000과 구분). stdio에서는 무시",
    )
    args = parser.parse_args(argv)

    transport: Literal["stdio", "sse", "streamable-http"] = args.transport
    if transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
