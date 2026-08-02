"""Curriculum / course enrichment document repository."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import CourseEnrichmentDocument


class CurriculumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        domain: str | None = None,
        active_only: bool = True,
    ) -> list[CourseEnrichmentDocument]:
        stmt = select(CourseEnrichmentDocument).where(
            CourseEnrichmentDocument.organization_id == organization_id
        )
        if active_only:
            stmt = stmt.where(CourseEnrichmentDocument.is_active.is_(True))
        if domain:
            stmt = stmt.where(CourseEnrichmentDocument.domain == domain)
        stmt = stmt.order_by(CourseEnrichmentDocument.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_course_domain(
        self, organization_id: UUID, domain: str
    ) -> list[CourseEnrichmentDocument]:
        """Docs tagged for this domain or organization-wide ('all')."""
        result = await self.session.execute(
            select(CourseEnrichmentDocument)
            .where(
                CourseEnrichmentDocument.organization_id == organization_id,
                CourseEnrichmentDocument.is_active.is_(True),
                CourseEnrichmentDocument.extraction_status == "extracted",
                or_(
                    CourseEnrichmentDocument.domain == domain,
                    CourseEnrichmentDocument.domain == "all",
                ),
            )
            .order_by(CourseEnrichmentDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, doc_id: UUID, organization_id: UUID
    ) -> CourseEnrichmentDocument | None:
        result = await self.session.execute(
            select(CourseEnrichmentDocument).where(
                CourseEnrichmentDocument.id == doc_id,
                CourseEnrichmentDocument.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, doc: CourseEnrichmentDocument) -> CourseEnrichmentDocument:
        self.session.add(doc)
        await self.session.flush()
        return doc
