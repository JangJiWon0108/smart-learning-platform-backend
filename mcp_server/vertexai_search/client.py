"""Client adapter for calling the local Vertex AI Search MCP server."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.vertexai_search.server"],
        cwd=_BACKEND_ROOT,
    )


def _extract_tool_response(result: Any) -> dict[str, Any]:
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
    """Call a Vertex AI Search MCP tool through a short-lived stdio session."""
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments)
            return _extract_tool_response(result)


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
    """Search exam questions through the MCP server."""
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
