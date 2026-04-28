"""
정보처리기사 실기 structData 기반 Vertex AI Search 검색 및 메타 필터링 수행.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from config.properties import Settings

from .discovery_session import vertex_discovery_authorized_session
from .schemas import SearchExamQuestionsResponse


@dataclass(frozen=True)
class VertexExamSearchMetadata:
    """vector_store_vertexai.jsonl 내 structData와 대응하는 검색 필터 메타데이터."""

    years: tuple[int, ...] | None = None
    rounds: tuple[int, ...] | None = None
    question_types: tuple[str, ...] | None = None
    year_min: int | None = None
    year_max: int | None = None
    question_numbers: tuple[int, ...] | None = None


def _extract_exam_section(content: str, marker: str) -> str:
    match = re.search(
        rf"(?:^|\n)\[{re.escape(marker)}\]\s*(.*?)(?=\n\[(?:문제|정답|해설)\]|\Z)",
        content,
        flags=re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _split_exam_content(content: str) -> tuple[str, str, str]:
    question = _extract_exam_section(content, "문제") or content.strip()
    answer = _extract_exam_section(content, "정답")
    explanation = _extract_exam_section(content, "해설")
    return question, answer, explanation


def _filter_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_vertex_exam_filter_expression(
    meta: VertexExamSearchMetadata | None,
) -> str | None:
    """Build a Discovery Engine filter expression from exam metadata."""
    if meta is None:
        return None
    parts: list[str] = []

    if meta.years:
        if len(meta.years) == 1:
            parts.append(f"year = {int(meta.years[0])}")
        else:
            ors = " OR ".join(f"year = {int(y)}" for y in meta.years)
            parts.append(f"({ors})")

    if meta.year_min is not None:
        parts.append(f"year >= {int(meta.year_min)}")
    if meta.year_max is not None:
        parts.append(f"year <= {int(meta.year_max)}")

    if meta.rounds:
        if len(meta.rounds) == 1:
            parts.append(f"round = {int(meta.rounds[0])}")
        else:
            ors = " OR ".join(f"round = {int(r)}" for r in meta.rounds)
            parts.append(f"({ors})")

    if meta.question_types:
        literals = ", ".join(
            _filter_string_literal(t) for t in meta.question_types
        )
        parts.append(f"question_type: ANY({literals})")

    if meta.question_numbers:
        if len(meta.question_numbers) == 1:
            parts.append(f"question_number = {int(meta.question_numbers[0])}")
        else:
            ors = " OR ".join(
                f"question_number = {int(n)}"
                for n in meta.question_numbers
            )
            parts.append(f"({ors})")

    if not parts:
        return None
    return " AND ".join(parts)


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
    """Call Vertex AI Search and return the raw Discovery Engine response."""
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
    exam_metadata 기반 메타 필터링 수행.
    categories는 exam_metadata가 미지정된 경우에만 question_types로 자동 변환 처리.
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


def parse_vertex_results(raw_response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a raw Vertex AI Search response into recommendation-ready records."""
    parsed_results = []

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

        parsed_results.append({
            "question": question_text,
            "answer": answer_text,
            "explanation": explanation_text,
            "year": metadata.get("year"),
            "round": metadata.get("round"),
            "question_type": metadata.get("question_type", ""),
            "question_number": metadata.get("question_number"),
            "score": round(relevance_score, 4),
        })

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
    """Search exam questions and return parsed results for the learning agent."""
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
