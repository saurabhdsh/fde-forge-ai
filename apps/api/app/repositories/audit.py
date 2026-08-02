"""Audit log repository — append only."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if action:
            query = query.where(AuditLog.action == action)
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
