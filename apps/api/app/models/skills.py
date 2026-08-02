"""Skills taxonomy and learner skill models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from app.db.types import GUID, JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CompetencyPillar(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "competency_pillars"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    skills: Mapped[list[Skill]] = relationship(back_populates="pillar")


class Skill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_skill_code_version"),)

    code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pillar_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("competency_pillars.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    parent_skill_id: Mapped[UUID | None] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    domain: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="foundational")
    evidence_requirements: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    assessment_mappings: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    learning_content_mappings: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    pillar: Mapped[CompetencyPillar] = relationship(back_populates="skills")
    parent: Mapped[Skill | None] = relationship(remote_side="Skill.id")


class SkillLevel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "skill_levels"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class LearnerSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "learner_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_learner_skill"),
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proficiency_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="not_assessed"
    )
    score: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="self_reported")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skill: Mapped[Skill] = relationship()
    evidence: Mapped[list[SkillEvidence]] = relationship(
        back_populates="learner_skill", cascade="all, delete-orphan"
    )


class SkillEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "skill_evidence"

    learner_skill_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("learner_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    learner_skill: Mapped[LearnerSkill] = relationship(back_populates="evidence")
