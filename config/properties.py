import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/config/properties.py 기준:
# parents[1] = smart-learning-platform-backend (백엔드 루트)
BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = str(BASE_DIR / ".env")
ENV_FILE = os.getenv("ENV_FILE", DEFAULT_ENV_FILE)


class Settings(BaseSettings):
    # Google Vertex AI
    GOOGLE_GENAI_USE_VERTEXAI: bool = True
    PROJECT_ID: str = ""
    LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    # Vertex AI Search (Discovery Engine). 비우면 LOCATION 사용.
    # 콘솔에 "global" 데이터 스토어인데 400 regional 오류면 .env 에 global 로 설정.
    VERTEX_AI_SEARCH_LOCATION: str = ""
    DATA_STORE_ID: str | None = None
    ENGINE_ID: str | None = None
    # 구조화 문서 생성 API: 공식 예시는 branches/0 (숫자 브랜치)
    VERTEX_AI_SEARCH_BRANCH: str = "0"
    RELEVANCE_THRESHOLD: str = "LOWEST"
    SEMANTIC_RELEVANCE_THRESHOLD: float = 0.2

    # Gemini 모델명 (Vertex AI 경유)
    GEMINI_MODEL_TYPE: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_SOLVER: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_CURATOR: str = "gemini-2.5-flash"
    GEMINI_MODEL_TYPE_TRACER: str = "gemini-2.5-flash"

    # FAISS 벡터 스토어
    FAISS_STORE_DIR: str = "data/faiss_store"
    VECTOR_STORE_JSONL: str = "data/vector_store.jsonl"
    EMBEDDING_MODEL: str = "/Users/n-jwjang/jjw/embedding/kure-v1"

    # 로깅
    LOGGING_DETAILS: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )
