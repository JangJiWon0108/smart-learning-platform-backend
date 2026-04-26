"""
question_refine_agent 완료 후 실행되는 ADK 콜백.

curator_output + refine_output을 읽어 프론트엔드 문제 카드 목록을 빌드하고
state["problem_cards"]에 저장합니다.
"""

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import random
import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
# 문제 카드에 적용할 강조 색상 목록
_CARD_ACCENTS = ["violet", "cyan", "amber", "rose"]


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _accent_for(_problem: dict[str, Any]) -> str:
    """문제 카드에 무작위 강조 색상을 할당합니다."""
    return random.choice(_CARD_ACCENTS)


def _match_label_for(problem: dict[str, Any]) -> str:
    """문제 카드의 배지 라벨(과목명 등)을 결정합니다."""
    subject = str(problem.get("subject") or "").strip()
    return subject if subject else "추천"


def _extract_question_number(problem: dict[str, Any]) -> int | None:
    """문제 텍스트에서 문제 번호를 추출합니다."""
    question_number = problem.get("question_number")
    if isinstance(question_number, int):
        return question_number
    question_text = str(problem.get("question") or "")
    match = re.search(r"(?:\[문제\]\s*)?(\d{1,2})\s*\.", question_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _build_refine_lookup(refine_output: Any) -> dict[str, Any]:
    """정제된 문제 목록(refine_output)을 ID 기반의 룩업 테이블로 변환합니다."""
    if refine_output is None:
        return {}
    if hasattr(refine_output, "model_dump"):
        refine_output = refine_output.model_dump()
    if not isinstance(refine_output, dict):
        return {}
    lookup = {}
    for refined in (refine_output.get("refined_problems") or []):
        if isinstance(refined, dict) and refined.get("id"):
            lookup[refined["id"]] = refined
    return lookup


def _to_problem_cards(
    curator_output: dict[str, Any],
    refine_lookup: dict[str, Any],
) -> list[dict[str, Any]]:
    """큐레이션 결과와 정제된 데이터를 결합하여 프론트엔드용 문제 카드 객체 리스트를 만듭니다."""
    # 1단계: 추천된 문제 중 상위 3개만 추출
    problems = (curator_output.get("recommended_problems") or [])[:3]
    if not isinstance(problems, list):
        return []

    cards = []
    for problem in problems:
        if not isinstance(problem, dict):
            continue

        problem_id = str(problem.get("id") or "")
        original_question = str(problem.get("question") or "").strip()

        # 2단계: 정제된 데이터(refined)가 있으면 오버라이드
        refined = refine_lookup.get(problem_id)
        if refined:
            display_question = refined.get("refined_question") or original_question
            display_code = refined.get("refined_code") or None
            code_language = refined.get("code_language") or None
        else:
            display_question = original_question
            display_code = None
            code_language = None

        year = int(problem.get("year") or 0)
        round_number = int(problem.get("round") or 0)

        # 3단계: 최종 카드 객체 구성
        cards.append(
            {
                "problemId": problem_id,
                "year": year,
                "round": round_number,
                "questionNumber": _extract_question_number(problem) or 0,
                "examTitle": f"[{year}년 {round_number}회] 정보처리기사 실기",
                "stemPreview": display_question,
                "officialAnswer": str(problem.get("answer") or "") or None,
                "matchLabel": _match_label_for(problem),
                "accent": _accent_for(problem),
                "subject": problem.get("subject"),
                "similarityScore": problem.get("similarity_score"),
                "question": display_question,
                "code": display_code,
                "codeLanguage": code_language,
                "answer": problem.get("answer"),
                "explanation": problem.get("explanation"),
            }
        )

    return cards


# ─── 콜백 함수 ─────────────────────────────────────────────────────────────
def build_curation_callback(callback_context: CallbackContext) -> types.Content | None:
    """에이전트 실행 완료 후 최종 UI용 문제 카드를 생성하여 state에 저장합니다."""
    state = callback_context.state
    curator_data = state.get("curator_output")

    # 1단계: 큐레이터 데이터 유효성 검사
    if curator_data is None:
        return None

    if hasattr(curator_data, "model_dump"):
        curator_data = curator_data.model_dump()

    if not isinstance(curator_data, dict):
        return None

    # 2단계: 정제 데이터와 결합하여 카드 생성 및 저장
    refine_lookup = _build_refine_lookup(state.get("refine_output"))
    state["problem_cards"] = _to_problem_cards(curator_data, refine_lookup)

    return None
