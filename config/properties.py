"""
프로젝트 전역 환경 변수 설정 관리 모듈

.env 파일 및 시스템 환경 변수 로드 수행
pydantic-settings 기반 타입 안전성 확보
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 파일 위치 식별: config 폴더 및 backend 루트 경로
BASE_DIR = Path(__file__).resolve().parents[1]

# .env 파일 경로 설정 로직
# ENV_FILE 환경 변수 우선 적용 및 미지정 시 루트 경로 .env 사용
DEFAULT_ENV_FILE = str(BASE_DIR / ".env")
ENV_FILE = os.getenv("ENV_FILE", DEFAULT_ENV_FILE)


class Settings(BaseSettings):
    """
    어플리케이션 전역 설정 관리 클래스

    .env 및 환경 변수 자동 매핑 처리
    PROJECT_ID 등 주요 설정값 로드
    """

    # ─── GCP 및 Vertex AI 기본 구성 ─────────────────────────
    # Vertex AI 사용 여부 정의 (True: Vertex AI, False: Gemini API 직결)
    GOOGLE_GENAI_USE_VERTEXAI: bool = True

    # GCP 프로젝트 ID 식별자
    PROJECT_ID: str = ""

    # GCP 배포 리전 설정
    LOCATION: str = "us-central1"

    # GCP 서비스 계정 인증 키 파일 경로
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    # ─── Vertex AI Search (Discovery Engine) 구성 ────────────────────
    # Discovery Engine 리전 설정 (미지정 시 기본 LOCATION 사용)
    # 글로벌 데이터 스토어 오류 발생 시 global 명시 권장
    VERTEX_AI_SEARCH_LOCATION: str = ""

    # Vertex AI Search 데이터 스토어 식별자
    DATA_STORE_ID: str | None = None

    # Vertex AI Search 엔진 식별자
    ENGINE_ID: str | None = None

    # 구조화 문서 저장 브랜치 정의 (기본값 "0")
    VERTEX_AI_SEARCH_BRANCH: str = "0"

    # 검색 결과 관련도 임계치 설정 (LOWEST, LOW, MEDIUM, HIGH, HIGHEST)
    RELEVANCE_THRESHOLD: str = "LOWEST"

    # 시맨틱 유사도 임계치 설정 (이하 점수 필터링)
    SEMANTIC_RELEVANCE_THRESHOLD: float = 0.2

    # ─── 에이전트별 Gemini 모델 구성 ─────────────────────
    GEMINI_MODEL_TYPE_INTENT: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_QUERY_REWRITE: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_FALLBACK: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_SOLVER: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_FILTER: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_CURATOR_INTRO: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_CURATOR: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_QUESTION_REFINE: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER_PREPROCESS: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER_INTRO: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER: str = "gemini-2.5-flash"

    # ─── 시스템 로깅 설정 ───────────────────────────────────────────────────
    # 상세 디버그 로그 출력 여부 설정
    LOGGING_DETAILS: bool = False

    # Pydantic Settings 메타 데이터 정의
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,          # 로드 대상 .env 파일 경로
        env_file_encoding="utf-8",  # 파일 인코딩 설정
        extra="ignore",             # 미정의 변수 무시 처리
    )
