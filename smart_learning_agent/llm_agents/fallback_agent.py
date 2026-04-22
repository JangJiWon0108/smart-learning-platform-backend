from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings

settings = Settings()

fallback_agent = Agent(
    name="fallback_agent",
    model=get_adk_model(settings, purpose="intent"),
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_key="fallback_output",
    description="지원 범위 외 질문에 대해 친절하게 안내하는 에이전트",
    instruction="""
사용자 질문: {original_query}

위 질문은 현재 서비스 범위를 벗어납니다.
아래 형식으로 답변하세요.

1. 질문에 대해 한두 문장으로 간단히 답하거나, 답하기 어려운 경우 "제가 도움드리기 어려운 질문이에요." 로 시작하세요.
2. 이어서 다음 세 가지 기능으로 유도하는 친절한 안내를 작성하세요:
   - 문제 해설: 풀기 어려운 문제나 코드를 붙여넣고 해설을 요청해 보세요!
   - 유사 문제 추천: "포인터 관련 문제 추천해줘"처럼 원하는 주제를 알려주세요!
   - 코드 실행 흐름 시각화: 코드를 붙여넣고 실행 흐름을 분석해달라고 해보세요!

요구사항:
- 총 3~5문장, 자연스럽고 따뜻한 말투
- 마크다운 없이 순수 텍스트만
""",
)
