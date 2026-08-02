"""Organization schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class OrganizationCreate(APIModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    branding: dict = Field(default_factory=dict)


class OrganizationUpdate(APIModel):
    name: str | None = None
    branding: dict | None = None
    status: str | None = None


class OrganizationSettingsUpdate(APIModel):
    readiness_weights: dict | None = None
    content_policies: dict | None = None
    security_settings: dict | None = None
    ai_limits: dict | None = None
    certification_settings: dict | None = None
    feature_flags: dict | None = None


class OrganizationOut(APIModel):
    id: UUID
    name: str
    slug: str
    status: str
    branding: dict
    is_demo: bool


class OrganizationSettingsOut(APIModel):
    organization_id: UUID
    readiness_weights: dict
    content_policies: dict
    security_settings: dict
    ai_limits: dict
    certification_settings: dict
    feature_flags: dict
