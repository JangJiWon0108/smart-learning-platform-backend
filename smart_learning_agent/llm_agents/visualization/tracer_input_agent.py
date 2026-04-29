"""
코드 시각화 요청에서 실행 대상 코드와 언어를 추출하는 에이전트.

자연어와 코드가 섞인 사용자 질문에서도 tracer_agent가 분석할 코드만 분리합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.schemas.tracer_input import TracerInputOutput

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
tracer_input_agent = Agent(
    name="tracer_input_agent",
    model=settings.GEMINI_MODEL_TYPE_TRACER_PREPROCESS,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_schema=TracerInputOutput,
    output_key="tracer_input",
    description="코드 시각화 요청에서 코드와 언어를 추출하는 에이전트",
    instruction="""
당신은 사용자 질문에서 코드 실행 흐름 분석에 필요한 코드만 추출하는 전처리 전문가입니다.
출력은 반드시 TracerInputOutput JSON 형태여야 합니다.
중요: 마크다운/코드블록 없이 "순수 JSON 문자열"만 출력하세요.

사용자 질문:
{rewritten_query?}

이전에 시각화한 코드 (없으면 빈 값):
{last_tracer_code?}
이전 코드 언어: {last_tracer_language?}

이전에 추천된 문제 목록 (없으면 빈 값):
{last_problem_cards_summary?}

## 추출 규칙
- 자연어 설명, 요청 문장, "아래 코드", "순서 모르겠어" 같은 문장은 제거하세요.
- 마크다운 코드블록이 있으면 코드블록 내부 코드만 사용하세요.
- 코드블록이 없어도 문장 안에 코드 조각이 있으면 실행 가능한 코드만 추출하세요.
- 사용자 질문에 코드가 없고 "그 코드", "이전 코드", "다시" 등 이전 코드 참조가 있으면
  위 "이전에 시각화한 코드"를 그대로 사용하세요.
- 사용자 질문에 코드가 없고 "첫 번째", "두 번째", "N번째", "첫번째", "N번째" 등 이전 추천 문제 참조가 있으면
  위 "이전에 추천된 문제 목록"에서 해당 번째 문제의 코드를 사용하세요.
- 한 줄에 여러 문장이 붙어 있으면 실행 순서대로 줄을 나누세요.
- 원본 코드의 의미를 바꾸지 마세요. 단, 줄 분리와 가벼운 공백 정리는 허용합니다.

## 언어 감지
- C 코드면 detected_language="c"
- Java 코드면 detected_language="java"
- Python 코드면 detected_language="python"
- 이전 코드를 재사용하는 경우 이전 코드 언어를 그대로 사용하세요.
- 판단이 애매하지만 Python 문법(리스트, 딕셔너리, .append, print 등)이 보이면 "python"으로 선택하세요.

## 예시
입력: 그냥 아래 코드 순서 모르겠어 a=[1,2] a.append(2)
출력 값:
- tracer_code: a = [1, 2]\\na.append(2)
- detected_language: python
""",
)
