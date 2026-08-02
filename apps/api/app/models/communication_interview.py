"""Live avatar communication interview models (Tavus CVI)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CommunicationInterview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "communication_interviews"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="live")
    tavus_conversation_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    conversation_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    domains: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rubric_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    coach_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_quotes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
