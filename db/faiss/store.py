from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


_LOCAL_EMBEDDING_PATH = "/Users/n-jwjang/jjw/embedding/kure-v1"


class FAISSVectorStore:
    """
    faiss-cpu + sentence-transformers 기반 벡터 스토어.
    메타데이터를 별도로 보관하고 post-filter 방식으로 필터링한다.
    """

    def __init__(self, model_name: str = _LOCAL_EMBEDDING_PATH):
        self._encoder = SentenceTransformer(model_name)
        self._dim: int | None = None
        self._index: faiss.Index | None = None
        self._documents: list[str] = []
        self._metadata: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 색인 구축
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """텍스트와 메타데이터를 벡터화하여 인덱스에 추가한다."""
        if not texts:
            return

        if metadatas is None:
            metadatas = [{} for _ in texts]

        if len(texts) != len(metadatas):
            raise ValueError("texts와 metadatas 길이가 일치해야 합니다.")

        vectors = self._encode(texts)

        if self._index is None:
            self._dim = vectors.shape[1]
            self._index = faiss.IndexFlatL2(self._dim)

        self._index.add(vectors)
        self._documents.extend(texts)
        self._metadata.extend(metadatas)

    # ------------------------------------------------------------------
    # 검색
    # ------------------------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
        fetch_k: int = 100,
    ) -> list[tuple[str, dict[str, Any], float]]:
        """
        쿼리와 유사한 문서를 반환한다.

        filter가 있으면 fetch_k개를 먼저 검색한 뒤 메타데이터 조건을 적용한다.
        결과: [(text, metadata, l2_distance), ...]  거리 오름차순 정렬.

        Args:
            query: 검색 쿼리 문자열
            k: 반환할 최종 문서 수
            filter: 메타데이터 등가 조건 (예: {"subject": "네트워크", "difficulty": "hard"})
            fetch_k: 필터 적용 전 후보 문서 수. filter 사용 시 k보다 충분히 크게 설정할 것.
        """
        if self._index is None:
            return []

        n_total = len(self._documents)
        search_k = min(fetch_k if filter else k, n_total)

        query_vec = self._encode([query])
        distances, indices = self._index.search(query_vec, search_k)

        results: list[tuple[str, dict[str, Any], float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata[idx]
            if filter and not _matches_filter(meta, filter):
                continue
            results.append((self._documents[idx], meta, float(dist)))
            if len(results) >= k:
                break

        return results

    # ------------------------------------------------------------------
    # 영속화
    # ------------------------------------------------------------------

    def save(self, directory: str | Path) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path / "index.faiss"))
        with open(path / "store.pkl", "wb") as f:
            pickle.dump(
                {
                    "documents": self._documents,
                    "metadata": self._metadata,
                    "dim": self._dim,
                },
                f,
            )

    @classmethod
    def load(
        cls,
        directory: str | Path,
        model_name: str = _LOCAL_EMBEDDING_PATH,
    ) -> "FAISSVectorStore":
        path = Path(directory)
        store = cls(model_name=model_name)
        store._index = faiss.read_index(str(path / "index.faiss"))
        with open(path / "store.pkl", "rb") as f:
            data = pickle.load(f)
        store._documents = data["documents"]
        store._metadata = data["metadata"]
        store._dim = data["dim"]
        return store

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------

    def _encode(self, texts: list[str]) -> np.ndarray:
        vecs = self._encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vecs.astype(np.float32)

    def __len__(self) -> int:
        return len(self._documents)


def _matches_filter(metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
    """
    모든 filter 조건을 만족하면 True.

    지원 형식(정형 메타데이터용):
    - 등가: {"year": 2024, "question_type": "code"}
    - 포함: {"year": [2023, 2024]}  (iterable이면 value in iterable)
    - 연산자: {"year": {"$gte": 2023, "$lte": 2025}}
      - $eq, $ne, $in, $nin, $gt, $gte, $lt, $lte, $contains, $regex
    - 함수: {"year": lambda v, meta: v is not None and v >= 2023}

    주의:
    - `question`(문항 텍스트) 기반 필터는 적용하지 않는다. (들어와도 무시)
      문맥 검색은 임베딩/시맨틱 서치로 처리한다.
    """
    import re
    from collections.abc import Callable, Iterable

    def _op_match(actual: Any, cond: Any) -> bool:
        # callable predicate
        if isinstance(cond, Callable):
            return bool(cond(actual, metadata))

        # operator dict
        if isinstance(cond, dict):
            for op, expected in cond.items():
                if op == "$eq":
                    if actual != expected:
                        return False
                elif op == "$ne":
                    if actual == expected:
                        return False
                elif op == "$in":
                    if actual not in expected:
                        return False
                elif op == "$nin":
                    if actual in expected:
                        return False
                elif op == "$gt":
                    if actual is None or actual <= expected:
                        return False
                elif op == "$gte":
                    if actual is None or actual < expected:
                        return False
                elif op == "$lt":
                    if actual is None or actual >= expected:
                        return False
                elif op == "$lte":
                    if actual is None or actual > expected:
                        return False
                elif op == "$contains":
                    # 문자열/리스트 등에서 포함 여부
                    if actual is None:
                        return False
                    try:
                        if expected not in actual:
                            return False
                    except TypeError:
                        return False
                elif op == "$regex":
                    if actual is None:
                        return False
                    if re.search(str(expected), str(actual)) is None:
                        return False
                else:
                    raise ValueError(f"지원하지 않는 filter 연산자: {op}")
            return True

        # iterable membership (문자열은 제외)
        if isinstance(cond, Iterable) and not isinstance(cond, (str, bytes)):
            return actual in cond

        return actual == cond

    for key, condition in filter.items():
        if key == "question":
            continue
        if not _op_match(metadata.get(key), condition):
            return False
    return True
