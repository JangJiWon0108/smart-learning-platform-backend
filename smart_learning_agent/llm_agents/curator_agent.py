"""
검색 결과를 분석해서 최종 추천 문제 목록을 구성하는 에이전트.

Vertex AI Search 검색 결과를 입력받아
사용자에게 맞는 문제 3개를 선정하고 메타데이터를 정리합니다.
"""

# ─── 임포트 ──────────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.schemas.curator_output import CuratorOutput

# ─── 설정 및 상수 ────────────────────────────────────────────────────────
# 전역 환경 설정 객체
settings = Settings()

# ─── 에이전트 정의 ────────────────────────────────────────────────────────
curator_agent = Agent(
    name="curator_agent",
    model=settings.GEMINI_MODEL_TYPE_CURATOR,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 출력 형식을 CuratorOutput JSON으로 강제합니다
    output_schema=CuratorOutput,
    # 추천 결과를 "curator_output" 키로 state에 저장합니다
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
