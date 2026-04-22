from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings
from schemas.curator import CuratorOutput

settings = Settings()

curator_agent = Agent(
    name="curator_agent",
    model=get_adk_model(settings, purpose="curator"),
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_schema=CuratorOutput,
    output_key="curator_output",
    description="정보처리기사 유사 문제 추천 에이전트",
    instruction="""
당신은 정보처리기사 기출 문제 큐레이터입니다.

원문 질문: {original_query}
Vertex AI Search 검색 결과: {rec_search_results}

위 검색 결과를 기반으로 추천 문제 목록을 구성하세요.
- rec_search_results 가 비어 있으면 원문 질문을 참고해 직접 구성하세요.
- 각 문제의 question, answer, explanation, year, round 를 그대로 활용하세요.
- similarity_score 는 score 필드 값을 사용하세요 (없으면 0.0).
- subject 는 question_type 또는 질문 내용으로 추론하세요.
- difficulty 는 문제 내용/유형을 바탕으로 추론하되 확인 불가 시 "medium" 으로 설정하세요.
- weakness_type 은 질문/과목/문제 유형을 바탕으로 추론해서 작성하세요.

출력은 반드시 CuratorOutput JSON 형태여야 합니다.
중요: 마크다운/코드블록/접두·접미 텍스트 없이 "순수 JSON 문자열"만 출력하세요.
""",
)

