"""Course API schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel

VisualType = Literal["map", "diagram", "process", "timeline", "cards", "none"]


class GeneratedSelfCheck(APIModel):
    question: str
    answer: str


class GeneratedSlide(APIModel):
    title: str
    body_markdown: str
    visual_type: VisualType = "none"
    visual_payload: dict[str, Any] = Field(default_factory=dict)
    key_takeaway: str | None = None
    self_check: GeneratedSelfCheck | None = None


class GeneratedModule(APIModel):
    title: str
    objectives: list[str] = Field(default_factory=list)
    slides: list[GeneratedSlide] = Field(min_length=1)


class GeneratedCoursePayload(APIModel):
    title: str
    summary: str
    learning_goals: list[str] = Field(default_factory=list)
    modules: list[GeneratedModule] = Field(min_length=1)


class CourseSlideOut(APIModel):
    id: UUID
    module_id: UUID
    title: str
    body_markdown: str
    visual_type: str
    visual_payload: dict[str, Any] = Field(default_factory=dict)
    key_takeaway: str | None = None
    self_check: dict[str, Any] | None = None
    sort_order: int
    completed: bool = False


class CourseModuleOut(APIModel):
    id: UUID
    title: str
    objectives: list[str] = Field(default_factory=list)
    sort_order: int
    status: str
    slides: list[CourseSlideOut] = Field(default_factory=list)


class CourseProgressOut(APIModel):
    percent_complete: float = 0
    completed_slide_ids: list[str] = Field(default_factory=list)
    current_module_id: UUID | None = None
    current_slide_id: UUID | None = None
    completed_at: datetime | None = None


class CourseOut(APIModel):
    id: UUID
    domain: str
    title: str
    summary: str | None = None
    status: str
    learning_goals: list[str] = Field(default_factory=list)
    selected_topics: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    modules: list[CourseModuleOut] = Field(default_factory=list)
    progress: CourseProgressOut | None = None
    total_slides: int = 0
    completed_slides: int = 0


class CourseTopicOut(APIModel):
    id: str
    label: str
    blurb: str
    group: str


class CourseCatalogItem(APIModel):
    domain: str
    required: bool = True
    course: CourseOut | None = None
    title_hint: str
    description: str
    topics: list[CourseTopicOut] = Field(default_factory=list)
    selected_topic_ids: list[str] = Field(default_factory=list)


class CourseCatalogOut(APIModel):
    domains: list[str]
    items: list[CourseCatalogItem]
    assessment_unlocked: bool


class SelectTopicsRequest(APIModel):
    topic_ids: list[str] = Field(min_length=1)


class EnsureCourseRequest(APIModel):
    topic_ids: list[str] | None = None
    force: bool = False


class CompleteSlideRequest(APIModel):
    slide_id: UUID
