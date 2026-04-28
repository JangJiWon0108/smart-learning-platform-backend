"""
문제 추천을 위한 Vertex AI Search 검색 노드.

filter_agent가 생성한 검색 조건으로 Vertex AI Search MCP 서버를 실행하고
결과를 다음 에이전트가 사용할 수 있는 형태로 변환합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import AsyncGenerator
from typing import Any

from google.adk import Event

from mcp_server.vertexai_search.client import search_exam_questions
from smart_learning_agent.schemas.curator_output import VertexFilterOutput


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
async def vertex_search_func(
    vertex_filter_output: Any,
    rewritten_query: str = "",
) -> AsyncGenerator[Event, None]:
    """
    filter_agent가 생성한 검색 조건으로 Vertex AI Search MCP 서버를 실행합니다.

    Args:
        vertex_filter_output: VertexFilterOutput 객체 또는 dict 형태의 검색 조건
        rewritten_query: Vertex AI Search 시맨틱 검색에 그대로 사용할 재작성 질문

    Yields:
        검색 결과를 포함하는 Event

    state에 저장되는 값:
        - rec_search_results: 검색된 문제 목록 (큐레이션 노드가 사용)
        - rec_query: 검색에 사용한 재작성 질문 텍스트
        - rec_subject: 검색한 문제 유형/과목
    """
    # 1단계: 입력 데이터(filter) 정규화
    if isinstance(vertex_filter_output, dict):
        filter_out = VertexFilterOutput.model_validate(vertex_filter_output)
    else:
        filter_out = vertex_filter_output

    search_query = rewritten_query.strip()

    # 2단계: MCP 서버를 통해 Vertex AI Search 검색 실행
    mcp_response = await search_exam_questions(
        search_query=search_query,
        years=filter_out.years,
        rounds=filter_out.rounds,
        question_types=filter_out.question_types,
        year_min=filter_out.year_min,
        year_max=filter_out.year_max,
        question_numbers=filter_out.question_numbers,
        page_size=3,  # 최대 3개 문제 추천
    )

    # 3단계: 결과 가공 및 응답 이벤트 생성
    if filter_out.question_types:
        subject_display = ", ".join(filter_out.question_types)
    else:
        subject_display = "전체"

    yield Event(
        state={
            "rec_search_results": mcp_response.get("results", []),
            "rec_query": search_query,
            "rec_subject": subject_display,
        }
    )
