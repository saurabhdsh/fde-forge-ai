"""Domain course models for learner super-courses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from app.db.types import GUID, JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("user_id", "domain", name="uq_courses_user_domain"),
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
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generating")
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    learning_goals: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    selected_topics: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modules: Mapped[list[CourseModule]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseModule.sort_order",
    )
    progress: Mapped[CourseProgress | None] = relationship(
        back_populates="course", uselist=False, cascade="all, delete-orphan"
    )


class CourseModule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_modules"

    course_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    objectives: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ready")

    course: Mapped[Course] = relationship(back_populates="modules")
    slides: Mapped[list[CourseSlide]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="CourseSlide.sort_order",
    )


class CourseSlide(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_slides"

    module_id: Mapped[UUID] = mapped_column(
        GUID,
        ForeignKey("course_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visual_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    visual_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    key_takeaway: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_check: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    module: Mapped[CourseModule] = relationship(back_populates="slides")


class CourseProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),)

    user_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_module_id: Mapped[UUID | None] = mapped_column(
        GUID, ForeignKey("course_modules.id", ondelete="SET NULL"), nullable=True
    )
    current_slide_id: Mapped[UUID | None] = mapped_column(
        GUID, ForeignKey("course_slides.id", ondelete="SET NULL"), nullable=True
    )
    completed_slide_ids: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    percent_complete: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped[Course] = relationship(back_populates="progress")
