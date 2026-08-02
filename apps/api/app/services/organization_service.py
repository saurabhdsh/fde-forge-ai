"""Organization management service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.identity import Organization, OrganizationSetting
from app.repositories.identity import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationSettingsOut,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
)
from app.services.audit_service import AuditService


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = OrganizationRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        payload: OrganizationCreate,
        *,
        actor_id: UUID | None,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OrganizationOut:
        existing = await self.repo.get_by_slug(payload.slug)
        if existing:
            raise ConflictError("Organization slug already exists")

        org = Organization(
            name=payload.name,
            slug=payload.slug,
            branding=payload.branding or {},
            status="active",
        )
        await self.repo.create(org)
        settings = OrganizationSetting(
            organization_id=org.id,
            readiness_weights={
                "technical": 0.25,
                "domain": 0.20,
                "project": 0.20,
                "consulting": 0.10,
                "communication": 0.10,
                "architecture": 0.10,
                "security_compliance": 0.05,
            },
            content_policies={
                "ai_requires_human_review": True,
                "healthcare_disclaimer_required": True,
                "life_sciences_sme_required": True,
            },
            security_settings={},
            ai_limits={"daily_budget_usd": 50},
            certification_settings={},
            feature_flags={"phase1_onboarding": True},
        )
        self.repo.session.add(settings)
        await self.repo.session.flush()

        await self.audit.log(
            action="organization.create",
            entity_type="organization",
            entity_id=org.id,
            organization_id=org.id,
            actor_id=actor_id,
            after={"name": org.name, "slug": org.slug},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return OrganizationOut.model_validate(org)

    async def get(self, org_id: UUID) -> OrganizationOut:
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization not found")
        return OrganizationOut.model_validate(org)

    async def update(
        self,
        org_id: UUID,
        payload: OrganizationUpdate,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OrganizationOut:
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization not found")
        before = {"name": org.name, "status": org.status, "branding": org.branding}
        if payload.name is not None:
            org.name = payload.name
        if payload.branding is not None:
            org.branding = payload.branding
        if payload.status is not None:
            org.status = payload.status
        await self.repo.session.flush()
        await self.audit.log(
            action="organization.update",
            entity_type="organization",
            entity_id=org.id,
            organization_id=org.id,
            actor_id=actor_id,
            before=before,
            after={"name": org.name, "status": org.status, "branding": org.branding},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return OrganizationOut.model_validate(org)

    async def get_settings(self, org_id: UUID) -> OrganizationSettingsOut:
        settings = await self.repo.get_settings(org_id)
        if not settings:
            raise NotFoundError("Organization settings not found")
        return OrganizationSettingsOut(
            organization_id=settings.organization_id,
            readiness_weights=settings.readiness_weights,
            content_policies=settings.content_policies,
            security_settings=settings.security_settings,
            ai_limits=settings.ai_limits,
            certification_settings=settings.certification_settings,
            feature_flags=settings.feature_flags,
        )

    async def update_settings(
        self,
        org_id: UUID,
        payload: OrganizationSettingsUpdate,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> OrganizationSettingsOut:
        settings = await self.repo.get_settings(org_id)
        if not settings:
            raise NotFoundError("Organization settings not found")
        before = {
            "ai_limits": settings.ai_limits,
            "feature_flags": settings.feature_flags,
        }
        for field in (
            "readiness_weights",
            "content_policies",
            "security_settings",
            "ai_limits",
            "certification_settings",
            "feature_flags",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(settings, field, value)
        await self.repo.session.flush()
        await self.audit.log(
            action="organization.settings_update",
            entity_type="organization_settings",
            entity_id=settings.id,
            organization_id=org_id,
            actor_id=actor_id,
            before=before,
            after={
                "ai_limits": settings.ai_limits,
                "feature_flags": settings.feature_flags,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self.get_settings(org_id)
