"""Organization routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentContext, DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
)
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.get("/current")
async def get_current_org(db: DbSession, ctx: CurrentContext) -> dict:
    service = OrganizationService(db)
    org = await service.get(ctx.organization_id)
    return success(org, correlation_id=ctx.correlation_id)


@router.patch("/current")
async def update_current_org(
    payload: OrganizationUpdate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("organization.manage"))],
) -> dict:
    service = OrganizationService(db)
    org = await service.update(
        ctx.organization_id,
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(org, correlation_id=ctx.correlation_id)


@router.get("/current/settings")
async def get_settings(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("organization.view"))],
) -> dict:
    service = OrganizationService(db)
    settings = await service.get_settings(ctx.organization_id)
    return success(settings, correlation_id=ctx.correlation_id)


@router.patch("/current/settings")
async def update_settings(
    payload: OrganizationSettingsUpdate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("organization.manage"))],
) -> dict:
    service = OrganizationService(db)
    settings = await service.update_settings(
        ctx.organization_id,
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(settings, correlation_id=ctx.correlation_id)


@router.post("")
async def create_organization(
    payload: OrganizationCreate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("organization.manage"))],
) -> dict:
    """Platform-level create; requires organization.manage (super admin in seed)."""
    if not ctx.user.is_super_admin:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Only platform super admins can create organizations")
    service = OrganizationService(db)
    org = await service.create(
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(org, correlation_id=ctx.correlation_id)


@router.get("/{organization_id}")
async def get_organization(
    organization_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("organization.view"))],
) -> dict:
    if organization_id != ctx.organization_id and not ctx.user.is_super_admin:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Cross-tenant access denied")
    service = OrganizationService(db)
    org = await service.get(organization_id)
    return success(org, correlation_id=ctx.correlation_id)
