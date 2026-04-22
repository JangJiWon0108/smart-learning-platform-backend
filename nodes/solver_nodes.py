from google.adk import Event


def solver_preprocess_func(original_query: str, has_image: bool = False):
    if has_image and not original_query.strip():
        solver_query = "[이미지에 포함된 문제를 풀어주세요]"
    else:
        solver_query = f"[이미지 첨부됨] {original_query}".strip() if has_image else original_query

    yield Event(state={"solver_query": solver_query})

