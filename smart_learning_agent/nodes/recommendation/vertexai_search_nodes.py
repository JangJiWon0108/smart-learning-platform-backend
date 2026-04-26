"""
문제 추천을 위한 Vertex AI Search 검색 노드.

filter_agent가 생성한 검색 조건으로 Vertex AI Search를 실행하고
결과를 다음 에이전트가 사용할 수 있는 형태로 변환합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator
from typing import Any

from google.adk import Event

from config.properties import Settings
from smart_learning_agent.schemas.curator_output import VertexFilterOutput
from vertexai_search.search_vertexai import VertexExamSearchMetadata, retrieve_vertexai_search

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
# 설정은 모듈 로드 시 한 번만 읽어옵니다 (매 호출마다 읽으면 비효율적)
_settings = Settings()


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _parse_vertex_results(raw_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Vertex AI Search API 응답을 파싱해서 문제 정보 목록으로 변환합니다.

    Args:
        raw_response: Vertex AI Search API의 원시 응답 dict

    Returns:
        문제 정보 dict 목록. 각 항목은 question, answer, year, round 등을 포함.
    """
    parsed_results = []

    for result in raw_response.get("results", []):
        # chunk에 문제 텍스트와 메타데이터가 들어있습니다
        chunk = result.get("chunk", {})
        question_text = chunk.get("content", "")

        # structData에 year, round, question_type 등 구조화 데이터가 있습니다
        metadata = chunk.get("documentMetadata", {}).get("structData", {})

        # 관련도 점수 (0.0 ~ 1.0, 높을수록 검색어와 관련성 높음)
        raw_score = result.get("rankSignals", {}).get("relevanceScore", 0.0)
        try:
            relevance_score = float(raw_score)
        except (TypeError, ValueError):
            relevance_score = 0.0

        parsed_results.append({
            "question": question_text,
            "answer": "",           # Vertex Search에서는 정답을 반환하지 않음
            "explanation": "",      # 해설도 마찬가지
            "year": metadata.get("year"),
            "round": metadata.get("round"),
            "question_type": metadata.get("question_type", ""),
            "question_number": metadata.get("question_number"),
            "score": round(relevance_score, 4),
        })

    return parsed_results


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def vertex_search_func(
    vertex_filter_output: Any,
    rewritten_query: str = "",
) -> Generator[Event, None, None]:
    """
    filter_agent가 생성한 검색 조건으로 Vertex AI Search를 실행합니다.

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

    # 2단계: 검색 메타데이터 구성 (빈 리스트는 None으로 처리해서 필터 제거)
    search_metadata = VertexExamSearchMetadata(
        years=tuple(filter_out.years) or None,
        rounds=tuple(filter_out.rounds) or None,
        question_types=tuple(filter_out.question_types) or None,
        year_min=filter_out.year_min,
        year_max=filter_out.year_max,
        question_numbers=tuple(filter_out.question_numbers) or None,
    )

    # 3단계: Vertex AI Search API 호출 및 데이터 획득
    raw_response = retrieve_vertexai_search(
        project_id=_settings.PROJECT_ID,
        # VERTEX_AI_SEARCH_LOCATION이 비어있으면 기본 LOCATION 사용
        location=_settings.VERTEX_AI_SEARCH_LOCATION or _settings.LOCATION,
        engine_id=_settings.ENGINE_ID or "",
        search_query=search_query,
        exam_metadata=search_metadata,
        page_size=3,  # 최대 3개 문제 추천
    )

    # 4단계: 결과 가공 및 응답 이벤트 생성
    if filter_out.question_types:
        subject_display = ", ".join(filter_out.question_types)
    else:
        subject_display = "전체"

    yield Event(
        state={
            "rec_search_results": _parse_vertex_results(raw_response),
            "rec_query": search_query,
            "rec_subject": subject_display,
        }
    )
