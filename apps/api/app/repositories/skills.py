"""Skills taxonomy repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.skills import CompetencyPillar, LearnerSkill, Skill, SkillLevel


class SkillsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_pillars(self) -> list[CompetencyPillar]:
        result = await self.session.execute(
            select(CompetencyPillar).order_by(CompetencyPillar.sort_order)
        )
        return list(result.scalars().all())

    async def list_skills(self, *, domain: str | None = None) -> list[Skill]:
        query = select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name)
        if domain:
            query = query.where(Skill.domain == domain)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_skill_by_code(self, code: str) -> Skill | None:
        result = await self.session.execute(select(Skill).where(Skill.code == code))
        return result.scalar_one_or_none()

    async def get_skill_by_name_ci(self, name: str) -> Skill | None:
        result = await self.session.execute(
            select(Skill).where(Skill.name.ilike(name))
        )
        return result.scalars().first()

    async def list_levels(self) -> list[SkillLevel]:
        result = await self.session.execute(select(SkillLevel).order_by(SkillLevel.rank))
        return list(result.scalars().all())

    async def list_learner_skills(
        self, user_id: UUID, organization_id: UUID
    ) -> list[LearnerSkill]:
        result = await self.session.execute(
            select(LearnerSkill)
            .options(selectinload(LearnerSkill.skill).selectinload(Skill.pillar))
            .where(
                LearnerSkill.user_id == user_id,
                LearnerSkill.organization_id == organization_id,
            )
            .order_by(LearnerSkill.updated_at.desc())
        )
        return list(result.scalars().all())

    async def upsert_learner_skill(self, entity: LearnerSkill) -> LearnerSkill:
        existing = await self.session.execute(
            select(LearnerSkill).where(
                LearnerSkill.user_id == entity.user_id,
                LearnerSkill.skill_id == entity.skill_id,
            )
        )
        found = existing.scalar_one_or_none()
        if found:
            found.proficiency_level = entity.proficiency_level
            found.score = entity.score
            found.confidence = entity.confidence
            found.source = entity.source
            found.confirmed = entity.confirmed
            found.notes = entity.notes
            if entity.last_assessed_at is not None:
                found.last_assessed_at = entity.last_assessed_at
            await self.session.flush()
            return found
        self.session.add(entity)
        await self.session.flush()
        return entity
