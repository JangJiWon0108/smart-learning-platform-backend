"""
Vertex AI Search MCP tool을 호출하는 추천 검색 에이전트.

filter_agent가 만든 메타 필터(state["vertex_filter_output"])와 rewritten_query로
MCP 서버의 search_exam_questions tool을 1회 호출합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.callbacks.vertex_search_callback import (
    ensure_vertex_search_state,
    save_vertex_search_result,
)

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
_SEARCH_TOOL_NAME = "search_exam_questions"
_MCP_TIMEOUT_SECONDS = 10.0


def _vertex_search_toolset() -> McpToolset:
    """MCP streamable-http 세션 및 search_exam_questions 단일 tool 바인딩."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=settings.VERTEXAI_SEARCH_MCP_URL,
            timeout=_MCP_TIMEOUT_SECONDS,
        ),
        tool_filter=[_SEARCH_TOOL_NAME],
    )


vertex_search_agent = Agent(
    name="vertex_search_agent",
    model=settings.GEMINI_MODEL_TYPE_FILTER,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    tools=[_vertex_search_toolset()],
    after_tool_callback=save_vertex_search_result,
    after_agent_callback=ensure_vertex_search_state,
    description="Vertex AI Search MCP 도구로 추천 후보 문제를 검색하는 에이전트",
    instruction=f"""
당신은 정보처리기사 실기 기출 문제를 검색하는 에이전트입니다.

재작성된 질문: {{rewritten_query?}}
검색 필터: {{vertex_filter_output?}}

반드시 `{_SEARCH_TOOL_NAME}` 도구를 한 번 호출하세요.
도구 호출 인자 규칙:
- search_query: rewritten_query 그대로
- years, rounds, question_types, year_min, year_max, question_numbers: vertex_filter_output 그대로
- page_size: 3

도구 호출 후 응답: "검색 완료"만 출력.
""".strip(),
)
