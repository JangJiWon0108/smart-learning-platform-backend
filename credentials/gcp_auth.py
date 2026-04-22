from __future__ import annotations

import os
from pathlib import Path

from google.oauth2 import service_account

try:
    import vertexai  # type: ignore
except Exception:
    vertexai = None  # type: ignore[assignment]


def get_credentials():
    auth_json_file_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not auth_json_file_path:
        try:
            from config.properties import Settings
            auth_json_file_path = Settings().GOOGLE_APPLICATION_CREDENTIALS
        except Exception:
            pass

    if not auth_json_file_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS 가 설정되지 않았습니다.")

    key_path = Path(auth_json_file_path)
    if not key_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        key_path = (backend_root / key_path).resolve()
        auth_json_file_path = str(key_path)
    if not key_path.exists():
        raise FileNotFoundError(f"서비스 계정 JSON 파일을 찾을 수 없습니다: {auth_json_file_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = auth_json_file_path

    return service_account.Credentials.from_service_account_file(
        auth_json_file_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def init_google_genai(
    *,
    project: str | None = None,
    location: str | None = None,
) -> None:
    if vertexai is None:
        raise RuntimeError("vertexai 패키지를 import 할 수 없습니다. 'pip install google-cloud-aiplatform' 실행하세요.")

    creds = get_credentials()  # GOOGLE_APPLICATION_CREDENTIALS env var도 함께 설정됨

    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)

    if project and location:
        vertexai.init(project=project, location=location, credentials=creds)
    elif project:
        vertexai.init(project=project, credentials=creds)
