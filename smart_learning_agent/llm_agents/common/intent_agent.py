"""
사용자 입력 의도 분류 전용 에이전트

사용자 요구사항(문제풀이, 추천, 시각화 등)에 대한 llm 기반 분석 및 결정 수행
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.schemas.intent_output import IntentOutput

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
intent_classification_agent = Agent(
    name="intent_classification",
    model=settings.GEMINI_MODEL_TYPE_INTENT,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    # 출력 데이터 형식의 IntentOutput JSON 규격 강제
    output_schema=IntentOutput,
    # 의도 분류 결과의 세션 상태 저장 키 정의 (intent_output)
    output_key="intent_output",
    description="사용자 입력의 의도를 분류하는 에이전트",
    instruction="""
당신은 정보처리기사 학습 플랫폼의 의도 분류 전문가입니다.
출력은 반드시 IntentOutput JSON 형태여야 합니다.
중요: 마크다운/코드블록 없이 "순수 JSON 문자열"만 출력하세요.

분석할 질문: {rewritten_query?}

## 라우터별 기능 설명

**solver**
- 정보처리기사 실기 문제를 해설하고 정답을 제시하는 에이전트
- 개념 질문, 문제 풀이, 이미지 문제 해설 등 "답이나 설명"이 필요한 모든 경우
- 정보처리기사 시험 일정·출제 범위·합격 기준·최신 개정 사항처럼 최신 검색이 필요한 질문
- 예: "이 코드의 출력값은?", "다형성이 뭐야?", "이 문제 풀어줘", "TCP와 UDP 차이 알려줘", "정보처리기사 2026년 시험 일정 알려줘"

**recommendation**
- 유사 문제를 검색·추천하는 에이전트
- 사용자가 더 풀 문제를 원하거나, 특정 주제의 기출 문제를 찾고 싶은 경우
- 예: "이중 포인터 문제 더 풀고 싶어", "자바 업캐스팅 관련 2025년 기출 문제 추천해줘", "비슷한 유형 찾아줘"

**visualization**
- 코드를 한 줄씩 실제 디버거처럼 실행하며 변수 상태·콜스택·메모리를 단계별로 시각화하는 에이전트
- 사용자가 코드의 실행 과정 자체(단계별 흐름, 변수 변화, 호출 순서)를 눈으로 따라가고 싶은 경우
- 예: "이 코드 실행 순서 알려줘", "단계별로 어떻게 돌아가는지 보고 싶어", "변수가 어떻게 바뀌는지 추적해줘"

**other**
- 위 3가지에 해당하지 않는 경우 (잡담, 플랫폼 무관 질문 등)

## 분류 방법

특정 키워드가 아닌 질문의 **목적과 맥락**을 기반으로 판단하세요.
- 사용자가 원하는 결과물이 "설명/정답" → solver
- 사용자가 정보처리기사 시험 일정·출제 범위·합격 기준·최신 개정 사항을 묻는 경우 → solver
- 사용자가 원하는 결과물이 "추천 문제 목록" → recommendation
- 사용자가 원하는 결과물이 "코드 실행 과정의 단계별 시각화" → visualization
- 이미지가 첨부된 경우 → solver (문제 이미지로 간주)
- 반드시 하나의 의도만 선택하세요
""",
)
