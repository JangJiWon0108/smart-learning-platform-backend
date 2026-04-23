"""
Gemini API HTTP 옵션 설정.

timeout: 단일 요청의 최대 대기 시간.
  - 60초(60_000ms) 안에 응답이 없으면 TimeoutError를 발생시킵니다.
  - HttpOptions.timeout 단위는 밀리초(ms)입니다.

retry_options: 429 RESOURCE_EXHAUSTED 등 일시적 오류 발생 시 자동 재시도 설정.
  - initial_delay: 첫 번째 재시도 전 대기 시간 (초)
  - attempts: 최초 요청 포함 총 시도 횟수 (attempts=4 → 최대 3회 재시도)
  - 참고: https://google.github.io/adk-docs/agents/models/google-gemini/#error-code-429-resource_exhausted
"""

from google.genai import types

GEMINI_GENERATE_CONTENT_RETRY_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        timeout=60_000,  # 60초 (단위: 밀리초)
        retry_options=types.HttpRetryOptions(
            initial_delay=2,  # 첫 재시도 전 2초 대기
            attempts=4,       # 최초 요청 1회 + 재시도 최대 3회
        ),
    )
)
