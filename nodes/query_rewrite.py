from google.adk import Event


def query_preprocess_func(node_input: str):
    """사용자의 원본 질문을 state에 저장한다."""
    yield Event(state={"original_query": node_input.strip()})
