"""
`build_vertexai_datastore` 출력(NDJSON)을 Vertex AI Search에 올린다.

Discovery Engine 문서 생성 요청:
  POST https://discoveryengine.googleapis.com/v1beta/{parent}/documents?documentId=DOCUMENT_ID
  Content-Type: application/json
  Body: {"structData": { ... }, "content": {"mimeType": "text/plain", "rawBytes": "<utf-8 base64>"}}
  (`content` 키가 있으면 본문 포함; 없으면 structData 만 — 하위 호환)

`parent` = projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/
           dataStores/{DATA_STORE_ID}/branches/{BRANCH}
기본 branch 는 Settings.VERTEX_AI_SEARCH_BRANCH (미설정 시 `0`).

실행 (backend 에서, .env 에 PROJECT_ID, LOCATION, DATA_STORE_ID):
  uv run python -m vertexai_search.upload_vertexai_datastore
  uv run python -m vertexai_search.upload_vertexai_datastore --dry-run
"""

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

if TYPE_CHECKING:
    from google.auth.transport.requests import AuthorizedSession


# ─── 헬퍼 함수 (URL 및 파싱) ───

def _branch_parent(cfg: Settings) -> str:
    if not cfg.PROJECT_ID or not cfg.DATA_STORE_ID:
        raise SystemExit(".env 에 PROJECT_ID, DATA_STORE_ID 가 필요합니다.")
    branch = (cfg.VERTEX_AI_SEARCH_BRANCH or "0").strip() or "0"
    ds = cfg.DATA_STORE_ID.strip()
    loc = (cfg.VERTEX_AI_SEARCH_LOCATION.strip() or cfg.LOCATION).strip()
    return (
        f"projects/{cfg.PROJECT_ID}/locations/{loc}"
        f"/collections/default_collection/dataStores/{ds}/branches/{branch}"
    )


def _document_create_url(parent: str, document_id: str) -> str:
    q = urllib.parse.urlencode({"documentId": document_id})
    return f"https://discoveryengine.googleapis.com/v1beta/{parent}/documents?{q}"


def _document_upsert_url(parent: str, document_id: str) -> str:
    q = urllib.parse.urlencode({"allowMissing": "true"})
    return f"https://discoveryengine.googleapis.com/v1beta/{parent}/documents/{document_id}?{q}"


def _parse_ndjson_line(
    rec: dict[str, Any],
) -> tuple[str, dict[str, Any], str | None]:
    if "structData" not in rec or not isinstance(rec["structData"], dict):
        raise ValueError("각 줄에 structData 객체가 있어야 합니다.")
    if rec.get("documentId"):
        doc_id = str(rec["documentId"])
    elif rec.get("id"):
        doc_id = str(rec["id"])
    else:
        raise ValueError("documentId 또는 id 가 필요합니다.")
    content_plain: str | None = None
    c = rec.get("content")
    if isinstance(c, str) and c.strip():
        content_plain = c
    return doc_id, dict(rec["structData"]), content_plain


def _document_body(struct_data: dict[str, Any], content_plain: str | None) -> dict[str, Any]:
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
    rows: list[tuple[str, dict[str, Any], str | None]] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(_parse_ndjson_line(json.loads(line)))
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"{path}:{lineno} {e}") from e
    return rows


# ─── 데이터 업로드 로직 ───

def upload_all(
    session: "AuthorizedSession",
    cfg: Settings,
    records: list[tuple[str, dict[str, Any], str | None]],
    *,
    request_delay_sec: float,
) -> None:
    parent = _branch_parent(cfg)
    
    # 1단계: 세션 헤더에 인증된 사용자 프로젝트 추가
    session.headers["X-Goog-User-Project"] = cfg.PROJECT_ID
    for i, (doc_id, struct_data, content_plain) in enumerate(records, 1):
        # 2단계: 개별 레코드에 대해 API 페이로드 구성
        body = _document_body(struct_data, content_plain)
        url = _document_create_url(parent, doc_id)
        # 3단계: HTTP POST로 문서 생성 요청
        r = session.post(url, json=body, timeout=120)
        # 4단계: (UPSERT) 이미 존재하는 문서(409 Conflict)일 경우 PATCH로 업데이트
        if r.status_code == 409:
            url = _document_upsert_url(parent, doc_id)
            r = session.patch(url, json=body, timeout=120)
        if not r.ok:
            raise RuntimeError(
                f"UPSERT 실패 documentId={doc_id!r} HTTP {r.status_code}: {r.text}",
            )
            
        # 5단계: API 쿼터 우회를 위한 딜레이 적용 및 로깅
        if request_delay_sec > 0:
            time.sleep(request_delay_sec)
        if i % 50 == 0 or i == len(records):
            print(f"  업로드 {i}/{len(records)}")


# ─── 스크립트 실행부 ───

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "jsonl",
        type=Path,
        nargs="?",
        default=None,
        help="전처리 NDJSON (기본: data/vector_store_vertexai.jsonl)",
    )
    p.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="요청 간 대기(초), 쿼터 완화용",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출 없이 파일만 읽고 건수 출력",
    )
    args = p.parse_args()
    cfg = Settings()
    path = args.jsonl or (Path(BASE_DIR) / "data" / "vector_store_vertexai.jsonl")
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1
    records = iter_records_from_ndjson(path)
    print(f"읽음: {len(records)}건 ({path})")
    if args.dry_run:
        return 0
    session = vertex_discovery_authorized_session()
    upload_all(
        session,
        cfg,
        records,
        request_delay_sec=max(0.0, args.request_delay),
    )
    print("업로드 완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
