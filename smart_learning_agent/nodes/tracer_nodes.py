"""
코드 추적(tracer) 에이전트를 위한 전처리 노드.

사용자 입력에서 코드 블록을 추출하고 프로그래밍 언어를 감지합니다.
"""

import re

from google.adk import Event

# 언어별 특징적인 코드 패턴 목록
# 각 패턴이 코드에 등장하면 해당 언어 점수가 1점씩 올라갑니다
_LANG_PATTERNS: list[tuple[str, list[str]]] = [
    ("c", [
        r"#include\s*<",        # #include <stdio.h> 같은 헤더 포함
        r"\bprintf\s*\(",       # printf() 함수 호출
        r"\bint\s+main\s*\(",   # int main() 진입점
        r"\bscanf\s*\(",        # scanf() 함수 호출
    ]),
    ("java", [
        r"\bclass\s+\w+",               # class 선언
        r"\bSystem\.out\.print",        # System.out.print() 출력
        r"\bpublic\s+static\s+void\s+main",  # public static void main 진입점
    ]),
    ("python", [
        r"\bdef\s+\w+\s*\(",   # def 함수 정의
        r"\bprint\s*\(",        # print() 함수 호출
        r"\bimport\s+\w+",      # import 구문
        r":\s*$",               # 콜론으로 끝나는 줄 (if, for, def 등)
    ]),
]


def _detect_language(code: str) -> str:
    """
    코드 문자열을 분석해서 프로그래밍 언어를 감지합니다.

    각 언어의 특징적인 패턴이 코드에 얼마나 등장하는지 점수를 매겨서
    가장 높은 점수의 언어를 반환합니다.

    Args:
        code: 분석할 코드 문자열

    Returns:
        감지된 언어 이름 ("c", "java", "python" 중 하나)
    """
    # 각 언어의 점수를 0으로 시작
    scores: dict[str, int] = {"c": 0, "java": 0, "python": 0}

    # 각 언어의 패턴을 코드에서 찾아서 점수를 올립니다
    for lang, patterns in _LANG_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, code, re.MULTILINE):
                scores[lang] += 1

    # 가장 높은 점수의 언어를 반환합니다
    return max(scores, key=lambda lang: scores[lang])


def _extract_code_block(query: str) -> str:
    """
    사용자 입력에서 마크다운 코드 블록(```...```)을 추출합니다.

    코드 블록이 없으면 입력 전체를 코드로 간주합니다.

    Args:
        query: 사용자 입력 텍스트 (코드 블록이 포함될 수 있음)

    Returns:
        추출된 코드 문자열

    예시:
        입력: "이 코드 분석해줘\\n```python\\nprint('hello')\\n```"
        출력: "print('hello')"
    """
    # ```언어명\n코드\n``` 형태의 코드 블록 찾기
    match = re.search(r"```(?:\w+)?\n(.*?)```", query, re.DOTALL)

    if match:
        # 코드 블록 안의 내용만 추출 (앞뒤 공백 제거)
        return match.group(1).strip()

    # 코드 블록이 없으면 입력 전체를 코드로 사용
    return query.strip()


def language_detect_func(original_query: str):
    """
    사용자 입력에서 코드를 추출하고 언어를 감지합니다.

    Args:
        original_query: 사용자가 입력한 텍스트 (코드 포함)

    Yields:
        tracer_code와 detected_language를 포함하는 Event

    state에 저장되는 값:
        - tracer_code       : 추출된 코드 (tracer_agent가 이 코드를 분석)
        - detected_language : 감지된 언어 ("c", "java", "python")
    """
    # 1단계: 마크다운 코드 블록에서 코드 추출
    extracted_code = _extract_code_block(original_query)

    # 2단계: 추출한 코드의 언어 감지
    detected_language = _detect_language(extracted_code)

    # state에 저장 (tracer_agent가 이 값들을 프롬프트에서 사용)
    yield Event(
        state={
            "tracer_code": extracted_code,
            "detected_language": detected_language,
        }
    )
