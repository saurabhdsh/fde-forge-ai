"""Coding playground repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coding_assessment import CodingAssessment, CodingQuestion, CodingSubmission


class CodingAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, assessment: CodingAssessment) -> CodingAssessment:
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def get_by_id(
        self, assessment_id: UUID, organization_id: UUID
    ) -> CodingAssessment | None:
        result = await self.session.execute(
            select(CodingAssessment)
            .options(
                selectinload(CodingAssessment.questions).selectinload(
                    CodingQuestion.submission
                ),
                selectinload(CodingAssessment.submissions),
            )
            .where(
                CodingAssessment.id == assessment_id,
                CodingAssessment.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_user(
        self, user_id: UUID, organization_id: UUID
    ) -> CodingAssessment | None:
        result = await self.session.execute(
            select(CodingAssessment)
            .options(
                selectinload(CodingAssessment.questions).selectinload(
                    CodingQuestion.submission
                ),
                selectinload(CodingAssessment.submissions),
            )
            .where(
                CodingAssessment.user_id == user_id,
                CodingAssessment.organization_id == organization_id,
            )
            .order_by(CodingAssessment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
