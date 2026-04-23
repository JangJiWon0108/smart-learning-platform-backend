"""
코드 실행 흐름 시각화(tracer) 에이전트의 출력 스키마.

코드를 한 줄씩 실행하면서 변수 상태, 메모리, 콜스택 등을
단계별로 기록한 결과를 담습니다.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryCell(BaseModel):
    """
    C 언어 포인터용 메모리 셀 정보.

    C에서 포인터 변수가 있을 때, 해당 메모리 주소와 값을 추적합니다.
    """

    address: str = Field(default="", description="메모리 주소 (예: 0x1000)")
    value: Any = Field(default=None, description="해당 주소에 저장된 값")
    type: str = Field(default="", description="데이터 타입 (예: int*, char*)")
    points_to: str = Field(default="", description="이 포인터가 가리키는 주소")


class HeapObject(BaseModel):
    """
    Java/Python의 힙(heap) 메모리에 생성된 객체 정보.

    Java의 new, Python의 객체 생성 시 이 형태로 추적합니다.
    """

    id: str = Field(..., description="객체 참조 ID (Java의 hashCode, Python의 id())")
    class_name: str = Field(default="", description="클래스 이름")
    fields: dict[str, Any] = Field(default_factory=dict, description="필드 이름 → 현재 값")


class ExecutionStep(BaseModel):
    """
    코드 실행 중 한 단계(한 줄)의 상태 스냅샷.

    실제 디버거처럼 코드를 한 줄 실행할 때마다 변수 상태 등을 기록합니다.
    """

    step: int = Field(..., description="실행 순서 번호 (1부터 시작)")
    line: int = Field(..., description="소스 코드 라인 번호 (1부터 시작)")
    code: str = Field(..., description="현재 실행 중인 코드 한 줄의 텍스트")

    # 현재 이 줄이 실행된 후의 변수 상태 (스코프 내 모든 변수)
    variables: dict[str, Any] = Field(default_factory=dict, description="현재 스코프 변수명 → 값")

    # C 언어 포인터 추적 (Java/Python은 비어있음)
    memory: list[MemoryCell] = Field(default_factory=list, description="C 포인터 메모리 상태")

    # Java/Python 힙 객체 추적 (C는 비어있음)
    heap: list[HeapObject] = Field(default_factory=list, description="Java/Python 힙 객체 상태")

    # 현재 실행 중인 함수 호출 스택 (바깥 → 안쪽 순서)
    # 예: ["main", "add"] = main 안에서 add 함수를 호출 중
    call_stack: list[str] = Field(default_factory=list, description="현재 콜스택 (함수명 목록)")

    # 이번 단계에서 새로 생기거나 값이 바뀐 변수 이름 목록
    changed_vars: list[str] = Field(default_factory=list, description="이번 단계에서 변경된 변수 이름")

    # 이 줄에서 무슨 일이 일어나는지 한국어로 설명
    note: str = Field(default="", description="이 단계의 설명 주석")


class TracerOutput(BaseModel):
    """
    코드 실행 흐름 분석의 최종 결과.

    language부터 summary까지 프론트엔드에서 시각화에 필요한
    모든 정보를 담고 있습니다.
    """

    language: Literal["c", "java", "python"] = Field(..., description="감지된 프로그래밍 언어")
    original_code: str = Field(..., description="분석한 원본 코드")
    steps: list[ExecutionStep] = Field(..., description="단계별 실행 흐름 목록")
    title: str = Field(..., description="코드 주제 키워드 (예: 상속과 생성자, 재귀 함수, 포인터 연산)")
    final_output: str = Field(default="", description="프로그램이 콘솔에 출력하는 최종 결과")
    summary: str = Field(..., description="전체 실행 흐름을 2~3문장으로 요약")
