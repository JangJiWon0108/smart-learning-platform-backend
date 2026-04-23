"""
정보처리기사 실기 문제 풀이 전용 에이전트

텍스트, 코드, 이미지 등 다양한 유형의 문제 해설 및 정답 제시
Google Search 도구를 활용한 최신 정보 검색 기능 포함
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent
from google.adk.tools import google_search

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings

# ─── 환경 설정 및 전역 상수 ───────────────────────────────────────────────────
# 전역 환경 설정 관리 객체
settings = Settings()

# ─── Solver 에이전트 구성 ───────────────────────────────────────────────────
solver_agent = Agent(
    name="solver_agent",
    model=settings.GEMINI_MODEL_TYPE_SOLVER,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 문제 풀이 결과의 세션 상태 저장 키 정의 (solver_output)
    output_key="solver_output",
    # 필요 시 Google Search 도구를 통한 웹 검색 수행
    tools=[google_search],
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

## google_search 사용 조건
다음 중 하나에 해당하면 반드시 google_search 도구를 사용하세요.
- 정보처리기사 시험 일정·출제 범위·합격 기준·최신 개정 사항이 필요한 경우
- 특정 기술(언어·프레임워크·프로토콜 등)의 최신 버전·표준·명세가 중요한 경우

위 조건에 해당하지 않는 개념 설명·문제 풀이·이미지 해설은 내부 지식만으로 답하세요.
""",
)
