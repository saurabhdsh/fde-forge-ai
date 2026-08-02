"""Analytics / dashboard schemas."""

from uuid import UUID

from app.schemas.common import APIModel


class OrgOverviewOut(APIModel):
    organization_id: str
    organization_name: str
    candidates_count: int
    profiles_completed: int
    skills_confirmed: int
    assessments_scored: int
    plans_active: int
    avg_assessment_score: float | None = None


class CandidateInterviewReadinessOut(APIModel):
    user_id: UUID
    username: str | None = None
    first_name: str
    last_name: str
    email: str
    account_status: str
    skills_confirmed: bool
    mcq_status: str | None = None
    mcq_score_percent: float | None = None
    coding_status: str | None = None
    coding_score_percent: float | None = None
    ready_for_manual_interview: bool
    readiness_reason: str


class InterviewReadinessOut(APIModel):
    organization_id: str
    organization_name: str
    mcq_pass_threshold: float
    coding_pass_threshold: float
    ready_count: int
    candidates: list[CandidateInterviewReadinessOut]
