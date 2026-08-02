"""Learner profile and resume ingestion models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.identity import User


class LearnerProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "learner_profiles"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    onboarding_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="invited"
    )
    target_fde_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    career_interests: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    domain_preferences: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    course_topic_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    technical_experience: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    project_experience: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    domain_experience: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    existing_certifications: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_weekly_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_privacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_ai_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    profile_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    skills_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="learner_profile")
    resumes: Mapped[list[ResumeDocument]] = relationship(
        back_populates="learner_profile", cascade="all, delete-orphan"
    )


class ResumeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resume_documents"

    learner_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    extraction_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    learner_profile: Mapped[LearnerProfile] = relationship(back_populates="resumes")
    ai_extractions: Mapped[list[AIExtractionRecord]] = relationship(
        back_populates="resume_document", cascade="all, delete-orphan"
    )


class AIExtractionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_extraction_records"

    resume_document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resume_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validated_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confirmed_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    hallucination_risk_score: Mapped[float | None] = mapped_column(nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    resume_document: Mapped[ResumeDocument] = relationship(back_populates="ai_extractions")
