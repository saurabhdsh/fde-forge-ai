"""Analytics routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/org-overview")
async def org_overview(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("analytics.executive"))],
) -> dict:
    service = AnalyticsService(db)
    data = await service.org_overview(ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/interview-readiness")
async def interview_readiness(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("analytics.executive"))],
) -> dict:
    service = AnalyticsService(db)
    data = await service.interview_readiness(ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)
