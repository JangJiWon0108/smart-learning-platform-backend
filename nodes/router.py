from google.adk import Event

from schemas.intent import IntentOutput


def intent_router(intent_output):
    """의도 분류 결과를 기반으로 처리 경로를 결정한다."""
    if isinstance(intent_output, dict):
        intent_output = IntentOutput.model_validate(intent_output)
    yield Event(
        state={"current_route": intent_output.intent},
        route=[intent_output.intent],
    )

