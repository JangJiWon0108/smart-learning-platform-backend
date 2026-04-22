from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryCell(BaseModel):
    address: str = Field(default="", description="메모리 주소 (C 포인터용, 예: 0x1000)")
    value: Any = Field(default=None, description="저장된 값")
    type: str = Field(default="", description="데이터 타입")
    points_to: str = Field(default="", description="가리키는 주소 (포인터인 경우)")


class HeapObject(BaseModel):
    id: str = Field(..., description="객체 참조 ID (Java new, Python id())")
    class_name: str = Field(default="", description="클래스 이름")
    fields: dict[str, Any] = Field(default_factory=dict, description="필드 이름→값")


class ExecutionStep(BaseModel):
    step: int = Field(..., description="실행 순서 번호 (1부터 시작)")
    line: int = Field(..., description="소스 코드 라인 번호")
    code: str = Field(..., description="현재 실행 중인 코드 라인 텍스트")
    variables: dict[str, Any] = Field(default_factory=dict, description="현재 스코프 변수명→값")
    memory: list[MemoryCell] = Field(default_factory=list, description="C 포인터 메모리 상태")
    heap: list[HeapObject] = Field(default_factory=list, description="Java/Python 힙 객체 상태")
    call_stack: list[str] = Field(default_factory=list, description="현재 콜스택 (함수명 목록)")
    changed_vars: list[str] = Field(default_factory=list, description="이번 단계에서 변경된 변수 이름")
    note: str = Field(default="", description="이 단계의 설명 주석")


class TracerOutput(BaseModel):
    language: Literal["c", "java", "python"] = Field(..., description="감지된 프로그래밍 언어")
    original_code: str = Field(..., description="원본 코드")
    steps: list[ExecutionStep] = Field(..., description="단계별 실행 흐름")
    title: str = Field(..., description="코드 주제 키워드 (예: 상속과 생성자, 재귀 함수, 포인터 연산)")
    final_output: str = Field(default="", description="프로그램 최종 출력값")
    summary: str = Field(..., description="전체 실행 흐름 요약")

