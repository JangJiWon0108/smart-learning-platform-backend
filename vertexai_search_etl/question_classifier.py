"""Vertex AI(Gemini)로 기출문제 유형을 분류한다."""

from __future__ import annotations

import json
import re

from google import genai
from google.genai import types

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from credentials.gcp_auth import init_google_genai

_SYSTEM = """당신은 한국 정보처리기사 실기 기출문제 분류기입니다.
사용자가 주는 것은 시험 **문제 본문**뿐입니다.

규칙:
1) question_category
   - concept: 개념 설명, 용어 정의, 서술, 암기형 — 소스 코드가 핵심이 아닌 문항.
   - code: C/Java/Python 소스가 제시되거나 SQL이 핵심인 문항.

2) code_language (question_category가 code일 때만 의미 있음)
   - sql | c | java | python 중 하나.
   - concept이면 반드시 "none".

반드시 JSON 한 개만 출력. 마크다운 금지.
형식: {"question_category":"concept|code","code_language":"none|sql|c|java|python"}"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = Settings()
        init_google_genai(project=settings.PROJECT_ID, location=settings.LOCATION)
        _client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION,
        )
    return _client


def classify_question(question: str) -> dict[str, str]:
    """문제 문자열을 concept/code 및 언어 라벨로 분류합니다."""
    settings = Settings()
    resp = _get_client().models.generate_content(
        model=settings.GEMINI_MODEL_TYPE_CLASSIFIER,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            response_mime_type="application/json",
            http_options=GEMINI_GENERATE_CONTENT_RETRY_CONFIG.http_options,
        ),
    )
    text = (resp.text or "").strip()
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    data = json.loads(text) if text else {}
    category = str(data.get("question_category", "")).strip().lower()
    language = str(data.get("code_language", "")).strip().lower()

    if category not in ("concept", "code"):
        category = "concept"
    if category == "concept" or language not in ("sql", "c", "java", "python"):
        language = "none"

    return {
        "question_category": category,
        "code_language": language,
        "question_type": language if category == "code" else "concept",
    }
