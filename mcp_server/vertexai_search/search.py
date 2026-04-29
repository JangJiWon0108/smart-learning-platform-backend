"""
정보처리기사 실기 문제 추천용 Vertex AI Search 검색 모듈.

Discovery Engine 검색 요청을 생성하고, 기출 문제 structData 메타데이터 기반 필터를
적용한 뒤, MCP tool 응답에 맞는 추천 결과 형태로 파싱합니다.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from dataclasses import dataclass
import re
from typing import Any

from config.properties import Settings

from .discovery_session import vertex_discovery_authorized_session
from .schemas import SearchExamQuestionsResponse


# ─── 검색 메타데이터 모델 ───────────────────────────────────────────────────
@dataclass(frozen=True)
class VertexExamSearchMetadata:
    """
    Vertex AI Search structData와 대응하는 검색 필터 메타데이터.

    Attributes:
        years: 특정 연도 필터
        rounds: 특정 회차 필터
        question_types: 문제 유형 필터
        year_min: 최소 연도 필터
        year_max: 최대 연도 필터
        question_numbers: 특정 문항 번호 필터
    """

    years: tuple[int, ...] | None = None
    rounds: tuple[int, ...] | None = None
    question_types: tuple[str, ...] | None = None
    year_min: int | None = None
    year_max: int | None = None
    question_numbers: tuple[int, ...] | None = None


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _extract_exam_section(content: str, marker: str) -> str:
    """
    `[문제]`, `[정답]`, `[해설]` 마커에 해당하는 본문 영역을 추출합니다.

    Args:
        content: Vertex AI Search chunk content 원문
        marker: 추출할 섹션 마커 이름

    Returns:
        마커에 해당하는 섹션 텍스트. 없으면 빈 문자열
    """
    match = re.search(
        rf"(?:^|\n)\[{re.escape(marker)}\]\s*(.*?)(?=\n\[(?:문제|정답|해설)\]|\Z)",
        content,
        flags=re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _split_exam_content(content: str) -> tuple[str, str, str]:
    """
    검색 chunk content를 문제, 정답, 해설 텍스트로 분리합니다.

    Args:
        content: Vertex AI Search chunk content 원문

    Returns:
        `(문제, 정답, 해설)` 튜플
    """
    question = _extract_exam_section(content, "문제") or content.strip()
    answer = _extract_exam_section(content, "정답")
    explanation = _extract_exam_section(content, "해설")
    return question, answer, explanation


def _filter_string_literal(value: str) -> str:
    """Discovery Engine filter 문자열에 사용할 문자열 리터럴을 이스케이프합니다."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _number_equals_filter(field: str, values: tuple[int, ...] | None) -> str | None:
    """숫자 필드의 단일/복수 equals 조건을 Discovery Engine filter로 변환합니다."""
    if not values:
        return None
    if len(values) == 1:
        return f"{field} = {int(values[0])}"
    return "(" + " OR ".join(f"{field} = {int(value)}" for value in values) + ")"


# ─── 필터 expression 구성 ───────────────────────────────────────────────────
def build_vertex_exam_filter_expression(
    meta: VertexExamSearchMetadata | None,
) -> str | None:
    """
    검색 메타데이터를 Discovery Engine filter expression으로 변환합니다.

    Args:
        meta: 연도, 회차, 문제 유형, 문항 번호 필터 메타데이터

    Returns:
        Discovery Engine filter expression. 필터가 없으면 None
    """
    if meta is None:
        return None
    parts: list[str] = []

    year_filter = _number_equals_filter("year", meta.years)
    if year_filter:
        parts.append(year_filter)

    if meta.year_min is not None:
        parts.append(f"year >= {int(meta.year_min)}")
    if meta.year_max is not None:
        parts.append(f"year <= {int(meta.year_max)}")

    round_filter = _number_equals_filter("round", meta.rounds)
    if round_filter:
        parts.append(round_filter)

    if meta.question_types:
        literals = ", ".join(
            _filter_string_literal(t) for t in meta.question_types
        )
        parts.append(f"question_type: ANY({literals})")

    question_number_filter = _number_equals_filter(
        "question_number",
        meta.question_numbers,
    )
    if question_number_filter:
        parts.append(question_number_filter)

    if not parts:
        return None
    return " AND ".join(parts)


# ─── Discovery 검색 요청 ────────────────────────────────────────────────────
def search_vertex_exam(
    search_query: str,
    *,
    exam_metadata: VertexExamSearchMetadata | None = None,
    project_id: str = "",
    location: str = "",
    engine_id: str = "",
    data_store_id: str | None = None,
    user_pseudo_id: str | None = None,
    relevance_threshold: str | None = None,
    semantic_relevance_threshold: float | None = None,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    Vertex AI Search REST API를 호출하고 원본 Discovery Engine 응답을 반환합니다.

    Args:
        search_query: Vertex AI Search에 전달할 시맨틱 검색어
        exam_metadata: structData 기반 메타 필터
        project_id: GCP 프로젝트 ID. 비어 있으면 Settings 사용
        location: Discovery Engine 리전. 비어 있으면 Settings 사용
        engine_id: Discovery Engine serving engine ID
        data_store_id: 검색 대상 data store ID
        user_pseudo_id: Discovery Engine 개인화/추적용 사용자 식별자
        relevance_threshold: 키워드 검색 관련도 임계치
        semantic_relevance_threshold: 시맨틱 검색 관련도 임계치
        page_size: 검색 결과 개수

    Returns:
        Discovery Engine search API 원본 JSON 응답
    """
    cfg = Settings()
    project_id = project_id or cfg.PROJECT_ID
    _cfg_loc = (cfg.VERTEX_AI_SEARCH_LOCATION or "").strip() or cfg.LOCATION
    discovery_location = (
        location.strip()
        if isinstance(location, str) and location.strip()
        else _cfg_loc.strip()
    )
    engine_id = engine_id or (cfg.ENGINE_ID or "")

    filter_expr = build_vertex_exam_filter_expression(exam_metadata)
    session = vertex_discovery_authorized_session()

    payload: dict[str, Any] = {
        "query": search_query,
        "pageSize": page_size,
        "offset": 0,
        "relevanceScoreSpec": {"returnRelevanceScore": True},
        "contentSearchSpec": {"searchResultMode": "CHUNKS"},
    }
    if filter_expr:
        payload["filter"] = filter_expr
    if user_pseudo_id:
        payload["userPseudoId"] = user_pseudo_id

    relevance_threshold = relevance_threshold or cfg.RELEVANCE_THRESHOLD
    semantic_threshold = (
        semantic_relevance_threshold
        if isinstance(semantic_relevance_threshold, (int, float))
        else cfg.SEMANTIC_RELEVANCE_THRESHOLD
    )
    payload["relevanceFilterSpec"] = {
        "keywordSearchThreshold": {"relevanceThreshold": relevance_threshold},
        "semanticSearchThreshold": {"semanticRelevanceThreshold": semantic_threshold},
    }

    resolved_data_store = (data_store_id or cfg.DATA_STORE_ID or "").strip() or None
    if resolved_data_store:
        payload["dataStoreSpecs"] = [
            {
                "dataStore": (
                    f"projects/{project_id}/locations/{discovery_location}"
                    "/collections/default_collection/dataStores/"
                    f"{resolved_data_store}"
                ),
            },
        ]

    session.headers["X-Goog-User-Project"] = project_id
    url = (
        "https://discoveryengine.googleapis.com/v1alpha/"
        f"projects/{project_id}/locations/{discovery_location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_search:search"
    )
    response = session.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def retrieve_vertexai_search(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
    categories: list[str] | None = None,
    user_pseudo_id: str | None = None,
    num_previous_chunks: int = 0,
    num_next_chunks: int = 0,
    data_store_id: str | None = None,
    relevance_threshold: str | None = None,
    semantic_relevance_threshold: float | None = None,
    exam_metadata: VertexExamSearchMetadata | None = None,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    기존 호출부 호환용 Vertex AI Search 검색 래퍼입니다.

    Args:
        project_id: GCP 프로젝트 ID
        location: Discovery Engine 리전
        engine_id: Discovery Engine serving engine ID
        search_query: Vertex AI Search에 전달할 시맨틱 검색어
        categories: exam_metadata가 없을 때 question_types로 변환할 카테고리
        user_pseudo_id: Discovery Engine 개인화/추적용 사용자 식별자
        num_previous_chunks: 현재 미사용. 기존 인터페이스 호환용
        num_next_chunks: 현재 미사용. 기존 인터페이스 호환용
        data_store_id: 검색 대상 data store ID
        relevance_threshold: 키워드 검색 관련도 임계치
        semantic_relevance_threshold: 시맨틱 검색 관련도 임계치
        exam_metadata: structData 기반 메타 필터
        page_size: 검색 결과 개수

    Returns:
        Discovery Engine search API 원본 JSON 응답
    """
    _ = (num_previous_chunks, num_next_chunks)
    meta = exam_metadata
    if meta is None and categories:
        meta = VertexExamSearchMetadata(question_types=tuple(categories))
    return search_vertex_exam(
        search_query,
        exam_metadata=meta,
        project_id=project_id,
        location=location,
        engine_id=engine_id,
        data_store_id=data_store_id,
        user_pseudo_id=user_pseudo_id,
        relevance_threshold=relevance_threshold,
        semantic_relevance_threshold=semantic_relevance_threshold,
        page_size=page_size,
    )


# ─── 검색 결과 파싱 ────────────────────────────────────────────────────────
def parse_vertex_results(raw_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Vertex AI Search 원본 응답을 추천 카드 생성에 필요한 dict 목록으로 변환합니다.

    Args:
        raw_response: Discovery Engine search API 원본 JSON 응답

    Returns:
        문제, 정답, 해설, 연도, 회차, 유형, 문항 번호, 점수를 담은 dict 목록
    """
    parsed_results: list[dict[str, Any]] = []

    for result in raw_response.get("results", []):
        chunk = result.get("chunk", {})
        question_text, answer_text, explanation_text = _split_exam_content(
            str(chunk.get("content", "") or "")
        )
        metadata = chunk.get("documentMetadata", {}).get("structData", {})

        raw_score = result.get("rankSignals", {}).get("relevanceScore", 0.0)
        try:
            relevance_score = float(raw_score)
        except (TypeError, ValueError):
            relevance_score = 0.0

        parsed_results.append(
            {
                "question": question_text,
                "answer": answer_text,
                "explanation": explanation_text,
                "year": metadata.get("year"),
                "round": metadata.get("round"),
                "question_type": metadata.get("question_type", ""),
                "question_number": metadata.get("question_number"),
                "score": round(relevance_score, 4),
            }
        )

    return parsed_results


def search_exam_questions(
    search_query: str,
    *,
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
    MCP tool에서 호출하는 기출 문제 검색 함수입니다.

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
        MCP tool 응답으로 반환할 파싱된 검색 결과 dict
    """
    settings = Settings()
    metadata = VertexExamSearchMetadata(
        years=tuple(years or ()) or None,
        rounds=tuple(rounds or ()) or None,
        question_types=tuple(question_types or ()) or None,
        year_min=year_min,
        year_max=year_max,
        question_numbers=tuple(question_numbers or ()) or None,
    )
    raw_response = retrieve_vertexai_search(
        project_id=settings.PROJECT_ID,
        location=settings.VERTEX_AI_SEARCH_LOCATION or settings.LOCATION,
        engine_id=settings.ENGINE_ID or "",
        search_query=search_query.strip(),
        user_pseudo_id=user_pseudo_id,
        relevance_threshold=relevance_threshold,
        semantic_relevance_threshold=semantic_relevance_threshold,
        exam_metadata=metadata,
        page_size=page_size,
    )
    response = SearchExamQuestionsResponse(
        results=parse_vertex_results(raw_response),
        query=search_query.strip(),
        filter_expression=build_vertex_exam_filter_expression(metadata),
    )
    return response.model_dump()
