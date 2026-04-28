"""MCP server exposing Vertex AI Search operations for the learning platform."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .search import (
    VertexExamSearchMetadata,
    build_vertex_exam_filter_expression,
    search_exam_questions as search_exam_questions_impl,
)

mcp = FastMCP("vertexai-search")


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
    """Search exam questions in Vertex AI Search and return parsed results."""
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
    """Build the Discovery Engine filter expression for given exam metadata."""
    metadata = VertexExamSearchMetadata(
        years=tuple(years or ()) or None,
        rounds=tuple(rounds or ()) or None,
        question_types=tuple(question_types or ()) or None,
        year_min=year_min,
        year_max=year_max,
        question_numbers=tuple(question_numbers or ()) or None,
    )
    return {"filter_expression": build_vertex_exam_filter_expression(metadata)}


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
