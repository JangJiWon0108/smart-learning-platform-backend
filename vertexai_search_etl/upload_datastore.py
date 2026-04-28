"""Vertex AI Search 적재용 NDJSON을 Discovery Engine data store에 업로드합니다."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any

from config.properties import BASE_DIR, Settings

from .discovery_session import vertex_discovery_authorized_session
from .schemas import DatastoreUploadResponse, DatastoreValidationResponse

if TYPE_CHECKING:
    from google.auth.transport.requests import AuthorizedSession


def _branch_parent(cfg: Settings) -> str:
    if not cfg.PROJECT_ID or not cfg.DATA_STORE_ID:
        raise ValueError(".env 에 PROJECT_ID, DATA_STORE_ID 가 필요합니다.")
    branch = (cfg.VERTEX_AI_SEARCH_BRANCH or "0").strip() or "0"
    data_store = cfg.DATA_STORE_ID.strip()
    location = (cfg.VERTEX_AI_SEARCH_LOCATION.strip() or cfg.LOCATION).strip()
    return (
        f"projects/{cfg.PROJECT_ID}/locations/{location}"
        f"/collections/default_collection/dataStores/{data_store}/branches/{branch}"
    )


def _document_create_url(parent: str, document_id: str) -> str:
    query = urllib.parse.urlencode({"documentId": document_id})
    return f"https://discoveryengine.googleapis.com/v1beta/{parent}/documents?{query}"


def _document_upsert_url(parent: str, document_id: str) -> str:
    query = urllib.parse.urlencode({"allowMissing": "true"})
    return f"https://discoveryengine.googleapis.com/v1beta/{parent}/documents/{document_id}?{query}"


def _parse_ndjson_line(
    record: dict[str, Any],
) -> tuple[str, dict[str, Any], str | None]:
    if "structData" not in record or not isinstance(record["structData"], dict):
        raise ValueError("각 줄에 structData 객체가 있어야 합니다.")
    if record.get("documentId"):
        document_id = str(record["documentId"])
    elif record.get("id"):
        document_id = str(record["id"])
    else:
        raise ValueError("documentId 또는 id 가 필요합니다.")

    content_plain: str | None = None
    content = record.get("content")
    if isinstance(content, str) and content.strip():
        content_plain = content
    return document_id, dict(record["structData"]), content_plain


def _document_body(
    struct_data: dict[str, Any],
    content_plain: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"structData": struct_data}
    if content_plain is not None:
        body["content"] = {
            "mimeType": "text/plain",
            "rawBytes": base64.b64encode(content_plain.encode("utf-8")).decode("ascii"),
        }
    return body


def iter_records_from_ndjson(
    path: Path,
) -> list[tuple[str, dict[str, Any], str | None]]:
    """Read and validate Vertex AI Search NDJSON records."""
    rows: list[tuple[str, dict[str, Any], str | None]] = []
    with path.open(encoding="utf-8") as file:
        for lineno, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(_parse_ndjson_line(json.loads(line)))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"{path}:{lineno} {exc}") from exc
    return rows


def upload_all(
    session: "AuthorizedSession",
    cfg: Settings,
    records: list[tuple[str, dict[str, Any], str | None]],
    *,
    request_delay_sec: float,
) -> None:
    """Upload all records to Discovery Engine using create-or-update semantics."""
    parent = _branch_parent(cfg)
    session.headers["X-Goog-User-Project"] = cfg.PROJECT_ID
    for index, (doc_id, struct_data, content_plain) in enumerate(records, 1):
        body = _document_body(struct_data, content_plain)
        url = _document_create_url(parent, doc_id)
        response = session.post(url, json=body, timeout=120)
        if response.status_code == 409:
            url = _document_upsert_url(parent, doc_id)
            response = session.patch(url, json=body, timeout=120)
        if not response.ok:
            raise RuntimeError(
                f"UPSERT 실패 documentId={doc_id!r} "
                f"HTTP {response.status_code}: {response.text}",
            )

        if request_delay_sec > 0:
            time.sleep(request_delay_sec)
        if index % 50 == 0 or index == len(records):
            print(f"  업로드 {index}/{len(records)}")


def _default_jsonl_path(jsonl_path: str | None) -> Path:
    return Path(jsonl_path) if jsonl_path else Path(BASE_DIR) / "data" / "vector_store_vertexai.jsonl"


def validate_vertexai_datastore(jsonl_path: str | None = None) -> dict[str, Any]:
    """Validate a Vertex AI Search NDJSON file and return its record count."""
    path = _default_jsonl_path(jsonl_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일 없음: {path}")
    records = iter_records_from_ndjson(path)
    return DatastoreValidationResponse(
        jsonl_path=str(path),
        record_count=len(records),
    ).model_dump()


def upload_vertexai_datastore(
    jsonl_path: str | None = None,
    request_delay_sec: float = 0.0,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """Upload a Vertex AI Search NDJSON file."""
    path = _default_jsonl_path(jsonl_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일 없음: {path}")
    records = iter_records_from_ndjson(path)

    uploaded = False
    if not dry_run:
        if not confirm:
            raise ValueError("실제 업로드는 dry_run=False, confirm=True가 모두 필요합니다.")
        session = vertex_discovery_authorized_session()
        upload_all(
            session,
            Settings(),
            records,
            request_delay_sec=max(0.0, request_delay_sec),
        )
        uploaded = True

    return DatastoreUploadResponse(
        jsonl_path=str(path),
        record_count=len(records),
        dry_run=dry_run,
        uploaded=uploaded,
    ).model_dump()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, nargs="?", default=None)
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="요청 간 대기(초), 쿼터 완화용",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출 없이 파일만 읽고 건수 출력",
    )
    args = parser.parse_args()

    try:
        result = upload_vertexai_datastore(
            str(args.jsonl) if args.jsonl else None,
            request_delay_sec=args.request_delay,
            dry_run=args.dry_run,
            confirm=not args.dry_run,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"읽음: {result['record_count']}건 ({result['jsonl_path']})")
    if result["uploaded"]:
        print("업로드 완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
