"""
정보처리기사 실기 원본 JSONL → data/vector_store_vertexai.jsonl.

각 문제를 Gemini로 분류(concept/code + 언어)해서 structData에 포함.
이미지 의존 행은 제외.

실행 (backend 디렉터리에서):
  uv run python -m vertex_ai_search.build_vertex_store_vertexai_jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator, TextIO

from config.properties import BASE_DIR
from log.logger import get_logger

from .gemini_question_classifier import classify_question

_logger = get_logger("build_vertexai_jsonl")


def _document_id(legacy_id: str) -> str:
    s = str(legacy_id).strip()
    m = re.fullmatch(r"(\d{4})_(\d{1,2})_(\d{1,3})", s)
    if m:
        y, r, q = m.groups()
        raw = f"doc-y{y}-r{int(r):02d}-q{int(q):02d}"
    else:
        raw = re.sub(r"[^A-Za-z0-9-]", "-", s)
        raw = re.sub(r"-+", "-", raw).strip("-").lower()
        if not raw:
            raise ValueError(f"empty id from {legacy_id!r}")
        if raw[0].isdigit():
            raw = "doc-" + raw
    raw = re.sub(r"[^a-z0-9_-]", "-", raw.lower())
    raw = re.sub(r"-+", "-", raw).strip("-")
    return raw[:63].rstrip("-_") if len(raw) > 63 else raw


def _build_content(row: dict[str, Any]) -> str:
    parts = [f"[문제] {row.get('question', '')}".rstrip()]
    parts.append(f"[정답] {row.get('answer', '')}".rstrip())
    exp = str(row.get("explanation", "") or "").strip()
    if exp:
        parts.append(f"[해설] {exp}".rstrip())
    return "\n".join(parts)


def _has_image(row: dict[str, Any]) -> bool:
    return bool(row.get("has_image") or row.get("images") or row.get("answer_images"))


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path} 라인 {lineno}: {e}") from e


def build_jsonl(input_path: Path, output: TextIO) -> tuple[int, int]:
    written = skipped = 0
    for row in _iter_jsonl(input_path):
        if _has_image(row):
            skipped += 1
            continue

        labels = classify_question(str(row.get("question", "")))

        doc_id = _document_id(str(row.get("id", "")))
        record = {
            "documentId": doc_id,
            "content": _build_content(row),
            "structData": {
                "id": doc_id,
                "year": int(row["year"]) if row.get("year") is not None else 0,
                "round": int(row["round"]) if row.get("round") is not None else 0,
                "exam_title": str(row.get("exam_title", "")),
                "question_number": int(row["question_number"]) if row.get("question_number") is not None else 0,
                "source_url": str(row.get("source_url", "")),
                **labels,
            },
        }
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
        written += 1
        _logger.info("[%d] %s → %s", written, row.get("id", "?"), labels["question_type"])

    _logger.info("완료: %d건 기록 / %d건 스킵(이미지)", written, skipped)
    return written, skipped


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, nargs="?", default=None)
    p.add_argument("-o", "--output", type=Path, default=None)
    args = p.parse_args()

    inp = args.input or (BASE_DIR / "data" / "정보처리기사_실기_기출문제.jsonl")
    out = args.output or (BASE_DIR / "data" / "vector_store_vertexai.jsonl")
    if not inp.is_file():
        print(f"입력 없음: {inp}", file=sys.stderr)
        return 1

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        n, sk = build_jsonl(inp, fh)
    print(f"완료: {n}건 (이미지 스킵 {sk}) → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
