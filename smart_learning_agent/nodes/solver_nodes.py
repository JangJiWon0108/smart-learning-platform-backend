"""
문제 풀이(solver) 에이전트를 위한 전처리 노드.

이미지 첨부 여부에 따라 solver_agent에 전달할 쿼리를 적절하게 변환합니다.
"""

# ─── 임포트 ──────────────────────────────────────────────────────────────
from google.adk import Event


# ─── 전처리 함수 ──────────────────────────────────────────────────────────
def solver_preprocess_func(original_query: str, has_image: bool = False):
    """
    이미지 첨부 여부에 따라 solver_agent에 전달할 쿼리를 만듭니다.

    Args:
        original_query: 사용자가 입력한 원본 질문
        has_image:      이미지 첨부 여부 (세션 초기 state에서 설정)

    Yields:
        solver_query를 포함하는 Event

    케이스별 처리:
        1. 이미지만 첨부 (텍스트 없음)  → "[이미지에 포함된 문제를 풀어주세요]"
        2. 이미지 + 텍스트              → "[이미지 첨부됨] {텍스트}"
        3. 텍스트만                     → 원본 텍스트 그대로
    """
    # 1단계: 이미지 및 텍스트 존재 여부에 따라 에이전트용 쿼리(solver_query) 조합
    if has_image:
        if not original_query.strip():
            # 이미지만 있고 텍스트가 없는 경우: 이미지 문제 풀이 요청
            solver_query = "[이미지에 포함된 문제를 풀어주세요]"
        else:
            # 이미지와 텍스트가 함께 있는 경우: 이미지 첨부 표시 추가
            solver_query = f"[이미지 첨부됨] {original_query}".strip()
    else:
        # 텍스트만 있는 경우: 그대로 사용
        solver_query = original_query

    # 2단계: 가공된 쿼리를 state에 저장하여 다음 노드(solver_agent)로 전달
    yield Event(state={"solver_query": solver_query})
