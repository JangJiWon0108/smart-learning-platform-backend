from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .store import FAISSVectorStore


@dataclass
class SearchResult:
    text: str
    metadata: dict[str, Any]
    distance: float
    score: float = field(init=False)

    def __post_init__(self) -> None:
        # L2 거리를 0~1 유사도 점수로 변환 (거리 0 → 1.0)
        self.score = 1.0 / (1.0 + self.distance)


def search_with_filter(
    store: FAISSVectorStore,
    query: str,
    k: int = 4,
    filter: dict[str, Any] | None = None,
    fetch_k: int = 100,
) -> list[SearchResult]:
    """
    메타데이터 필터를 적용한 유사도 검색.

    Examples:
        # 연도 + 유형 필터
        results = search_with_filter(
            store, "포인터 역참조",
            filter={"year": {"$gte": 2023}, "question_type": "code"},
        )

        # 특정 연도 + 회차 필터
        results = search_with_filter(
            store, "TCP 3-way handshake",
            filter={"year": 2023, "round": {"$in": [1, 2]}},
        )

        # 필터 없이 단순 유사도 검색
        results = search_with_filter(store, "SQL JOIN 서브쿼리")
    """
    raw = store.similarity_search(query=query, k=k, filter=filter, fetch_k=fetch_k)
    return [SearchResult(text=text, metadata=meta, distance=dist) for text, meta, dist in raw]
