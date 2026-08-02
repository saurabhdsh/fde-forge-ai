"""Learner profile and resume repositories."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learner import AIExtractionRecord, LearnerProfile, ResumeDocument


class LearnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user(
        self, user_id: UUID, organization_id: UUID
    ) -> LearnerProfile | None:
        result = await self.session.execute(
            select(LearnerProfile)
            .options(
                selectinload(LearnerProfile.resumes).selectinload(ResumeDocument.ai_extractions)
            )
            .where(
                LearnerProfile.user_id == user_id,
                LearnerProfile.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self, profile_id: UUID, organization_id: UUID
    ) -> LearnerProfile | None:
        result = await self.session.execute(
            select(LearnerProfile)
            .options(selectinload(LearnerProfile.resumes))
            .where(
                LearnerProfile.id == profile_id,
                LearnerProfile.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, profile: LearnerProfile) -> LearnerProfile:
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_resume(
        self, resume_id: UUID, organization_id: UUID
    ) -> ResumeDocument | None:
        result = await self.session.execute(
            select(ResumeDocument)
            .options(selectinload(ResumeDocument.ai_extractions))
            .where(
                ResumeDocument.id == resume_id,
                ResumeDocument.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_resumes_not_latest(self, learner_profile_id: UUID) -> None:
        await self.session.execute(
            update(ResumeDocument)
            .where(ResumeDocument.learner_profile_id == learner_profile_id)
            .values(is_latest=False)
        )

    async def create_resume(self, resume: ResumeDocument) -> ResumeDocument:
        self.session.add(resume)
        await self.session.flush()
        return resume

    async def create_extraction(self, record: AIExtractionRecord) -> AIExtractionRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_extraction(
        self, extraction_id: UUID, organization_id: UUID
    ) -> AIExtractionRecord | None:
        result = await self.session.execute(
            select(AIExtractionRecord).where(
                AIExtractionRecord.id == extraction_id,
                AIExtractionRecord.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()
