"""Gemini(google-genai) `GenerateContentConfig` 공통 HTTP 재시도 설정."""

from google.genai import types

GEMINI_GENERATE_CONTENT_RETRY_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=6,
            initial_delay=2.0,
            max_delay=90.0,
            exp_base=2.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
    )
)

