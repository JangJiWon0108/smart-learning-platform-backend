"""
정보처리기사 실기 structData 기반 Vertex AI Search 검색 및 메타 필터링 수행

필터 조건: 스키마 내 필터 가능 필드 설정 필수
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from config.properties import Settings

from .discovery_session import vertex_discovery_authorized_session


# ─── 내부 유틸리티 및 필터 정의 ───────────────────────────────────────────────────

def _filter_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@dataclass(frozen=True)
class VertexExamSearchMetadata:
    """vector_store_vertexai.jsonl 내 structData와 대응하는 검색 필터 메타데이터"""

    years: tuple[int, ...] | None = None
    rounds: tuple[int, ...] | None = None
    question_types: tuple[str, ...] | None = None
    year_min: int | None = None
    year_max: int | None = None
    question_numbers: tuple[int, ...] | None = None


def build_vertex_exam_filter_expression(
    meta: VertexExamSearchMetadata | None,
) -> str | None:
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
            parts.append(
                f"question_number = {int(meta.question_numbers[0])}",
            )
        else:
            ors = " OR ".join(
                f"question_number = {int(n)}"
                for n in meta.question_numbers
            )
            parts.append(f"({ors})")

    if not parts:
        return None
    return " AND ".join(parts)


# ─── Vertex AI Search 핵심 검색 로직 ───────────────────────────────────────────────────

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
    # 1단계: 환경 변수 로드 및 설정값 초기화
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

    # 2단계: 검색 요청 페이로드 및 필터 표현식 구성
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

    # 3단계: 검색 임계치(Threshold) 및 데이터 스토어 사양 설정
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

    # 4단계: REST API 통신 및 검색 결과 반환
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


# ─── 모듈 테스트 실행부 ───────────────────────────────────────────────────────

if __name__ == "__main__":
    q = input("질문 >>> ").strip()
    if not q:
        print("비어 있음", file=sys.stderr)
        sys.exit(1)
    meta = VertexExamSearchMetadata(years=(2020,), question_types=("concept",))
    print(search_vertex_exam(q, exam_metadata=meta))
