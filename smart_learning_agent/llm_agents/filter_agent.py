"""
Vertex AI Search용 검색 필터를 생성하는 에이전트.

사용자의 문제 추천 요청을 분석해서
연도, 회차, 문제 유형 등의 검색 조건을 만들어냅니다.
"""

from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.schemas.curator_output import VertexFilterOutput

# 설정 로드
settings = Settings()

filter_agent = Agent(
    name="filter_agent",
    model=settings.GEMINI_MODEL_TYPE_FILTER,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 출력 형식을 VertexFilterOutput JSON으로 강제합니다
    output_schema=VertexFilterOutput,
    # 필터 결과를 "vertex_filter_output" 키로 state에 저장합니다
    output_key="vertex_filter_output",
    description="Vertex AI Search 메타 필터 생성 에이전트",
    instruction="""
당신은 Vertex AI Search 검색 필터를 생성하는 에이전트입니다.

원문 질문: {original_query}

위 질문을 분석하여 아래 두 가지를 생성하세요.

1. query_text
   시맨틱 유사도 검색에 사용할 텍스트입니다.
   키워드, 개념 설명, 관련 용어를 모두 포함해 풍부하게 작성하세요.

2. 메타 필터 (불필요하면 빈 리스트/null)
   - question_types: ["concept","java","c","python","sql"] 중 해당 유형만
     (C언어 → ["c"], Java → ["java"], Python → ["python"], SQL/DB → ["sql"], 개념 → ["concept"])
   - years: 특정 연도 리스트 (예: [2023]). 불필요하면 []
   - rounds: 특정 회차 리스트 (예: [1, 2]). 불필요하면 []
   - year_min / year_max: 연도 범위 (불필요하면 null)
   - question_numbers: 특정 문제 번호 (불필요하면 [])

데이터 범위 (중요):
- 유효 연도: 2020~2025 (이 범위를 벗어나는 필터 금지)
- 회차: 2020년은 1~4회차, 2021~2025년은 1~3회차
- 문제 번호: 각 시험마다 1~20번

연도 규칙:
- 특정 연도 명시 (예: "2023년") → years=[2023], year_min/year_max=null
- "N년부터" / "N년 이후" / "N년 이상" → year_min=N, years=[]
- "N년까지" / "N년 이전" / "N년 이하" → year_max=N, years=[]
- "N년~M년" / "N년부터 M년까지" → year_min=N, year_max=M, years=[]
- "최신" → year_min=2024, year_max=2025, years=[]
- 연도 언급 없으면 → years=[], year_min=null, year_max=null

회차 규칙:
- 존재하지 않는 회차 필터 금지 (예: 2021년 4회차 → 무시)
- "마지막 회차" / "최종 회차" → 2020년이면 rounds=[4], 나머지면 rounds=[3]

문제 번호 규칙:
- 유효 범위: 1~20번
- "앞 문제" / "초반" → question_numbers=[1,2,3,4,5]
- "마지막 문제" / "마지막" → question_numbers=[20]

출력은 반드시 순수 JSON 문자열만 출력하세요. 마크다운/코드블록 없이.
""",
)
