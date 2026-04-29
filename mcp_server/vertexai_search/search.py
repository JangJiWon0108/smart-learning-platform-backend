"""
정보처리기사 실기 추천용 Vertex AI Search 모듈.

책임 분리: 필터 expression 조립 → Discovery 요청 구성·POST → chunk 응답을 추천용 dict로 변환.
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import re
from dataclasses import dataclass
from typing import Any

from config.properties import Settings

from .discovery_session import vertex_discovery_authorized_session
from .schemas import SearchExamQuestionsResponse


# ─── 데이터 모델 ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VertexExamSearchMetadata:
    """
    structData 필드와 대응하는 검색 메타(연·회차·유형·문항).

    Attributes:
        years: 특정 연도 필터
        rounds: 특정 회차 필터
        question_types: 문제 유형 필터
        year_min: 최소 연도
        year_max: 최대 연도
        question_numbers: 문항 번호 필터
    """

    years: tuple[int, ...] | None = None
    rounds: tuple[int, ...] | None = None
    question_types: tuple[str, ...] | None = None
    year_min: int | None = None
    year_max: int | None = None
    question_numbers: tuple[int, ...] | None = None


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _extract_exam_section(content: str, marker: str) -> str:
    """chunk 본문에서 `[marker]` 블록만 추출. 없으면 빈 문자열."""
    match = re.search(
        rf"(?:^|\n)\[{re.escape(marker)}\]\s*(.*?)(?=\n\[(?:문제|정답|해설)\]|\Z)",
        content,
        flags=re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _split_exam_content(content: str) -> tuple[str, str, str]:
    """chunk content → (문제, 정답, 해설). `[문제]` 없으면 전체를 문제로."""
    question = _extract_exam_section(content, "문제") or content.strip()
    answer = _extract_exam_section(content, "정답")
    explanation = _extract_exam_section(content, "해설")
    return question, answer, explanation


def _filter_string_literal(value: str) -> str:
    """filter 문자열 리터럴 이스케이프."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _number_equals_filter(field: str, values: tuple[int, ...] | None) -> str | None:
    """숫자 필드 equals(단일 또는 OR) filter 조각."""
    if not values:
        return None
    if len(values) == 1:
        return f"{field} = {int(values[0])}"
    return "(" + " OR ".join(f"{field} = {int(value)}" for value in values) + ")"


# ─── 필터 expression ───────────────────────────────────────────────────────
def build_vertex_exam_filter_expression(
    meta: VertexExamSearchMetadata | None,
) -> str | None:
    """
    메타데이터 → Discovery `filter` 문자열. 조건 없으면 None.

    Args:
        meta: 연·회차·유형·문항 메타

    Returns:
        AND로 연결된 filter expression 또는 None
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
        literals = ", ".join(_filter_string_literal(t) for t in meta.question_types)
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


# ─── Discovery 요청 구성 ─────────────────────────────────────────────────
# 실제 Vertex AI Search 검색 요청 (파라미터 조립)
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
    Discovery `servingConfigs/default_search:search` POST. 원본 JSON dict 반환.

    Args:
        search_query: 시맨틱 검색어
        exam_metadata: structData 기반 필터
        project_id: GCP 프로젝트. 빈 문자열이면 Settings
        location: Discovery 리전. 빈 문자열이면 Settings
        engine_id: 엔진 ID. 빈 문자열이면 Settings
        data_store_id: data store ID. None이면 Settings
        user_pseudo_id: Discovery userPseudoId
        relevance_threshold: 키워드 관련도 임계치
        semantic_relevance_threshold: 시맨틱 관련도 임계치
        page_size: pageSize

    Returns:
        Discovery Search API 원본 응답 dict
    """
    # 1단계: 프로젝트·리전·엔진 후보 값 확정
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

    # 2단계: 요청 본문
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

    # 3단계: POST 및 응답
    session.headers["X-Goog-User-Project"] = project_id
    url = (
        "https://discoveryengine.googleapis.com/v1alpha/"
        f"projects/{project_id}/locations/{discovery_location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_search:search"
    )
    response = session.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


# ─── 응답 파싱 ─────────────────────────────────────────────────────────────
def parse_vertex_results(raw_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Discovery `results` → 추천 후속 처리용 dict 리스트.

    Args:
        raw_response: Search API 원본 JSON

    Returns:
        문제·정답·해설·메타·score 키를 가진 dict 목록
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


# ─── MCP tool 구현 ─────────────────────────────────────────────────────────
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
    기출 검색 한 번에 끝: 설정 로드 → REST → 파싱 → `SearchExamQuestionsResponse` dump.

    Args:
        search_query: 시맨틱 검색어
        years: 연도 필터
        rounds: 회차 필터
        question_types: 유형 필터
        year_min: 최소 연도
        year_max: 최대 연도
        question_numbers: 문항 번호 필터
        page_size: 결과 개수 상한
        user_pseudo_id: userPseudoId
        relevance_threshold: 키워드 관련도 임계치
        semantic_relevance_threshold: 시맨틱 관련도 임계치

    Returns:
        MCP tool과 동일 키를 가진 응답 dict
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
    raw_response = search_vertex_exam(
        search_query.strip(),
        exam_metadata=metadata,
        project_id=settings.PROJECT_ID,
        location=settings.VERTEX_AI_SEARCH_LOCATION or settings.LOCATION,
        engine_id=settings.ENGINE_ID or "",
        user_pseudo_id=user_pseudo_id,
        relevance_threshold=relevance_threshold,
        semantic_relevance_threshold=semantic_relevance_threshold,
        page_size=page_size,
    )
    response = SearchExamQuestionsResponse(
        results=parse_vertex_results(raw_response),
        query=search_query.strip(),
        filter_expression=build_vertex_exam_filter_expression(metadata),
    )
    return response.model_dump()
