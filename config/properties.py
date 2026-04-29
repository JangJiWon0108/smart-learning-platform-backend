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
    GOOGLE_GENAI_USE_VERTEXAI: bool = True  # Gemini 호출에 Vertex AI backend 사용 여부

    # GCP 프로젝트 ID 식별자
    PROJECT_ID: str = ""  # Vertex AI, Discovery Engine 호출 대상 GCP 프로젝트

    # GCP 배포 리전 설정
    LOCATION: str = "us-central1"  # Gemini/Vertex AI 기본 리전

    # GCP 서비스 계정 인증 키 파일 경로
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None  # 로컬 서비스 계정 키 파일 경로

    # ─── Vertex AI Search (Discovery Engine) 구성 ────────────────────
    # Discovery Engine 리전 설정 (미지정 시 기본 LOCATION 사용)
    # 글로벌 데이터 스토어 오류 발생 시 global 명시 권장
    VERTEX_AI_SEARCH_LOCATION: str = ""  # Discovery Engine 검색/업로드 리전

    # Vertex AI Search 데이터 스토어 식별자
    DATA_STORE_ID: str | None = None  # 기출문제 문서가 저장된 Discovery Engine data store ID

    # Vertex AI Search 엔진 식별자
    ENGINE_ID: str | None = None  # 추천 검색에 사용하는 Discovery Engine serving engine ID

    # 구조화 문서 저장 브랜치 정의 (기본값 "0")
    VERTEX_AI_SEARCH_BRANCH: str = "0"  # 문서 업로드 대상 data store branch

    # 검색 결과 관련도 임계치 설정 (LOWEST, LOW, MEDIUM, HIGH, HIGHEST)
    RELEVANCE_THRESHOLD: str = "LOWEST"  # 키워드 검색 관련도 필터 강도

    # 시맨틱 유사도 임계치 설정 (이하 점수 필터링)
    SEMANTIC_RELEVANCE_THRESHOLD: float = 0.2  # 시맨틱 검색 최소 관련도 점수

    # ─── 에이전트별 Gemini 모델 구성 ─────────────────────
    GEMINI_MODEL_TYPE_INTENT: str = "gemini-2.5-flash"  # 사용자 의도 분류 모델
    GEMINI_MODEL_TYPE_QUERY_REWRITE: str = "gemini-2.5-flash"  # 검색/풀이용 질문 재작성 모델
    GEMINI_MODEL_TYPE_FALLBACK: str = "gemini-2.5-flash"  # 지원 범위 외 요청 응답 모델
    GEMINI_MODEL_TYPE_SOLVER: str = "gemini-2.5-flash"  # 문제 풀이/개념 설명 모델
    GEMINI_MODEL_TYPE_FILTER: str = "gemini-2.5-flash"  # 추천 검색 메타 필터 생성 모델
    GEMINI_MODEL_TYPE_CLASSIFIER: str = "gemini-2.5-flash"  # 기출문제 데이터셋 유형 분류 모델
    GEMINI_MODEL_TYPE_CURATOR_INTRO: str = "gemini-2.5-flash"  # 추천 결과 소개 문구 생성 모델
    GEMINI_MODEL_TYPE_CURATOR: str = "gemini-2.5-flash"  # 추천 문제 큐레이션 모델
    GEMINI_MODEL_TYPE_QUESTION_REFINE: str = "gemini-2.5-flash"  # 추천 문제 카드 정제 모델
    GEMINI_MODEL_TYPE_TRACER_PREPROCESS: str = "gemini-2.5-flash"  # 코드 추적 입력 추출 모델
    GEMINI_MODEL_TYPE_TRACER_INTRO: str = "gemini-2.5-flash"  # 코드 추적 시작 안내 모델
    GEMINI_MODEL_TYPE_TRACER: str = "gemini-2.5-flash"  # 코드 실행 흐름 분석 모델

    # ─── 시스템 로깅 설정 ───────────────────────────────────────────────────
    # 상세 디버그 로그 출력 여부 설정
    LOGGING_DETAILS: bool = False  # 상세 디버그 로그 출력 여부

    # ─── A2A Route 서비스(URL: 각 서비스 `uvicorn ... --port`) ─────────────────
    SOLVER_A2A_URL: str = "http://localhost:8101"
    RECOMMENDATION_A2A_URL: str = "http://localhost:8102"
    VISUALIZATION_A2A_URL: str = "http://localhost:8103"
    FALLBACK_A2A_URL: str = "http://localhost:8104"

    # ─── MCP 서버 구성 (streamable-http 전용) ───────────────────────────────
    # 아래 URL과 맞추려면 MCP를 127.0.0.1:8200 에 띄웁니다.
    # uv run python -m mcp_server.vertexai_search.server --transport streamable-http --host 127.0.0.1 --port 8200
    VERTEXAI_SEARCH_MCP_URL: str = "http://127.0.0.1:8200/mcp"

    # Pydantic Settings 메타 데이터 정의
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,          # 로드 대상 .env 파일 경로
        env_file_encoding="utf-8",  # 파일 인코딩 설정
        extra="ignore",             # 미정의 변수 무시 처리
    )
