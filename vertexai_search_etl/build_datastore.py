"""
정보처리기사 실기 원본 JSONL을 Vertex AI Search 적재용 NDJSON으로 변환합니다.
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

from .question_classifier import classify_question
from .schemas import DatastoreBuildResponse

_logger = get_logger("build_vertexai_jsonl")


def _document_id(legacy_id: str) -> str:
    text = str(legacy_id).strip()
    match = re.fullmatch(r"(\d{4})_(\d{1,2})_(\d{1,3})", text)
    if match:
        year, round_number, question_number = match.groups()
        raw = f"doc-y{year}-r{int(round_number):02d}-q{int(question_number):02d}"
    else:
        raw = re.sub(r"[^A-Za-z0-9-]", "-", text)
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
    explanation = str(row.get("explanation", "") or "").strip()
    if explanation:
        parts.append(f"[해설] {explanation}".rstrip())
    return "\n".join(parts)


def _has_image(row: dict[str, Any]) -> bool:
    return bool(row.get("has_image") or row.get("images") or row.get("answer_images"))


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        for lineno, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} 라인 {lineno}: {exc}") from exc


def build_jsonl(input_path: Path, output: TextIO) -> tuple[int, int]:
    """Build Vertex AI Search NDJSON records from the source question JSONL."""
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
        _logger.info("[%d] %s -> %s", written, row.get("id", "?"), labels["question_type"])

    _logger.info("완료: %d건 기록 / %d건 스킵(이미지)", written, skipped)
    return written, skipped


def build_vertexai_datastore(
    input_path: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Build a Vertex AI Search NDJSON file and return a summary."""
    source_path = Path(input_path) if input_path else BASE_DIR / "data" / "정보처리기사_실기_기출문제.jsonl"
    target_path = Path(output_path) if output_path else BASE_DIR / "data" / "vector_store_vertexai.jsonl"
    if not source_path.is_file():
        raise FileNotFoundError(f"입력 없음: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as file:
        written, skipped = build_jsonl(source_path, file)

    return DatastoreBuildResponse(
        input_path=str(source_path),
        output_path=str(target_path),
        written=written,
        skipped=skipped,
    ).model_dump()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", default=None)
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        result = build_vertexai_datastore(
            str(args.input) if args.input else None,
            str(args.output) if args.output else None,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"완료: {result['written']}건 "
        f"(이미지 스킵 {result['skipped']}) -> {result['output_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
