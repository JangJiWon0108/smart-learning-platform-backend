"""
Vertex AI Search MCP tool 실행 결과를 recommendation route state에 반영.

vertex_search_agent의 tool 응답을 후속 큐레이션 노드가 읽는
rec_search_results, rec_query, rec_subject, rec_filter_expression로 정규화합니다.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import json
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
_SEARCH_TOOL_NAME = "search_exam_questions"


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _parse_mcp_response(response: dict[str, Any]) -> dict[str, Any]:
    """
    MCP CallToolResult payload에서 구조화 본문 dict 추출.

    Args:
        response: tool 원시 응답 dict

    Returns:
        results·filter_expression 등이 올 수 있는 파싱된 dict
    """
    if "results" in response:
        return response
    if isinstance(response.get("structuredContent"), dict):
        return response["structuredContent"]
    for item in response.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except (json.JSONDecodeError, KeyError):
                pass
    return {}


def _search_results(response: dict[str, Any]) -> list[dict[str, Any]]:
    """파싱된 응답에서 results 리스트만 추출. 없거나 타입 불일치 시 빈 리스트."""
    parsed = _parse_mcp_response(response)
    results = parsed.get("results")
    return results if isinstance(results, list) else []


def _subject_display(args: dict[str, Any]) -> str:
    """tool 인자 question_types를 UI용 과목 라벨 문자열로 변환."""
    question_types = args.get("question_types")
    if isinstance(question_types, list) and question_types:
        return ", ".join(str(question_type) for question_type in question_types)
    return "전체"


# ─── 콜백 함수 ─────────────────────────────────────────────────────────────
def save_vertex_search_result(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """
    search_exam_questions tool 완료 직후 state에 검색 결과 반영.

    Args:
        tool: 호출된 ADK tool
        args: tool 호출 인자
        tool_context: ADK ToolContext(state 쓰기)
        tool_response: MCP가 반환한 원시 dict

    Returns:
        후속 처리 없음. 항상 None.

    state에 저장되는 값:
        - rec_search_results: 파싱된 문제 dict 목록
        - rec_query: search_query 인자(트림)
        - rec_subject: question_types 요약 또는 "전체"
        - rec_filter_expression: 응답 내 filter_expression(있을 때)
    """
    if tool.name != _SEARCH_TOOL_NAME:
        return None

    parsed = _parse_mcp_response(tool_response)
    tool_context.state["rec_search_results"] = _search_results(tool_response)
    tool_context.state["rec_query"] = str(args.get("search_query") or "").strip()
    tool_context.state["rec_subject"] = _subject_display(args)
    tool_context.state["rec_filter_expression"] = parsed.get("filter_expression")
    return None


def ensure_vertex_search_state(callback_context: CallbackContext) -> types.Content | None:
    """
    vertex_search_agent 종료 시점에 검색 관련 state 기본값 보장.

    Args:
        callback_context: ADK CallbackContext

    Returns:
        후속 메시지 없음. 항상 None.

    state에 저장되는 값:
        - rec_search_results: 없으면 []
        - rec_query: 없으면 rewritten_query 폴백
        - rec_subject: 없으면 "전체"
        - rec_filter_expression: 없으면 None
    """
    callback_context.state.setdefault("rec_search_results", [])
    fallback_query = str(callback_context.state.get("rewritten_query") or "").strip()
    callback_context.state.setdefault("rec_query", fallback_query)
    callback_context.state.setdefault("rec_subject", "전체")
    callback_context.state.setdefault("rec_filter_expression", None)
    return None
