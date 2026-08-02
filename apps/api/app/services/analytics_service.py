"""Organization analytics for admin overview and interview readiness."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.assessment import Assessment
from app.models.coding_assessment import CodingAssessment
from app.models.identity import Organization, Role, User, UserRole
from app.models.learner import LearnerProfile
from app.models.learning_plan import LearningPlan
from app.schemas.analytics import (
    CandidateInterviewReadinessOut,
    InterviewReadinessOut,
    OrgOverviewOut,
)

MCQ_PASS_THRESHOLD = 70.0
CODING_PASS_THRESHOLD = 70.0


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def org_overview(self, organization_id: UUID) -> OrgOverviewOut:
        org = await self.session.get(Organization, organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        candidates_count = await self.session.scalar(
            select(func.count(func.distinct(UserRole.user_id)))
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.organization_id == organization_id,
                Role.code == "learner",
            )
        ) or 0

        profiles_completed = await self.session.scalar(
            select(func.count())
            .select_from(LearnerProfile)
            .where(
                LearnerProfile.organization_id == organization_id,
                LearnerProfile.profile_completed_at.is_not(None),
            )
        ) or 0

        skills_confirmed = await self.session.scalar(
            select(func.count())
            .select_from(LearnerProfile)
            .where(
                LearnerProfile.organization_id == organization_id,
                LearnerProfile.skills_confirmed_at.is_not(None),
            )
        ) or 0

        assessments_scored = await self.session.scalar(
            select(func.count())
            .select_from(Assessment)
            .where(
                Assessment.organization_id == organization_id,
                Assessment.status == "scored",
            )
        ) or 0

        plans_active = await self.session.scalar(
            select(func.count())
            .select_from(LearningPlan)
            .where(
                LearningPlan.organization_id == organization_id,
                LearningPlan.status.in_(["active", "draft"]),
            )
        ) or 0

        avg_score = await self.session.scalar(
            select(func.avg(Assessment.score_percent)).where(
                Assessment.organization_id == organization_id,
                Assessment.status == "scored",
                Assessment.score_percent.is_not(None),
            )
        )

        return OrgOverviewOut(
            organization_id=str(organization_id),
            organization_name=org.name,
            candidates_count=int(candidates_count),
            profiles_completed=int(profiles_completed),
            skills_confirmed=int(skills_confirmed),
            assessments_scored=int(assessments_scored),
            plans_active=int(plans_active),
            avg_assessment_score=round(float(avg_score), 1) if avg_score is not None else None,
        )

    async def interview_readiness(self, organization_id: UUID) -> InterviewReadinessOut:
        org = await self.session.get(Organization, organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        learners_result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.organization_id == organization_id,
                UserRole.organization_id == organization_id,
                Role.code == "learner",
            )
            .order_by(User.last_name.asc(), User.first_name.asc())
        )
        learners = list(learners_result.scalars().unique().all())

        profiles_result = await self.session.execute(
            select(LearnerProfile).where(LearnerProfile.organization_id == organization_id)
        )
        profiles_by_user = {p.user_id: p for p in profiles_result.scalars().all()}

        latest_mcq = await self._latest_assessment_map(organization_id)
        latest_coding = await self._latest_coding_map(organization_id)

        candidates: list[CandidateInterviewReadinessOut] = []
        ready_count = 0
        for user in learners:
            mcq = latest_mcq.get(user.id)
            coding = latest_coding.get(user.id)
            profile = profiles_by_user.get(user.id)
            skills_confirmed = bool(profile and profile.skills_confirmed_at)

            mcq_status = mcq["status"] if mcq else None
            mcq_score = mcq["score_percent"] if mcq else None
            coding_status = coding["status"] if coding else None
            coding_score = coding["score_percent"] if coding else None

            if mcq_status != "scored":
                mcq_score = None
            if coding_status != "scored":
                coding_score = None

            ready, reason = self._readiness(
                mcq_status=mcq_status,
                mcq_score=mcq_score,
                coding_status=coding_status,
                coding_score=coding_score,
            )
            if ready:
                ready_count += 1

            candidates.append(
                CandidateInterviewReadinessOut(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    account_status=user.status,
                    skills_confirmed=skills_confirmed,
                    mcq_status=mcq_status,
                    mcq_score_percent=round(mcq_score, 1) if mcq_score is not None else None,
                    coding_status=coding_status,
                    coding_score_percent=round(coding_score, 1)
                    if coding_score is not None
                    else None,
                    ready_for_manual_interview=ready,
                    readiness_reason=reason,
                )
            )

        candidates.sort(
            key=lambda c: (
                0 if c.ready_for_manual_interview else 1,
                c.last_name.lower(),
                c.first_name.lower(),
            )
        )

        return InterviewReadinessOut(
            organization_id=str(organization_id),
            organization_name=org.name,
            mcq_pass_threshold=MCQ_PASS_THRESHOLD,
            coding_pass_threshold=CODING_PASS_THRESHOLD,
            ready_count=ready_count,
            candidates=candidates,
        )

    async def _latest_assessment_map(
        self, organization_id: UUID
    ) -> dict[UUID, dict[str, float | str | None]]:
        ranked = (
            select(
                Assessment.user_id.label("user_id"),
                Assessment.status.label("status"),
                Assessment.score_percent.label("score_percent"),
                func.row_number()
                .over(
                    partition_by=Assessment.user_id,
                    order_by=Assessment.created_at.desc(),
                )
                .label("rn"),
            )
            .where(
                Assessment.organization_id == organization_id,
                Assessment.kind == "baseline",
            )
            .subquery()
        )
        result = await self.session.execute(select(ranked).where(ranked.c.rn == 1))
        out: dict[UUID, dict[str, float | str | None]] = {}
        for row in result.all():
            score = float(row.score_percent) if row.score_percent is not None else None
            out[row.user_id] = {"status": row.status, "score_percent": score}
        return out

    async def _latest_coding_map(
        self, organization_id: UUID
    ) -> dict[UUID, dict[str, float | str | None]]:
        ranked = (
            select(
                CodingAssessment.user_id.label("user_id"),
                CodingAssessment.status.label("status"),
                CodingAssessment.score_percent.label("score_percent"),
                func.row_number()
                .over(
                    partition_by=CodingAssessment.user_id,
                    order_by=CodingAssessment.created_at.desc(),
                )
                .label("rn"),
            )
            .where(CodingAssessment.organization_id == organization_id)
            .subquery()
        )
        result = await self.session.execute(select(ranked).where(ranked.c.rn == 1))
        out: dict[UUID, dict[str, float | str | None]] = {}
        for row in result.all():
            score = float(row.score_percent) if row.score_percent is not None else None
            out[row.user_id] = {"status": row.status, "score_percent": score}
        return out

    @staticmethod
    def _readiness(
        *,
        mcq_status: str | None,
        mcq_score: float | None,
        coding_status: str | None,
        coding_score: float | None,
    ) -> tuple[bool, str]:
        missing: list[str] = []
        if mcq_status != "scored" or mcq_score is None:
            missing.append("MCQ not scored")
        elif mcq_score < MCQ_PASS_THRESHOLD:
            missing.append(f"MCQ {mcq_score:.0f}% < {MCQ_PASS_THRESHOLD:.0f}%")

        if coding_status != "scored" or coding_score is None:
            missing.append("Coding not scored")
        elif coding_score < CODING_PASS_THRESHOLD:
            missing.append(f"Coding {coding_score:.0f}% < {CODING_PASS_THRESHOLD:.0f}%")

        if missing:
            return False, "; ".join(missing)
        return True, "MCQ and Coding both ≥ 70% — ready for manual interview"
