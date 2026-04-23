"""
사용자의 원본 질문을 state에 저장하는 전처리 노드.

워크플로우의 가장 첫 단계에서 실행됩니다.
이후 에이전트들이 {original_query}로 원본 질문을 참조합니다.
"""

from google.adk import Event


def query_preprocess_func(node_input: str):
    """
    사용자 입력을 정리해서 state에 저장합니다.

    Args:
        node_input: 사용자가 입력한 원본 질문 텍스트

    Yields:
        original_query를 포함하는 Event
    """
    # 앞뒤 공백을 제거하고 state에 저장합니다
    cleaned_query = node_input.strip()
    yield Event(state={"original_query": cleaned_query})
