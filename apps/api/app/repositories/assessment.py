"""Assessment repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment, AssessmentAnswer, AssessmentQuestion
from app.models.skills import Skill


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, assessment: Assessment) -> Assessment:
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def get_by_id(
        self, assessment_id: UUID, organization_id: UUID
    ) -> Assessment | None:
        result = await self.session.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.questions).selectinload(AssessmentQuestion.skill),
                selectinload(Assessment.answers),
            )
            .where(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_user(
        self,
        user_id: UUID,
        organization_id: UUID,
        *,
        kind: str | None = "baseline",
    ) -> Assessment | None:
        stmt = (
            select(Assessment)
            .options(
                selectinload(Assessment.questions).selectinload(AssessmentQuestion.skill),
                selectinload(Assessment.answers),
            )
            .where(
                Assessment.user_id == user_id,
                Assessment.organization_id == organization_id,
            )
        )
        if kind:
            stmt = stmt.where(Assessment.kind == kind)
        result = await self.session.execute(
            stmt.order_by(Assessment.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def add_question(self, question: AssessmentQuestion) -> AssessmentQuestion:
        self.session.add(question)
        await self.session.flush()
        return question

    async def add_answer(self, answer: AssessmentAnswer) -> AssessmentAnswer:
        self.session.add(answer)
        await self.session.flush()
        return answer

    async def get_skill_map(self, codes: list[str]) -> dict[str, Skill]:
        if not codes:
            return {}
        result = await self.session.execute(select(Skill).where(Skill.code.in_(codes)))
        return {s.code: s for s in result.scalars().all()}
