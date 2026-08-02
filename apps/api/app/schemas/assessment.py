"""Assessment API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class GeneratedQuestion(APIModel):
    skill_code: str
    stem: str
    choices: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str | None = None


class GeneratedAssessmentPayload(APIModel):
    questions: list[GeneratedQuestion] = Field(min_length=1)


class AssessmentAnswerIn(APIModel):
    question_id: UUID
    selected_index: int = Field(ge=0, le=3)


class AssessmentSubmitRequest(APIModel):
    answers: list[AssessmentAnswerIn] = Field(min_length=1)


class AssessmentDraftRequest(APIModel):
    answers: list[AssessmentAnswerIn] = Field(default_factory=list)


class AssessmentQuestionOut(APIModel):
    id: UUID
    skill_id: UUID
    skill_code: str | None = None
    skill_name: str | None = None
    stem: str
    choices: list[str]
    sort_order: int
    # Revealed only after scoring
    correct_index: int | None = None
    explanation: str | None = None
    selected_index: int | None = None
    is_correct: bool | None = None


class AssessmentOut(APIModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    kind: str
    status: str
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    score_percent: float | None = None
    correct_count: int | None = None
    total_count: int | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    questions: list[AssessmentQuestionOut] = Field(default_factory=list)
    draft_answers: list[AssessmentAnswerIn] = Field(default_factory=list)
