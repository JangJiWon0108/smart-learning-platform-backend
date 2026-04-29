"""
추천 검색용 메타 필터 추출.

MCP tool `extract_vertex_filter` 구현에서 사용합니다.

정규식/규칙 기반으로 rewritten_query에서 연도/회차/유형/문항번호를 추출합니다.
LLM 호출 없음(타임아웃·불안정성 회피).
"""

from __future__ import annotations

# ─── 모듈 임포트 ───────────────────────────────────────────────────────────
import re
from typing import Any

# ─── 상수 정의 ─────────────────────────────────────────────────────────────
_VALID_QUESTION_TYPES = ("concept", "java", "c", "python", "sql")


# ─── 공개 함수 ─────────────────────────────────────────────────────────────
def extract_vertex_filter_output(rewritten_query: str) -> dict[str, Any]:
    """
    rewritten_query에서 연도·회차·유형·문항번호 등 메타 필터 dict 추출.

    Args:
        rewritten_query: 사용자 질문(재작성본)

    Returns:
        VertexFilterOutput 호환 dict(years, rounds, question_types 등)
    """
    text = (rewritten_query or "").strip()
    if not text:
        return {
            "years": [],
            "rounds": [],
            "question_types": [],
            "year_min": None,
            "year_max": None,
            "question_numbers": [],
        }

    years = [int(y) for y in re.findall(r"(20\d{2})\s*년?", text)]
    years = sorted(set([y for y in years if 2015 <= y <= 2035]))

    rounds: set[int] = set()
    for n in re.findall(r"([1-4])\s*회(?:차)?", text):
        rounds.add(int(n))

    qnums: set[int] = set()
    for n in re.findall(r"(?:문항\s*)?(\d{1,2})\s*번", text):
        v = int(n)
        if 1 <= v <= 20:
            qnums.add(v)

    lowered = text.lower()
    qtypes: list[str] = []
    if "자바" in text or "java" in lowered:
        qtypes.append("java")
    if any(k in lowered for k in ["c언어", "포인터", "pointer", "scanf", "printf"]):
        qtypes.append("c")
    if "python" in lowered or "파이썬" in text:
        qtypes.append("python")
    if any(k in lowered for k in ["sql", "db", "데이터베이스", "조인", "트랜잭션", "정규화"]):
        qtypes.append("sql")
    if any(k in text for k in ["개념", "이론", "설명"]):
        qtypes.append("concept")
    qtypes = sorted(set([t for t in qtypes if t in _VALID_QUESTION_TYPES]))

    year_min = None
    year_max = None
    m = re.search(r"(20\d{2})\s*년?\s*[~\-]\s*(20\d{2})\s*년?", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        year_min, year_max = (a, b) if a <= b else (b, a)

    return {
        "years": years,
        "rounds": sorted(rounds),
        "question_types": qtypes,
        "year_min": year_min,
        "year_max": year_max,
        "question_numbers": sorted(qnums),
    }

