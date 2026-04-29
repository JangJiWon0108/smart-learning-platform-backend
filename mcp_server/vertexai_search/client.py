"""
Vertex AI Search MCP 서버(streamable-http) 호출용 클라이언트 어댑터.

ADK 외부에서 동일 MCP를 직접 호출할 때 사용. 운영 추천 경로는 ADK McpToolset이 담당.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from config.properties import Settings


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _tool_result(result: Any) -> dict[str, Any]:
    """CallToolResult에서 dict 페이로드 추출. 오류 시 RuntimeError."""
    if result.isError:
        messages = [
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        ]
        raise RuntimeError("\n".join(messages) or "MCP tool call failed")

    if result.structuredContent:
        return dict(result.structuredContent)

    for content in result.content:
        if isinstance(content, TextContent):
            return json.loads(content.text)

    return {}


async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    streamable-http로 MCP tool 1회 호출.

    Args:
        name: tool 이름
        arguments: tool 인자 dict

    Returns:
        structuredContent 또는 text JSON 파싱 결과 dict
    """
    settings = Settings()
    url = settings.VERTEXAI_SEARCH_MCP_URL
    async with streamable_http_client(url, terminate_on_close=True) as (
        read_stream,
        write_stream,
        _get_sid,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments)
            return _tool_result(result)


async def search_exam_questions(
    *,
    search_query: str,
    years: list[int] | None = None,
    rounds: list[int] | None = None,
    question_types: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    question_numbers: list[int] | None = None,
    page_size: int = 3,
) -> dict[str, Any]:
    """
    MCP `search_exam_questions` 래퍼.

    Args:
        search_query: 시맨틱 검색어
        years: 연도 필터
        rounds: 회차 필터
        question_types: 유형 필터
        year_min: 최소 연도
        year_max: 최대 연도
        question_numbers: 문항 번호 필터
        page_size: 결과 개수 상한

    Returns:
        MCP 서버와 동일 스키마의 응답 dict
    """
    return await call_tool(
        "search_exam_questions",
        {
            "search_query": search_query,
            "years": years or [],
            "rounds": rounds or [],
            "question_types": question_types or [],
            "year_min": year_min,
            "year_max": year_max,
            "question_numbers": question_numbers or [],
            "page_size": page_size,
        },
    )
