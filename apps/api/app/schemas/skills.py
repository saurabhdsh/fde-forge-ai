"""Skills taxonomy schemas."""

from uuid import UUID

from app.schemas.common import APIModel


class CompetencyPillarOut(APIModel):
    id: UUID
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool


class SkillOut(APIModel):
    id: UUID
    code: str
    name: str
    description: str | None
    pillar_id: UUID
    category: str
    domain: str
    difficulty: str
    version: int
    is_active: bool
    parent_skill_id: UUID | None = None


class LearnerSkillOut(APIModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    skill_code: str
    pillar_name: str | None = None
    proficiency_level: str
    score: float | None
    confidence: float | None
    source: str
    confirmed: bool
    notes: str | None = None


class SkillLevelOut(APIModel):
    code: str
    name: str
    rank: int
    description: str | None
