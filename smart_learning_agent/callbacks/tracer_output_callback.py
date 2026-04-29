"""
tracer_agent 완료 후 실행되는 ADK 콜백.

LLM이 코드를 변형하는 경우가 있어서,
TracerOutput의 original_code와 각 step.code를 사용자 원본 코드로 덮어씁니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


# ─── 콜백 함수 ─────────────────────────────────────────────────────────────
def normalize_tracer_callback(callback_context: CallbackContext) -> types.Content | None:
    """tracer 출력의 코드 문자열을 사용자 원본 코드 기준으로 정규화합니다."""
    state = callback_context.state
    tracer_output = state.get("tracer_output")
    tracer_code = state.get("tracer_code")

    if not tracer_output or not isinstance(tracer_code, str):
        return None

    if hasattr(tracer_output, "model_dump"):
        tracer_output = tracer_output.model_dump()

    if not isinstance(tracer_output, dict):
        return None

    code_lines = tracer_code.splitlines()
    tracer_output["original_code"] = tracer_code

    steps = tracer_output.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            line_number = step.get("line")
            if isinstance(line_number, int) and 0 < line_number <= len(code_lines):
                step["code"] = code_lines[line_number - 1].rstrip("\n")

    state["tracer_output"] = tracer_output

    # 다음 턴 multi-turn 참조용 persistent summary 저장
    title = tracer_output.get("title", "")
    summary = tracer_output.get("summary", "")
    if title or summary:
        state["last_tracer_summary"] = f"{title}: {summary}".strip(": ")

    return None
