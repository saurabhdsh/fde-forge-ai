"""Learning plan models for Phase 2."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from app.db.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LearningPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "learning_plans"

    user_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_assessment_id: Mapped[UUID | None] = mapped_column(
        GUID,
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    items: Mapped[list[LearningPlanItem]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="LearningPlanItem.priority",
    )


class LearningPlanItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "learning_plan_items"

    plan_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("learning_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="todo")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    plan: Mapped[LearningPlan] = relationship(back_populates="items")
    skill: Mapped["Skill"] = relationship()  # noqa: F821
