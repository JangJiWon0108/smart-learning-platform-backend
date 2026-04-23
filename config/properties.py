"""
프로젝트 전체에서 사용하는 환경 변수 설정 파일.

.env 파일 또는 시스템 환경 변수에서 값을 읽어옵니다.
pydantic-settings 라이브러리를 사용해 타입 안전하게 관리합니다.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 이 파일(properties.py)의 위치: backend/config/properties.py
# parents[0] = config 폴더
# parents[1] = backend 루트 폴더
BASE_DIR = Path(__file__).resolve().parents[1]

# .env 파일 경로 설정
# 환경 변수 ENV_FILE이 지정되어 있으면 그 경로를 사용하고,
# 없으면 backend 루트의 .env 파일을 사용합니다.
DEFAULT_ENV_FILE = str(BASE_DIR / ".env")
ENV_FILE = os.getenv("ENV_FILE", DEFAULT_ENV_FILE)


class Settings(BaseSettings):
    """
    애플리케이션 전체 설정 클래스.

    .env 파일이나 환경 변수에서 자동으로 값을 읽어옵니다.
    예를 들어 PROJECT_ID는 환경 변수 PROJECT_ID 또는 .env의 PROJECT_ID= 로 설정합니다.
    """

    # ─── Google Cloud / Vertex AI 기본 설정 ─────────────────────────
    # Vertex AI를 사용할지 여부 (True = Vertex AI 사용, False = Gemini API 직접 사용)
    GOOGLE_GENAI_USE_VERTEXAI: bool = True

    # GCP 프로젝트 ID (예: "my-gcp-project-123")
    PROJECT_ID: str = ""

    # GCP 리전 (기본값: 미국 중부)
    LOCATION: str = "us-central1"

    # 서비스 계정 JSON 키 파일 경로 (예: "credentials/service_account.json")
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    # ─── Vertex AI Search (Discovery Engine) 설정 ────────────────────
    # Discovery Engine 리전. 비워두면 위의 LOCATION을 사용합니다.
    # 참고: 콘솔에서 "global" 데이터 스토어인데 400 에러가 나면 "global"로 설정하세요.
    VERTEX_AI_SEARCH_LOCATION: str = ""

    # Vertex AI Search 데이터 스토어 ID
    DATA_STORE_ID: str | None = None

    # Vertex AI Search 엔진 ID
    ENGINE_ID: str | None = None

    # 구조화 문서 저장 브랜치. Google 공식 예시에서는 "0" (숫자 브랜치)을 사용합니다.
    VERTEX_AI_SEARCH_BRANCH: str = "0"

    # 검색 결과 관련도 임계값 (LOWEST, LOW, MEDIUM, HIGH, HIGHEST)
    RELEVANCE_THRESHOLD: str = "LOWEST"

    # 시맨틱 유사도 점수 임계값. 이 값보다 낮은 결과는 필터링됩니다.
    SEMANTIC_RELEVANCE_THRESHOLD: float = 0.2

    # ─── Gemini 모델 설정 (에이전트별 개별 설정) ─────────────────────
    GEMINI_MODEL_TYPE_INTENT: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_QUERY_REWRITE: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_FALLBACK: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_SOLVER: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_FILTER: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_CURATOR_INTRO: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_CURATOR: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_QUESTION_REFINE: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER_INTRO: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER: str = "gemini-2.5-flash"

    # ─── 로깅 설정 ───────────────────────────────────────────────────
    # True로 설정하면 더 자세한 디버그 로그를 출력합니다.
    LOGGING_DETAILS: bool = False

    # pydantic-settings 메타 설정
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,          # 읽을 .env 파일 경로
        env_file_encoding="utf-8",  # .env 파일 인코딩
        extra="ignore",             # .env에 정의되지 않은 변수는 무시
    )
