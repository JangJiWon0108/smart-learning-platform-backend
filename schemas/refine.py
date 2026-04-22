from pydantic import BaseModel, Field


class RefinedProblem(BaseModel):
    id: str = Field(..., description="문제 ID")
    refined_question: str = Field(
        ...,
        description="정제된 문제 지문. [cs], colored by 등 아티팩트 제거. 코드/테이블은 여기서 제외.",
    )
    refined_code: str | None = Field(
        default=None,
        description="정제된 코드 또는 SQL 테이블 문자열. 없으면 None.",
    )
    code_language: str | None = Field(
        default=None,
        description="코드 언어 식별자. java | c | python | sql 중 하나. 없으면 None.",
    )


class RefineOutput(BaseModel):
    refined_problems: list[RefinedProblem] = Field(..., description="정제된 문제 목록")
