"""User management routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.schemas.users import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("")
async def list_users(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.view"))],
) -> dict:
    service = UserService(db)
    users = await service.list_users(ctx.organization_id)
    return success(users, correlation_id=ctx.correlation_id, total=len(users))


@router.post("")
async def create_user(
    payload: UserCreate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.create"))],
) -> dict:
    service = UserService(db)
    user = await service.create_user(
        ctx.organization_id,
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    generated = getattr(user, "_generated_password", None)
    return success(
        user,
        correlation_id=ctx.correlation_id,
        extra_meta={"generated_password": generated} if generated else None,
    )


@router.get("/me/password")
async def reveal_my_password(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.manage"))],
) -> dict:
    """Reveal the signed-in admin's recoverable password."""
    service = UserService(db)
    revealed = await service.reveal_password(
        organization_id=ctx.organization_id,
        target_user_id=ctx.user.id,
        actor=ctx.user,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(revealed, correlation_id=ctx.correlation_id)


@router.get("/{user_id}/password")
async def reveal_user_password(
    user_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.manage"))],
) -> dict:
    """Reveal a candidate/user password (admin only). Audited; plaintext never written to logs."""
    service = UserService(db)
    revealed = await service.reveal_password(
        organization_id=ctx.organization_id,
        target_user_id=user_id,
        actor=ctx.user,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(revealed, correlation_id=ctx.correlation_id)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.manage"))],
) -> dict:
    service = UserService(db)
    user = await service.update_user(
        ctx.organization_id,
        user_id,
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(user, correlation_id=ctx.correlation_id)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("user.manage"))],
) -> dict:
    service = UserService(db)
    await service.delete_user(
        ctx.organization_id,
        user_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success({"deleted": True, "user_id": str(user_id)}, correlation_id=ctx.correlation_id)
