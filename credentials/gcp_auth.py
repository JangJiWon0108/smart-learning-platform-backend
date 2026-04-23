"""
Google Cloud Platform(GCP) 인증 관련 함수 모음.

서비스 계정 JSON 키 파일을 읽어서 인증 정보를 만들고,
Vertex AI와 Gemini API를 초기화합니다.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.oauth2 import service_account

# vertexai 패키지가 없는 환경(테스트 등)에서도 import 오류 없이 동작하도록 처리
try:
    import vertexai  # type: ignore
except Exception:
    vertexai = None  # type: ignore[assignment]


def get_credentials():
    """
    서비스 계정 JSON 키 파일을 읽어서 GCP 인증 객체를 반환합니다.

    키 파일 경로는 다음 순서로 찾습니다:
    1. 환경 변수 GOOGLE_APPLICATION_CREDENTIALS
    2. .env 파일의 GOOGLE_APPLICATION_CREDENTIALS 설정

    Returns:
        google.oauth2.service_account.Credentials 객체

    Raises:
        RuntimeError: 키 파일 경로가 설정되지 않은 경우
        FileNotFoundError: 키 파일이 실제로 존재하지 않는 경우
    """
    # 1단계: 환경 변수에서 키 파일 경로 가져오기
    key_file_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # 환경 변수에 없으면 Settings에서 읽어봅니다
    if not key_file_path:
        try:
            from config.properties import Settings
            key_file_path = Settings().GOOGLE_APPLICATION_CREDENTIALS
        except Exception:
            pass

    # 그래도 없으면 오류
    if not key_file_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS 가 설정되지 않았습니다.")

    # 2단계: 경로가 상대 경로면 backend 루트 기준으로 절대 경로로 변환
    key_path = Path(key_file_path)
    if not key_path.is_absolute():
        # 이 파일 위치: backend/credentials/gcp_auth.py
        # parents[1] = backend 루트
        backend_root = Path(__file__).resolve().parents[1]
        key_path = (backend_root / key_path).resolve()
        key_file_path = str(key_path)

    # 3단계: 파일이 실제로 존재하는지 확인
    if not key_path.exists():
        raise FileNotFoundError(f"서비스 계정 JSON 파일을 찾을 수 없습니다: {key_file_path}")

    # 환경 변수에도 절대 경로로 업데이트해둡니다 (다른 라이브러리가 참조할 수 있음)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path

    # 서비스 계정 인증 객체 생성 (cloud-platform 권한)
    credentials = service_account.Credentials.from_service_account_file(
        key_file_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return credentials


def init_google_genai(
    *,
    project: str | None = None,
    location: str | None = None,
) -> None:
    """
    Vertex AI와 Google GenAI SDK를 초기화합니다.

    앱 시작 시 한 번만 호출하면 됩니다.
    이 함수를 호출하면 이후 Gemini API 호출이 Vertex AI를 통해 이루어집니다.

    Args:
        project:  GCP 프로젝트 ID
        location: GCP 리전 (예: "us-central1")

    Raises:
        RuntimeError: vertexai 패키지가 설치되지 않은 경우
    """
    if vertexai is None:
        raise RuntimeError(
            "vertexai 패키지를 import 할 수 없습니다. "
            "'pip install google-cloud-aiplatform' 를 실행하세요."
        )

    # 서비스 계정 인증 (이 과정에서 GOOGLE_APPLICATION_CREDENTIALS 환경 변수도 설정됨)
    credentials = get_credentials()

    # Vertex AI 사용 모드 활성화
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    # 다른 AI 서비스의 API 키가 남아있으면 충돌할 수 있으므로 제거합니다
    for api_key_name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(api_key_name, None)

    # Vertex AI 초기화 (프로젝트와 리전 설정)
    if project and location:
        vertexai.init(project=project, location=location, credentials=credentials)
    elif project:
        vertexai.init(project=project, credentials=credentials)
