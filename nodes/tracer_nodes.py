import re

from google.adk import Event

_LANG_PATTERNS: list[tuple[str, list[str]]] = [
    ("c", [r"#include\s*<", r"\bprintf\s*\(", r"\bint\s+main\s*\(", r"\bscanf\s*\("]),
    ("java", [r"\bclass\s+\w+", r"\bSystem\.out\.print", r"\bpublic\s+static\s+void\s+main"]),
    ("python", [r"\bdef\s+\w+\s*\(", r"\bprint\s*\(", r"\bimport\s+\w+", r":\s*$"]),
]


def _detect_language(code: str) -> str:
    scores: dict[str, int] = {"c": 0, "java": 0, "python": 0}
    for lang, patterns in _LANG_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, code, re.MULTILINE):
                scores[lang] += 1
    return max(scores, key=lambda k: scores[k])


def _extract_code_block(query: str) -> str:
    match = re.search(r"```(?:\w+)?\n(.*?)```", query, re.DOTALL)
    if match:
        return match.group(1).strip()
    return query.strip()


def language_detect_func(original_query: str):
    code = _extract_code_block(original_query)
    detected_language = _detect_language(code)

    yield Event(
        state={
            "tracer_code": code,
            "detected_language": detected_language,
        }
    )

