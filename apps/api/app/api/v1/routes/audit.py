"""Audit log routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("")
async def list_audit_logs(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("audit.read"))],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
) -> dict:
    service = AuditService(db)
    logs = await service.list_logs(
        ctx.organization_id, limit=limit, offset=offset, action=action
    )
    data = [
        {
            "id": str(log.id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "before_state": log.before_state,
            "after_state": log.after_state,
            "ip_address": log.ip_address,
            "correlation_id": log.correlation_id,
            "created_at": log.created_at.isoformat(),
            "metadata": log.metadata_,
        }
        for log in logs
    ]
    return success(data, correlation_id=ctx.correlation_id, page_size=limit, page=offset // limit + 1)
