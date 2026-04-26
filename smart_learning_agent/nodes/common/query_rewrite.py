"""
사용자의 원본 질문을 state에 저장하는 전처리 노드.

워크플로우의 가장 첫 단계에서 실행됩니다.
이후 query_rewrite_agent가 원본 질문을 바탕으로 rewritten_query를 덮어씁니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator

from google.adk import Event


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def query_preprocess_func(node_input: str) -> Generator[Event, None, None]:
    """
    사용자 입력을 정리해서 state에 저장합니다.

    Args:
        node_input: 사용자가 입력한 원본 질문 텍스트

    Yields:
        original_query와 rewritten_query 기본값을 포함하는 Event.

    state에 저장되는 값:
        - original_query: 앞뒤 공백을 제거한 원본 사용자 입력
        - rewritten_query: query_rewrite_agent 실행 전 사용할 원본 기반 기본값
    """
    # 앞뒤 공백을 제거하고 state에 저장합니다
    cleaned_query = node_input.strip()
    yield Event(
        state={
            "original_query": cleaned_query,
            "rewritten_query": cleaned_query,
        }
    )
