"""Schemas shared by the Vertex AI Search MCP server and client."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExamSearchResult(BaseModel):
    """A single parsed exam question search result."""

    question: str = ""
    answer: str = ""
    explanation: str = ""
    year: int | None = None
    round: int | None = None
    question_type: str = ""
    question_number: int | None = None
    score: float = 0.0


class SearchExamQuestionsResponse(BaseModel):
    """Parsed response returned by the search_exam_questions MCP tool."""

    results: list[ExamSearchResult] = Field(default_factory=list)
    query: str = ""
    filter_expression: str | None = None
