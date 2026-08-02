"""Communication interview API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class TranscriptTurn(APIModel):
    role: str
    content: str
    timestamp: float | None = None
    seconds_from_start: float | None = None


class DimensionScore(APIModel):
    id: str
    label: str
    score: float = Field(ge=0, le=5)
    feedback: str = ""


class GradedInterviewPayload(APIModel):
    score_percent: float = Field(ge=0, le=100)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    coach_summary: str = ""
    evidence_quotes: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)


class CommunicationInterviewOut(APIModel):
    id: UUID
    status: str
    domains: list[str] = Field(default_factory=list)
    conversation_url: str | None = None
    tavus_conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    score_percent: float | None = None
    dimension_count: int | None = None
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    rubric_scores: dict = Field(default_factory=dict)
    coach_summary: str | None = None
    evidence_quotes: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    scored_at: datetime | None = None
    error_message: str | None = None
    test_mode: bool = False
    created_at: datetime


class InterviewStartRequest(APIModel):
    test_mode: bool | None = None
