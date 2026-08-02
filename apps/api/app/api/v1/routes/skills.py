"""Skills taxonomy routes."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentContext, DbSession
from app.api.responses import success
from app.repositories.skills import SkillsRepository
from app.schemas.skills import CompetencyPillarOut, SkillLevelOut, SkillOut

router = APIRouter()


@router.get("/pillars")
async def list_pillars(db: DbSession, ctx: CurrentContext) -> dict:
    repo = SkillsRepository(db)
    pillars = await repo.list_pillars()
    return success(
        [CompetencyPillarOut.model_validate(p) for p in pillars],
        correlation_id=ctx.correlation_id,
        total=len(pillars),
    )


@router.get("")
async def list_skills(
    db: DbSession,
    ctx: CurrentContext,
    domain: str | None = Query(default=None),
) -> dict:
    repo = SkillsRepository(db)
    skills = await repo.list_skills(domain=domain)
    return success(
        [SkillOut.model_validate(s) for s in skills],
        correlation_id=ctx.correlation_id,
        total=len(skills),
    )


@router.get("/levels")
async def list_levels(db: DbSession, ctx: CurrentContext) -> dict:
    repo = SkillsRepository(db)
    levels = await repo.list_levels()
    return success(
        [SkillLevelOut.model_validate(level) for level in levels],
        correlation_id=ctx.correlation_id,
        total=len(levels),
    )
