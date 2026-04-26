"""
Solver 에이전트용 전처리 노드

이미지 첨부 여부 기반 쿼리 변환 로직 수행
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
from collections.abc import Generator

from google.adk import Event


# ─── 노드 함수 ─────────────────────────────────────────────────────────────
def solver_preprocess_func(
    rewritten_query: str,
    has_image: bool = False,
) -> Generator[Event, None, None]:
    """
    이미지 유무에 따른 Solver 에이전트 전달용 쿼리 생성

    Args:
        rewritten_query: 멀티턴 맥락을 반영해 재작성된 질문 텍스트
        has_image: 이미지 첨부 상태 정보 (세션 초기 상태 데이터)

    Yields:
        solver_query 데이터 포함 이벤트 객체

    state에 저장되는 값:
        - solver_query: 이미지 첨부 여부를 반영한 Solver Agent 입력값

    유형별 처리 로직:
        1. 이미지만 첨부 (텍스트 없음)  → "[이미지에 포함된 문제를 풀어주세요]"
        2. 이미지 + 텍스트              → "[이미지 첨부됨] {텍스트}"
        3. 텍스트만                     → 재작성된 질문 그대로
    """
    # 1단계: 이미지 및 텍스트 조합 기반 에이전트용 쿼리(solver_query) 생성
    if has_image:
        if not rewritten_query.strip():
            # 이미지만 존재할 경우: 이미지 문제 풀이 요청 메시지 정의
            solver_query = "[이미지에 포함된 문제를 풀어주세요]"
        else:
            # 이미지 및 텍스트 동시 존재 시: 이미지 첨부 식별자 추가
            solver_query = f"[이미지 첨부됨] {rewritten_query}".strip()
    else:
        # 텍스트만 존재할 경우: 재작성된 질문 유지
        solver_query = rewritten_query

    # 2단계: 가공된 쿼리의 세션 상태 저장 및 다음 노드(solver_agent) 전달
    yield Event(state={"solver_query": solver_query})
