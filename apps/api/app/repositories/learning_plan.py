"""Learning plan repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.skills import Skill


class LearningPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, plan: LearningPlan) -> LearningPlan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def get_by_id(self, plan_id: UUID, organization_id: UUID) -> LearningPlan | None:
        result = await self.session.execute(
            select(LearningPlan)
            .options(selectinload(LearningPlan.items).selectinload(LearningPlanItem.skill))
            .where(
                LearningPlan.id == plan_id,
                LearningPlan.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_user(
        self, user_id: UUID, organization_id: UUID
    ) -> LearningPlan | None:
        result = await self.session.execute(
            select(LearningPlan)
            .options(selectinload(LearningPlan.items).selectinload(LearningPlanItem.skill))
            .where(
                LearningPlan.user_id == user_id,
                LearningPlan.organization_id == organization_id,
            )
            .order_by(LearningPlan.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_item(
        self, item_id: UUID, organization_id: UUID
    ) -> LearningPlanItem | None:
        result = await self.session.execute(
            select(LearningPlanItem)
            .options(selectinload(LearningPlanItem.plan), selectinload(LearningPlanItem.skill))
            .join(LearningPlan)
            .where(
                LearningPlanItem.id == item_id,
                LearningPlan.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_skill_map(self, codes: list[str]) -> dict[str, Skill]:
        if not codes:
            return {}
        result = await self.session.execute(select(Skill).where(Skill.code.in_(codes)))
        return {s.code: s for s in result.scalars().all()}
