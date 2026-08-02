"""Audit logging service — append-only from application perspective."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AuditRepository(session)

    async def log(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | UUID | None = None,
        organization_id: UUID | None = None,
        actor_id: UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            organization_id=organization_id,
            actor_id=actor_id,
            before_state=before,
            after_state=after,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            metadata_=metadata or {},
            notes=notes,
        )
        return await self.repo.append(entry)

    async def list_logs(
        self,
        organization_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
    ) -> list[AuditLog]:
        return await self.repo.list_for_org(
            organization_id, limit=limit, offset=offset, action=action
        )
