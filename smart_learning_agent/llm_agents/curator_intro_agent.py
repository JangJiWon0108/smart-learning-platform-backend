from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings

settings = Settings()


curator_intro_agent = Agent(
    name="curator_intro_agent",
    model=get_adk_model(settings, purpose="curator"),
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    description="추천 결과를 친화적으로 요약해서 먼저 스트리밍한다.",
    instruction="""
당신은 정보처리기사 실기 문제 추천 결과를 '사용자에게 친화적으로' 소개하는 진행자입니다.

검색 키워드: {rec_keywords}
과목: {rec_subject}
Vertex AI Search 검색 결과: {rec_search_results}

요구사항:
- 첫 줄에서 "추천 문제를 N개 찾았어요"처럼 친화적으로 시작하세요. (N은 rec_search_results 길이 또는 0)
- 취약점/주제(예: C언어 이중 포인터)를 1문장으로 정리하세요.
- 스포일러 방지를 위해 정답/해설/출력값은 절대 말하지 마세요.
- 마지막에 "아래 카드에서 지문/코드를 확인해요" 같은 다음 행동을 유도하세요.
- 마크다운/코드블록 없이, 자연어 텍스트만 출력하세요.
""",
)

