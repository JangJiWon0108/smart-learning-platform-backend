"""Vertex AI 인증 초기화."""

from __future__ import annotations

import os
from pathlib import Path

from google.oauth2 import service_account  # pyright: ignore[reportMissingImports]
import vertexai  # pyright: ignore[reportMissingImports]

from config.properties import Settings


def get_credentials():
    """서비스 계정 JSON 키 파일을 읽어서 Vertex AI 인증 객체를 반환합니다."""
    key_file_path = Settings().GOOGLE_APPLICATION_CREDENTIALS
    if not key_file_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS 가 설정되지 않았습니다.")

    key_path = Path(key_file_path)
    if not key_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        key_path = (backend_root / key_path).resolve()
        key_file_path = str(key_path)

    if not key_path.exists():
        raise FileNotFoundError(f"서비스 계정 JSON 파일을 찾을 수 없습니다: {key_file_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path

    return service_account.Credentials.from_service_account_file(
        key_file_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def init_google_genai(*, project: str, location: str) -> None:
    """Vertex AI 인증 초기화합니다."""
    credentials = get_credentials()
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    vertexai.init(project=project, location=location, credentials=credentials)
