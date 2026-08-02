"""Coding playground assessment models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from app.db.types import GUID, JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CodingAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "coding_assessments"

    user_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generating")
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    domains: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    questions: Mapped[list[CodingQuestion]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="CodingQuestion.sort_order",
    )
    submissions: Mapped[list[CodingSubmission]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class CodingQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "coding_questions"

    assessment_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("coding_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    prompt_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False, default="python")
    starter_code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic_tags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    domain_focus: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False, default="hard")
    rubric: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    reference_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assessment: Mapped[CodingAssessment] = relationship(back_populates="questions")
    submission: Mapped[CodingSubmission | None] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class CodingSubmission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "coding_submissions"

    assessment_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("coding_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("coding_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_scores: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    assessment: Mapped[CodingAssessment] = relationship(back_populates="submissions")
    question: Mapped[CodingQuestion] = relationship(back_populates="submission")
