"""Learner profile and resume extraction schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import APIModel


class ExtractedSkill(APIModel):
    name: str
    category: str | None = None
    proficiency_level: str = "foundational"
    years_experience: float | None = None
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)


class ExtractedExperience(APIModel):
    title: str
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    technologies: list[str] = Field(default_factory=list)
    domain: str | None = None


class ExtractedCertification(APIModel):
    name: str
    issuer: str | None = None
    year: str | None = None


class ResumeExtractionPayload(APIModel):
    """Structured AI output for resume skill extraction."""

    summary: str | None = None
    years_of_experience: float | None = None
    skills: list[ExtractedSkill] = Field(default_factory=list)
    technical_experience: list[ExtractedExperience] = Field(default_factory=list)
    project_experience: list[ExtractedExperience] = Field(default_factory=list)
    domain_experience: list[str] = Field(default_factory=list)
    certifications: list[ExtractedCertification] = Field(default_factory=list)
    suggested_target_roles: list[str] = Field(default_factory=list)
    suggested_domains: list[str] = Field(default_factory=list)

    @field_validator("skills")
    @classmethod
    def limit_skills(cls, value: list[ExtractedSkill]) -> list[ExtractedSkill]:
        return value[:80]


class LearnerProfileUpdate(APIModel):
    target_fde_role: str | None = None
    career_interests: list[str] | None = None
    domain_preferences: list[str] | None = None
    technical_experience: dict | None = None
    project_experience: list | None = None
    domain_experience: dict | None = None
    existing_certifications: list | None = None
    years_of_experience: int | None = None
    available_weekly_hours: int | None = None
    summary: str | None = None
    consent_privacy: bool | None = None
    consent_ai_processing: bool | None = None


class LearnerProfileOut(APIModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    onboarding_status: str
    target_fde_role: str | None
    career_interests: list
    domain_preferences: list
    technical_experience: dict
    project_experience: list
    domain_experience: dict
    existing_certifications: list
    years_of_experience: int | None
    available_weekly_hours: int | None
    consent_privacy: bool
    consent_ai_processing: bool
    profile_completed_at: datetime | None
    skills_confirmed_at: datetime | None
    summary: str | None


class ResumeDocumentOut(APIModel):
    id: UUID
    original_filename: str
    content_type: str
    file_extension: str
    file_size_bytes: int
    extraction_status: str
    is_latest: bool
    created_at: datetime
    has_extracted_text: bool = False


class AIExtractionOut(APIModel):
    id: UUID
    resume_document_id: UUID
    provider: str
    model: str
    prompt_version: str
    status: str
    validated_payload: ResumeExtractionPayload | None = None
    edited_payload: ResumeExtractionPayload | None = None
    confirmed_payload: ResumeExtractionPayload | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error_message: str | None = None
    hallucination_risk_score: float | None = None
    confirmed_at: datetime | None = None


class ConfirmSkillsRequest(APIModel):
    payload: ResumeExtractionPayload
