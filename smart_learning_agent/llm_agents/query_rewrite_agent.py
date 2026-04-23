"""
멀티턴 대화에서 사용자 질문을 문맥에 맞게 재작성하는 에이전트.

예를 들어 이전 대화에서 "포인터"를 이야기했는데
사용자가 "그게 뭐야?"라고 물으면, "C언어 포인터가 뭐야?"로 재작성합니다.
이렇게 하면 각 에이전트가 이전 대화 문맥 없이도 질문을 이해할 수 있습니다.
"""

from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings

# 설정 로드
settings = Settings()

query_rewrite_agent = Agent(
    name="query_rewrite",
    model=settings.GEMINI_MODEL_TYPE_QUERY_REWRITE,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 재작성된 질문을 "original_query" 키로 state에 덮어씁니다
    # (이후 에이전트들이 이 재작성된 질문을 사용합니다)
    output_key="original_query",
    description="멀티턴 대화에서 사용자의 질문을 문맥에 맞게 재작성하는 에이전트",
    instruction="""
당신은 멀티턴 대화에서 사용자 질문을 독립적으로 이해 가능한 형태로 재작성하는 전문가입니다.
최근 대화 5개를 참고하여 현재 질문을 재작성하세요.

현재 질문: {original_query}

규칙:
1. 최근 대화가 없거나 현재 질문이 이미 독립적이면 그대로 반환하세요.
2. 현재 질문이 이전 대화의 특정 주제/개념을 암묵적으로 참조하면 맥락을 포함해 재작성하세요.
3. 재작성된 질문만 출력하세요. 설명, 따옴표, 부가 문장 없이 질문 텍스트만 출력합니다.

예시:
이전 대화: "C언어 포인터가 뭐야?" → "포인터는 메모리 주소를 저장하는 변수입니다."
현재 질문: "주소가 뭐야?"
출력: C언어 포인터에서 메모리 주소가 뭐야?
""",
)
