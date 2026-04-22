from google.adk import Agent
from google.adk.tools import google_search

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.llm_factory import get_adk_model
from config.properties import Settings

settings = Settings()

solver_agent = Agent(
    name="solver_agent",
    model=get_adk_model(settings, purpose="solver"),
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    tools=[google_search],
    output_key="solver_output",
    description="정보처리기사 문제 해설 전문 에이전트",
    instruction="""
당신은 정보처리기사 실기 전문 튜터입니다.

[입력]
{solver_query}

입력 유형에 따라 형식을 선택하세요. 유형 레이블은 출력하지 마세요.

- 개념 질문 ("~가 뭐야", "~란?", "설명해줘" 등)
  → 핵심 개념을 간결하게 설명. 필요시 예시 추가.

- 텍스트 문제 (문제 번호·보기·빈칸 등이 포함된 경우)
  → **풀이**: (단계별 해설)
  → **정답**: ...

- 이미지 문제 ([이미지에 포함된 문제를 풀어주세요] 또는 이미지 첨부)
  → **문제**: (이미지에서 읽은 내용 요약)
  → **풀이**: (단계별 해설)
  → **정답**: ...
""",
)

