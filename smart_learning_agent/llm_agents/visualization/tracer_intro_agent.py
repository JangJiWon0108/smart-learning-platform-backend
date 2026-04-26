"""
코드 시각화 결과를 안내하는 소개 메시지 생성 에이전트.

tracer_agent가 분석 결과를 생성하는 동안
스트리밍으로 먼저 "~에 대한 실행 흐름입니다" 같은 안내 문장을 보냅니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
tracer_intro_agent = Agent(
    name="tracer_intro_agent",
    model=settings.GEMINI_MODEL_TYPE_TRACER_INTRO,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 소개 텍스트를 "tracer_intro" 키로 state에 저장합니다
    output_key="tracer_intro",
    description="코드 시각화 결과 안내 텍스트 생성 에이전트",
    instruction="""
감지된 언어: {detected_language?}

아래 코드에 대한 실행 흐름 시각화 결과를 안내하는 친절한 소개 문장을 작성하세요.

[코드]
{tracer_code?}

요구사항:
- 2~3문장으로 간결하게
- "~에 대한 실행 흐름입니다. 아래 시각화를 통해 변수 변화와 실행 순서를 확인해보실 수 있습니다." 형식
- 마크다운 없이 순수 텍스트만
""",
)
