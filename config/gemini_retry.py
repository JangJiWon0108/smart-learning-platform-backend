"""
Gemini API 호출 시 HTTP 오류가 발생했을 때 자동으로 재시도하는 설정.

네트워크가 불안정하거나 서버가 일시적으로 과부하 상태일 때
자동으로 몇 번 더 시도해서 안정적인 응답을 받을 수 있게 합니다.
"""

from google.genai import types

# 재시도 옵션 정의
# - attempts=6       : 최대 6번까지 시도합니다 (첫 시도 1번 + 재시도 5번)
# - initial_delay=2  : 첫 재시도 전 2초 기다립니다
# - max_delay=90     : 최대 90초까지 기다립니다 (지수 백오프)
# - exp_base=2       : 대기 시간을 2배씩 늘립니다 (2초 → 4초 → 8초 → ...)
# - http_status_codes: 이 HTTP 오류 코드가 나왔을 때만 재시도합니다
#   408=타임아웃, 429=요청 한도 초과, 5xx=서버 오류
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
