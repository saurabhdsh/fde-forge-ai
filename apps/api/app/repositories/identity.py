"""Identity and RBAC repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity import (
    LoginAttempt,
    Organization,
    OrganizationSetting,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
    UserRole,
)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        return await self.session.get(Organization, org_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(self, org: Organization) -> Organization:
        self.session.add(org)
        await self.session.flush()
        return org

    async def get_settings(self, org_id: UUID) -> OrganizationSetting | None:
        result = await self.session.execute(
            select(OrganizationSetting).where(OrganizationSetting.organization_id == org_id)
        )
        return result.scalar_one_or_none()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission),
                selectinload(User.organization),
                selectinload(User.profile),
                selectinload(User.learner_profile),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, organization_id: UUID, username: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission),
                selectinload(User.organization),
            )
            .where(
                User.organization_id == organization_id,
                User.username.ilike(username.strip()),
            )
        )
        return result.scalar_one_or_none()

    async def find_by_username_any_org(self, username: str) -> list[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission),
                selectinload(User.organization),
            )
            .where(User.username.ilike(username.strip()))
        )
        return list(result.scalars().all())

    async def get_by_email(self, organization_id: UUID, email: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission),
                selectinload(User.organization),
            )
            .where(
                User.organization_id == organization_id,
                User.email == email.lower(),
            )
        )
        return result.scalar_one_or_none()

    async def find_by_email_any_org(self, email: str) -> list[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission),
                selectinload(User.organization),
            )
            .where(User.email == email.lower())
        )
        return list(result.scalars().all())

    async def list_by_org(
        self, organization_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[User]:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(User.organization_id == organization_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str, organization_id: UUID | None = None) -> Role | None:
        filters = [Role.code == code]
        if organization_id is None:
            filters.append(Role.organization_id.is_(None))
        else:
            filters.append(
                or_(Role.organization_id == organization_id, Role.organization_id.is_(None))
            )
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
            .where(and_(*filters))
            .order_by(Role.organization_id.desc().nulls_last())
        )
        return result.scalars().first()

    async def list_permissions(self) -> list[Permission]:
        result = await self.session.execute(select(Permission).order_by(Permission.code))
        return list(result.scalars().all())

    async def ensure_permission(self, permission: Permission) -> Permission:
        existing = await self.session.execute(
            select(Permission).where(Permission.code == permission.code)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found
        self.session.add(permission)
        await self.session.flush()
        return permission


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self, entity: Session) -> Session:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get_session(self, session_id: UUID) -> Session | None:
        return await self.session.get(Session, session_id)

    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: UUID) -> None:
        entity = await self.get_session(session_id)
        if entity and entity.revoked_at is None:
            entity.revoked_at = datetime.now(UTC)
            await self.session.flush()


class LoginAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, attempt: LoginAttempt) -> LoginAttempt:
        self.session.add(attempt)
        await self.session.flush()
        return attempt
