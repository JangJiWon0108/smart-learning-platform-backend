"""
의도 분류 결과를 보고 다음 처리 경로를 결정하는 라우터.

intent_classification_agent가 분류한 의도(intent)를 읽어서
어떤 에이전트로 라우팅할지 결정합니다.
"""

# ─── 임포트 ──────────────────────────────────────────────────────────────
from google.adk import Event

from smart_learning_agent.schemas.intent_output import IntentOutput


# ─── 라우터 함수 ──────────────────────────────────────────────────────────
def intent_router(intent_output):
    """
    의도 분류 결과에 따라 처리 경로를 결정합니다.

    Args:
        intent_output: IntentOutput 객체 또는 dict 형태의 분류 결과

    Yields:
        current_route 상태와 라우팅 경로를 담은 Event

    라우팅 경로:
        - "solver"         → 문제 풀이 에이전트
        - "recommendation" → 문제 추천 에이전트
        - "visualization"  → 코드 추적 에이전트
        - "other"          → 폴백 에이전트
    """
    # 1단계: dict 형태로 들어올 수 있으므로 Pydantic 모델로 변환합니다
    if isinstance(intent_output, dict):
        intent_output = IntentOutput.model_validate(intent_output)

    # 2단계: 분류된 의도를 state에 저장하고, 해당 경로로 라우팅합니다
    # route 리스트가 워크플로우 분기를 결정합니다
    yield Event(
        state={"current_route": intent_output.intent},
        route=[intent_output.intent],
    )
