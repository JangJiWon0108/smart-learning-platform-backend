from typing import Any

from google.adk import Event

from config.properties import Settings
from schemas.curator import VertexFilterOutput
from vertex_ai_search.search import VertexExamSearchMetadata, retrieve_vertexai_search

_settings = Settings()


def _parse_vertex_results(raw: dict) -> list[dict]:
    out = []
    for r in raw.get("results", []):
        chunk = r.get("chunk", {})
        content = chunk.get("content", "")
        struct = chunk.get("documentMetadata", {}).get("structData", {})
        score = r.get("rankSignals", {}).get("relevanceScore", 0.0)
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        out.append({
            "question": content,
            "answer": "",
            "explanation": "",
            "year": struct.get("year"),
            "round": struct.get("round"),
            "question_type": struct.get("question_type", ""),
            "question_number": struct.get("question_number"),
            "score": round(score, 4),
        })
    return out


def vertex_search_func(vertex_filter_output: Any) -> None:
    """filter_agent 출력을 바탕으로 Vertex AI Search를 수행한다."""
    if isinstance(vertex_filter_output, dict):
        filter_out = VertexFilterOutput.model_validate(vertex_filter_output)
    else:
        filter_out = vertex_filter_output

    meta = VertexExamSearchMetadata(
        years=tuple(filter_out.years) or None,
        rounds=tuple(filter_out.rounds) or None,
        question_types=tuple(filter_out.question_types) or None,
        year_min=filter_out.year_min,
        year_max=filter_out.year_max,
        question_numbers=tuple(filter_out.question_numbers) or None,
    )

    raw = retrieve_vertexai_search(
        project_id=_settings.PROJECT_ID,
        location=_settings.VERTEX_AI_SEARCH_LOCATION or _settings.LOCATION,
        engine_id=_settings.ENGINE_ID or "",
        search_query=filter_out.query_text,
        exam_metadata=meta,
        page_size=3,
    )

    subject = ", ".join(filter_out.question_types) if filter_out.question_types else "전체"
    yield Event(state={
        "rec_search_results": _parse_vertex_results(raw),
        "rec_keywords": filter_out.query_text,
        "rec_subject": subject,
    })
