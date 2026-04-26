"""
코드를 한 줄씩 실행하며 실행 흐름을 단계별로 추적하는 에이전트.

실제 디버거처럼 각 줄마다 변수 상태, 콜스택, 메모리를 기록합니다.
C/Java/Python을 지원합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk import Agent

from config.gemini_retry import GEMINI_GENERATE_CONTENT_RETRY_CONFIG
from config.properties import Settings
from smart_learning_agent.callbacks import normalize_tracer_callback
from smart_learning_agent.schemas.tracer_output import TracerOutput

# ─── 설정 로드 ─────────────────────────────────────────────────────────────
settings = Settings()

# ─── 에이전트 정의 ─────────────────────────────────────────────────────────
tracer_agent = Agent(
    name="tracer_agent",
    model=settings.GEMINI_MODEL_TYPE_TRACER,
    generate_content_config=GEMINI_GENERATE_CONTENT_RETRY_CONFIG,
    output_schema=TracerOutput,
    output_key="tracer_output",
    after_agent_callback=normalize_tracer_callback,
    description="코드 실행 흐름 단계별 시각화 에이전트",
    instruction="""
당신은 코드 실행 흐름 시각화 전문가입니다.
감지된 언어: {detected_language?}

[분석할 코드] (왼쪽 숫자 = 줄 번호, step의 line 필드에 이 번호를 그대로 사용)
{tracer_code_numbered?}

위 코드를 실제 디버거처럼 한 줄씩 실행하며 TracerOutput을 채우세요.

## steps 작성 규칙
- 선언문·대입·함수 호출·반환·출력 등 실행 가능한 줄마다 하나의 step 생성
- `line`: 현재 **실행되는 문장(statement)** 의 1-indexed 줄 번호. 메서드/클래스 선언줄이 아닌, 실제로 동작하는 코드 줄을 가리켜야 함. 예: `new Child()`가 실행 중이면 `Parent p = new Child();` 줄 번호, `p.hello()`가 실행 중이면 해당 줄 번호
- `variables`: 해당 스코프의 현재 모든 변수 이름→값 스냅샷
- `changed_vars`: 이 step에서 새로 생기거나 값이 바뀐 변수 이름 목록
- `call_stack`: 외부→내부 순서 함수명 목록 (예: ["main", "add"])
- `note`: 이 줄에서 일어나는 일을 한국어로 한 문장 설명

## 언어별 추가 규칙
- **C**: 포인터 변수마다 memory 항목 추가 (address, value, type, points_to)
- **Java / Python**: new 또는 객체 생성 시 heap 항목 추가 (id, class_name, fields)

## 기타
- 조건문·반복문은 실제 실행 경로만 추적 (실행되지 않는 분기 제외)
- 재귀 호출은 최대 깊이 10까지만 추적
- `title`: 코드가 다루는 핵심 개념을 10자 이내 키워드로 (예: 상속과 생성자, 재귀 함수, 포인터 연산)
- `final_output`: 프로그램이 콘솔에 출력하는 최종 결과 전체
- `summary`: 실행 흐름 전체를 2~3문장으로 한국어 요약
""",
)
