"""
코드 추적(tracer) 에이전트를 위한 전처리 노드.

LLM이 추출한 코드/언어 결과를 후속 tracer 에이전트 입력 형태로 정리합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator
from typing import Any

from google.adk import Event

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
_SUPPORTED_LANGUAGES = {"c", "java", "python"}


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _normalize_language(language: str) -> str:
    """
    LLM이 반환한 언어 값을 워크플로우에서 지원하는 값으로 보정합니다.

    Args:
        language: LLM이 감지한 언어 이름

    Returns:
        지원 언어 값 ("c", "java", "python" 중 하나)
    """
    normalized = language.strip().lower()

    if normalized in _SUPPORTED_LANGUAGES:
        return normalized

    return "python"


def _build_numbered_code(code: str) -> str:
    """
    tracer_agent가 line 값을 정확히 지정할 수 있도록 코드에 줄 번호를 붙입니다.

    Args:
        code: 실행 흐름 분석 대상 코드

    Returns:
        줄 번호가 붙은 코드 문자열
    """
    numbered_lines = [f"{i + 1:3d}: {line}" for i, line in enumerate(code.split("\n"))]
    return "\n".join(numbered_lines)


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def prepare_tracer_input_func(
    tracer_input: dict[str, Any] | None = None,
) -> Generator[Event, None, None]:
    """
    LLM 전처리 결과를 tracer_agent가 사용하는 state 값으로 변환합니다.

    Args:
        tracer_input: tracer_input_agent가 추출한 코드와 언어 정보

    Yields:
        tracer_code, tracer_code_numbered, detected_language를 포함하는 Event

    state에 저장되는 값:
        - tracer_code: 추출된 코드 (tracer_agent가 이 코드를 분석)
        - tracer_code_numbered: 줄 번호가 붙은 코드 (tracer_agent의 line 필드 생성용)
        - detected_language: 감지된 언어 ("c", "java", "python")
    """
    tracer_input = tracer_input or {}
    tracer_code = str(tracer_input.get("tracer_code", "")).strip()
    detected_language = _normalize_language(str(tracer_input.get("detected_language", "")))

    yield Event(
        state={
            "tracer_code": tracer_code,
            "tracer_code_numbered": _build_numbered_code(tracer_code),
            "detected_language": detected_language,
        }
    )
