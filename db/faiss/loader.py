from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from .store import FAISSVectorStore

_DEFAULT_MODEL = "/Users/n-jwjang/jjw/embedding/kure-v1"
_store: FAISSVectorStore | None = None


def get_store(
    store_dir: str | Path | None = None,
    jsonl_path: str | Path | None = None,
    model_name: str = _DEFAULT_MODEL,
) -> FAISSVectorStore:
    """모듈 레벨 싱글턴. 바이너리 인덱스 → jsonl 순서로 폴백하여 로드."""
    global _store
    if _store is not None:
        return _store

    if store_dir is not None:
        p = Path(store_dir)
        if (p / "index.faiss").exists():
            _store = FAISSVectorStore.load(p, model_name=model_name)
            return _store

    if jsonl_path is not None:
        p = Path(jsonl_path)
        if p.exists():
            _store = _load_from_jsonl(p, model_name)
            return _store

    _store = FAISSVectorStore(model_name=model_name)
    return _store


def _load_from_jsonl(path: Path, model_name: str) -> FAISSVectorStore:
    """사전 계산된 임베딩 jsonl에서 FAISS 인덱스를 구성한다."""
    texts: list[str] = []
    metadatas: list[dict] = []
    embeddings: list[list[float]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            texts.append(item["content"])
            metadatas.append(item["metadata"])
            embeddings.append(item["embedding"])

    store = FAISSVectorStore(model_name=model_name)
    if not texts:
        return store

    vecs = np.array(embeddings, dtype=np.float32)
    store._dim = vecs.shape[1]
    store._index = faiss.IndexFlatL2(store._dim)
    store._index.add(vecs)
    store._documents = texts
    store._metadata = metadatas
    return store
