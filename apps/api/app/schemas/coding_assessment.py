"""Coding playground schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class GeneratedCodingQuestion(APIModel):
    title: str
    prompt_markdown: str
    language: str = "python"
    starter_code: str
    topic_tags: list[str] = Field(default_factory=list)
    domain_focus: str | None = "technical"
    difficulty: str = "hard"
    rubric: list[str] = Field(default_factory=list)
    reference_solution: str | None = None


class GeneratedCodingPayload(APIModel):
    questions: list[GeneratedCodingQuestion] = Field(min_length=1)


class GradedCodingItem(APIModel):
    question_id: str
    score: float
    passed: bool
    feedback: str
    rubric_scores: dict[str, float] = Field(default_factory=dict)


class GradedCodingPayload(APIModel):
    results: list[GradedCodingItem] = Field(default_factory=list)


class CodingAnswerIn(APIModel):
    question_id: UUID
    code: str


class CodingSubmitRequest(APIModel):
    answers: list[CodingAnswerIn] = Field(min_length=1)


class CodingDraftRequest(APIModel):
    answers: list[CodingAnswerIn] = Field(default_factory=list)


class SyntaxCheckRequest(APIModel):
    code: str = ""
    language: str = "python"


class SyntaxDiagnosticOut(APIModel):
    line: int
    column: int
    message: str
    severity: str = "error"
    source: str = "python"


class SyntaxCheckOut(APIModel):
    ok: bool
    diagnostics: list[SyntaxDiagnosticOut] = Field(default_factory=list)


class CodingQuestionOut(APIModel):
    id: UUID
    title: str
    prompt_markdown: str
    language: str
    starter_code: str
    topic_tags: list[str] = Field(default_factory=list)
    domain_focus: str | None = None
    difficulty: str
    sort_order: int
    submitted_code: str | None = None
    score: float | None = None
    passed: bool | None = None
    feedback: str | None = None


class CodingAssessmentOut(APIModel):
    id: UUID
    status: str
    domains: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    score_percent: float | None = None
    passed_count: int | None = None
    total_count: int | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    questions: list[CodingQuestionOut] = Field(default_factory=list)
    draft_answers: list[CodingAnswerIn] = Field(default_factory=list)
