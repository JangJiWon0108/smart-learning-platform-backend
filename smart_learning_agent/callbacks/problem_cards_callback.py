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
# 카드 강조 색상 후보
_CARD_ACCENTS = ["violet", "cyan", "amber", "rose"]
_MAX_CURATION_CARDS = 3


# ─── 헬퍼 함수 ─────────────────────────────────────────────────────────────
def _accent_for(_problem: dict[str, Any]) -> str:
    """카드별 강조 색상 무작위 선택."""
    return random.choice(_CARD_ACCENTS)


def _match_label_for(problem: dict[str, Any]) -> str:
    """배지 라벨(과목명) 결정."""
    subject = str(problem.get("subject") or "").strip()
    return subject if subject else "추천"


def _extract_question_number(problem: dict[str, Any]) -> int | None:
    """지문 또는 메타에서 문항 번호 추출."""
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
    """refine_output을 문제 id → 정제 dict 룩업으로 변환."""
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
    """curator_output + refine 룩업 → 프론트 문제 카드 리스트."""
    # 1단계: 추천 상위 3건
    problems = (curator_output.get("recommended_problems") or [])[:_MAX_CURATION_CARDS]
    if not isinstance(problems, list):
        return []

    cards = []
    for problem in problems:
        if not isinstance(problem, dict):
            continue

        problem_id = str(problem.get("id") or "")
        original_question = str(problem.get("question") or "").strip()

        # 2단계: refine 있으면 지문·코드 덮어쓰기
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

        # 3단계: 카드 dict 조립
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


def _build_problem_cards_summary(cards: list[dict[str, Any]]) -> str:
    """멀티턴용 문제 카드 텍스트 요약."""
    if not cards:
        return ""
    lines = [f"이전에 추천된 문제 목록 (총 {len(cards)}개):"]
    for i, card in enumerate(cards, 1):
        year = card.get("year", "")
        round_num = card.get("round", "")
        q_num = card.get("questionNumber", "")
        code_lang = card.get("codeLanguage") or ""
        question = str(card.get("question") or "").strip()
        code = str(card.get("code") or "").strip()

        header = f"[{i}번째] {year}년 {round_num}회 문항 {q_num}"
        if code_lang:
            header += f" ({code_lang})"
        lines.append(header)
        if question:
            lines.append(f"지문: {question}")
        if code:
            lines.append(f"코드:\n{code}")
    return "\n".join(lines)


# ─── 콜백 함수 ─────────────────────────────────────────────────────────────
def build_curation_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    question_refine_agent 직후: problem_cards 및 요약 state 반영.

    Args:
        callback_context: ADK CallbackContext

    Returns:
        추가 응답 없음. 항상 None.

    state에 저장되는 값:
        - problem_cards: 프론트 표시용 카드 dict 목록
        - last_problem_cards_summary: 다음 턴 참조용 요약(세션 정리 키에서 제외되는 경우 유지)
    """
    state = callback_context.state
    curator_data = state.get("curator_output")

    # 1단계: curator_output 유효성
    if curator_data is None:
        return None

    if hasattr(curator_data, "model_dump"):
        curator_data = curator_data.model_dump()

    if not isinstance(curator_data, dict):
        return None

    # 2단계: refine 결합 후 카드 생성·저장
    refine_lookup = _build_refine_lookup(state.get("refine_output"))
    cards = _to_problem_cards(curator_data, refine_lookup)
    state["problem_cards"] = cards

    # 3단계: 멀티턴용 요약(last_problem_cards_summary는 route state 초기화 대상 아님)
    state["last_problem_cards_summary"] = _build_problem_cards_summary(cards)

    return None
