"""
Vertex AI Search용 검색 필터를 생성하는 에이전트.

사용자의 문제 추천 요청(rewritten_query)에서
연도, 회차, 문제 유형 등의 메타 필터를 LLM이 직접 추출합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.schemas.curator_output import VertexFilterOutput

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
filter_agent = Agent(
    name="filter_agent",
    model=settings.GEMINI_MODEL_TYPE_FILTER,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 출력 형식: VertexFilterOutput JSON 스키마 강제
    output_schema=VertexFilterOutput,
    output_key="vertex_filter_output",
    description="Vertex AI Search 메타 필터 생성 에이전트",
    instruction="""
당신은 Vertex AI Search 메타 필터를 생성하는 에이전트입니다.

재작성된 질문: {rewritten_query?}

위 질문을 분석하여 메타 필터만 생성.
시맨틱 검색어는 시스템이 rewritten_query를 그대로 사용하므로 query_text 필드 생성 금지.

## 메타 필터 (불필요 시 빈 리스트/null)
- question_types: ["concept","java","c","python","sql"] 중 해당 유형만
  (C언어 → ["c"], Java → ["java"], Python → ["python"], SQL/DB → ["sql"], 개념 → ["concept"])
- years: 특정 연도 리스트 (예: [2023]). 불필요 시 []
- rounds: 특정 회차 리스트 (예: [1,2]). 불필요 시 []
- year_min: 최소 연도 (예: 2020). 불필요 시 null
- year_max: 최대 연도 (예: 2024). 불필요 시 null
- question_numbers: 특정 문항 번호 리스트 (예: [3,7]). 불필요 시 []

출력 형식:
- VertexFilterOutput JSON만. 마크다운·코드블록 없이 순수 JSON 문자열만.
""".strip(),
)
