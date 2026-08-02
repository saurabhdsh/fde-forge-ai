"""Learning plan API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class GeneratedPlanItem(APIModel):
    skill_code: str
    priority: int = Field(ge=1)
    rationale: str | None = None
    estimated_hours: float | None = Field(default=None, ge=0.5, le=40)


class GeneratedLearningPlanPayload(APIModel):
    summary: str
    items: list[GeneratedPlanItem] = Field(min_length=1)


class LearningPlanItemUpdate(APIModel):
    status: str = Field(pattern="^(todo|in_progress|done)$")


class LearningPlanItemOut(APIModel):
    id: UUID
    skill_id: UUID
    skill_code: str | None = None
    skill_name: str | None = None
    priority: int
    status: str
    rationale: str | None = None
    estimated_hours: float | None = None


class LearningPlanOut(APIModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    source_assessment_id: UUID | None = None
    status: str
    summary: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime
    items: list[LearningPlanItemOut] = Field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
