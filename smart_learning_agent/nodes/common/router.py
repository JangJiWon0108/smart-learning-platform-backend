"""
의도 분류 결과 기반 워크플로우 라우터

Intent 분류 에이전트의 결과를 분석하여 최적의 에이전트 경로로 라우팅 수행
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator
from typing import Any

from google.adk import Event

from smart_learning_agent.schemas.intent_output import IntentOutput


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def intent_router(
    intent_output: IntentOutput | dict[str, Any],
) -> Generator[Event, None, None]:
    """
    분류된 의도 데이터 기반 워크플로우 분기 결정

    Args:
        intent_output: 의도 분류 결과 객체 (IntentOutput 또는 dict)

    Yields:
        라우팅 경로 및 현재 상태 정보를 포함한 이벤트 객체

    state에 저장되는 값:
        - current_route: 다음에 실행할 워크플로우 분기 이름

    경로별 할당 에이전트:
        - "solver"         → 문제 풀이 에이전트
        - "recommendation" → 문제 추천 에이전트
        - "visualization"  → 코드 추적 에이전트
        - "other"          → 폴백 에이전트
    """
    # 1단계: 입력 데이터의 Pydantic 모델 유효성 검사 및 변환
    if isinstance(intent_output, dict):
        intent_output = IntentOutput.model_validate(intent_output)

    # 2단계: 분류 의도의 세션 상태 저장 및 워크플로우 분기(Route) 결정
    yield Event(
        state={"current_route": intent_output.intent},
        route=[intent_output.intent],
    )
