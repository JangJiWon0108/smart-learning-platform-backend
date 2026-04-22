from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from sentence_transformers import SentenceTransformer
from vertex_ai_search.gemini_question_classifier import (  # noqa: E402
    ExamQuestionLabels,
    classify_exam_questions_parallel,
)


@dataclass(frozen=True)
class BuildArgs:
    input_jsonl: Path
    output_jsonl: Path
    model: str
    batch_size: int
    limit: int | None


def _build_content(question: str, answer: str, explanation: str) -> str:
    parts: list[str] = []
    parts.append(f"[문제] {question}".rstrip())
    parts.append(f"[정답] {answer}".rstrip())
    if explanation and explanation.strip():
        parts.append(f"[해설] {explanation}".rstrip())
    return "\n".join(parts)


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _resolve_default_model() -> str:
    """
    - EMBEDDING_MODEL_PATH 환경변수가 있으면 그 값을 우선(로컬 경로/모델명 모두 허용)
    - 로컬 경로 `/Users/n-jwjang/jjw/embedding`이 존재하면 그 경로 사용
    - 아니면 백엔드 기본값과 동일한 HF 모델명 사용
    """
    import os

    env = os.getenv("EMBEDDING_MODEL_PATH")
    if env:
        return env

    local = Path("/Users/n-jwjang/jjw/embedding")
    if local.exists():
        # `SentenceTransformer`는 보통 `config.json`이 있는 HF 디렉토리를 기대한다.
        if (local / "config.json").exists():
            return str(local)
        for child in sorted(p for p in local.iterdir() if p.is_dir()):
            if (child / "config.json").exists():
                return str(child)

    return str(Path("/Users/n-jwjang/jjw/embedding/kure-v1"))


def _parse_args() -> BuildArgs:
    parser = argparse.ArgumentParser(
        description="기출 jsonl을 임베딩해서 data/vector_store.jsonl을 재생성합니다."
    )
    parser.add_argument(
        "--input",
        dest="input_jsonl",
        type=Path,
        default=Path("data/정보처리기사_실기_기출문제.jsonl"),
        help="입력 jsonl 경로 (기본: data/정보처리기사_실기_기출문제.jsonl)",
    )
    parser.add_argument(
        "--output",
        dest="output_jsonl",
        type=Path,
        default=Path("data/vector_store.jsonl"),
        help="출력 jsonl 경로 (기본: data/vector_store.jsonl)",
    )
    parser.add_argument(
        "--model",
        dest="model",
        type=str,
        default=_resolve_default_model(),
        help="SentenceTransformer 모델명 또는 로컬 경로",
    )
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=64)
    parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=None,
        help="디버깅용: 앞에서 N개만 처리",
    )

    ns = parser.parse_args()
    if ns.batch_size <= 0:
        raise SystemExit("--batch-size는 1 이상이어야 합니다.")
    if ns.limit is not None and ns.limit <= 0:
        raise SystemExit("--limit는 1 이상이어야 합니다.")

    return BuildArgs(
        input_jsonl=ns.input_jsonl,
        output_jsonl=ns.output_jsonl,
        model=ns.model,
        batch_size=ns.batch_size,
        limit=ns.limit,
    )


def _build_metadata(row: dict[str, Any], labels: ExamQuestionLabels) -> dict[str, Any]:
    explanation = str(row.get("explanation", "") or "").strip()
    images = row.get("images") or []

    meta: dict[str, Any] = {
        "id": row.get("id"),
        "year": row.get("year"),
        "round": row.get("round"),
        "exam_title": row.get("exam_title"),
        "question_number": row.get("question_number"),
        "question": row.get("question", ""),
        "answer": row.get("answer", ""),
        "explanation": row.get("explanation", ""),
        "source_url": row.get("source_url", ""),
        "crawled_at": row.get("crawled_at", ""),
        "has_image": bool(row.get("has_image", bool(images))),
        "has_explanation": bool(explanation),
        **labels.as_metadata_fields(),
    }
    return meta


def main() -> None:
    args = _parse_args()

    if not args.input_jsonl.exists():
        raise SystemExit(f"입력 파일이 없습니다: {args.input_jsonl}")

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    encoder = SentenceTransformer(args.model)

    source_rows: list[dict[str, Any]] = []
    contents: list[str] = []

    for i, row in enumerate(_iter_jsonl(args.input_jsonl), start=1):
        source_rows.append(row)
        contents.append(
            _build_content(
                question=str(row.get("question", "")),
                answer=str(row.get("answer", "")),
                explanation=str(row.get("explanation", "")),
            )
        )

        if args.limit is not None and i >= args.limit:
            break

    questions = [str(r.get("question", "")) for r in source_rows]
    label_list = classify_exam_questions_parallel(questions, max_workers=4)
    rows: list[dict[str, Any]] = []
    for row, content, lab in zip(source_rows, contents, label_list, strict=True):
        rows.append(
            {"content": content, "metadata": _build_metadata(row, lab)},
        )

    with args.output_jsonl.open("w", encoding="utf-8") as out:
        for start in range(0, len(contents), args.batch_size):
            batch_texts = contents[start : start + args.batch_size]
            emb = encoder.encode(
                batch_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            for j, vec in enumerate(emb):
                item = rows[start + j] | {"embedding": vec.astype("float32").tolist()}
                out.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

