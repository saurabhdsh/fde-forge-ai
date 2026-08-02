"""Learning plan routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.schemas.learning_plan import LearningPlanItemUpdate
from app.services.learning_plan_service import LearningPlanService

router = APIRouter()


@router.get("/me/latest")
async def latest_plan(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearningPlanService(db)
    data = await service.get_latest(ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.patch("/me/items/{item_id}")
async def update_plan_item(
    item_id: UUID,
    payload: LearningPlanItemUpdate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearningPlanService(db)
    data = await service.update_item(
        item_id=item_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        payload=payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(data, correlation_id=ctx.correlation_id)
