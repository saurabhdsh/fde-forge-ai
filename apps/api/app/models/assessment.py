"""Assessment models for Phase 2 baseline quizzes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Assessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assessments"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="baseline")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generating")
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    questions: Mapped[list[AssessmentQuestion]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.sort_order",
    )
    answers: Mapped[list[AssessmentAnswer]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assessment_questions"

    assessment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assessment: Mapped[Assessment] = relationship(back_populates="questions")
    skill: Mapped["Skill"] = relationship()  # noqa: F821


class AssessmentAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assessment_answers"

    assessment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    assessment: Mapped[Assessment] = relationship(back_populates="answers")
    question: Mapped[AssessmentQuestion] = relationship()
