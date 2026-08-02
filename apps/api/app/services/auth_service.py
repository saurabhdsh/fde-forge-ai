"""Authentication and session management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    generate_csrf_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.models.identity import LoginAttempt, RefreshToken, Session, User
from app.repositories.identity import (
    LoginAttemptRepository,
    OrganizationRepository,
    SessionRepository,
    UserRepository,
)
from app.schemas.auth import AuthSessionData, TokenUser
from app.services.audit_service import AuditService


def collect_permissions(user: User) -> tuple[list[str], list[str]]:
    role_codes: list[str] = []
    permissions: set[str] = set()
    for ur in user.roles:
        role_codes.append(ur.role.code)
        for rp in ur.role.permissions:
            permissions.add(rp.permission.code)
    if user.is_super_admin:
        permissions.update(
            [
                "organization.manage",
                "user.create",
                "user.view",
                "user.manage",
                "role.manage",
                "learner.view",
                "learner.manage",
                "audit.read",
                "ai_configuration.manage",
                "analytics.executive",
            ]
        )
    return sorted(set(role_codes)), sorted(permissions)


def display_username(user: User) -> str:
    return (user.username or user.first_name or "user").strip()


def to_token_user(user: User, roles: list[str], permissions: list[str]) -> TokenUser:
    return TokenUser(
        id=user.id,
        username=display_username(user),
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        organization_slug=user.organization.slug,
        organization_name=user.organization.name,
        roles=roles,
        permissions=permissions,
        is_super_admin=user.is_super_admin,
    )


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.orgs = OrganizationRepository(session)
        self.sessions = SessionRepository(session)
        self.attempts = LoginAttemptRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def login(
        self,
        *,
        username: str,
        password: str,
        organization_slug: str | None,
        ip_address: str | None,
        user_agent: str | None,
        correlation_id: str | None,
    ) -> tuple[AuthSessionData, str, str]:
        login_id = username.strip()
        user: User | None = None

        if organization_slug:
            org = await self.orgs.get_by_slug(organization_slug)
            if not org:
                await self._record_attempt(
                    login_id, None, False, ip_address, user_agent, "org_not_found"
                )
                raise UnauthorizedError("Invalid credentials")
            user = await self.users.get_by_username(org.id, login_id)
            if not user and "@" in login_id:
                user = await self.users.get_by_email(org.id, login_id.lower())
        else:
            matches = await self.users.find_by_username_any_org(login_id)
            if not matches and "@" in login_id:
                matches = await self.users.find_by_email_any_org(login_id.lower())
            if len(matches) == 1:
                user = matches[0]
            elif len(matches) > 1:
                raise ValidationAppError(
                    "Multiple organizations found for this username. Provide organization_slug.",
                    details={"required_field": "organization_slug"},
                )

        if not user:
            await self._record_attempt(
                login_id, None, False, ip_address, user_agent, "user_not_found"
            )
            raise UnauthorizedError("Invalid credentials")

        if user.locked_until and user.locked_until > datetime.now(UTC):
            await self._record_attempt(
                login_id, user.organization_id, False, ip_address, user_agent, "locked"
            )
            raise ForbiddenError("Account is temporarily locked due to failed login attempts")

        if user.status != "active":
            raise ForbiddenError("Account is not active")

        if not verify_password(user.password_hash, password):
            user.failed_login_count += 1
            if user.failed_login_count >= self.settings.login_max_attempts:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=self.settings.login_lockout_minutes
                )
            await self._record_attempt(
                login_id, user.organization_id, False, ip_address, user_agent, "bad_password"
            )
            await self.audit.log(
                action="login.failed",
                entity_type="user",
                entity_id=user.id,
                organization_id=user.organization_id,
                actor_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
            )
            raise UnauthorizedError("Invalid credentials")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

        roles, permissions = collect_permissions(user)
        csrf = generate_csrf_token()
        session = Session(
            user_id=user.id,
            organization_id=user.organization_id,
            csrf_token=csrf,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(UTC)
            + timedelta(days=self.settings.refresh_token_expire_days),
        )
        await self.sessions.create_session(session)

        refresh_value = create_refresh_token_value()
        refresh = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            organization_id=user.organization_id,
            token_hash=hash_token(refresh_value),
            expires_at=session.expires_at,
        )
        await self.sessions.create_refresh_token(refresh)

        access = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            permissions=permissions,
            session_id=session.id,
        )

        await self._record_attempt(
            login_id, user.organization_id, True, ip_address, user_agent, None
        )
        await self.audit.log(
            action="login.success",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            after={"username": display_username(user)},
        )

        data = AuthSessionData(
            user=to_token_user(user, roles, permissions),
            csrf_token=csrf,
        )
        return data, access, refresh_value

    async def logout(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        ip_address: str | None,
        user_agent: str | None,
        correlation_id: str | None,
    ) -> None:
        await self.sessions.revoke_session(session_id)
        await self.audit.log(
            action="logout",
            entity_type="session",
            entity_id=session_id,
            organization_id=organization_id,
            actor_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )

    async def refresh(
        self,
        *,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        correlation_id: str | None,
    ) -> tuple[AuthSessionData, str, str]:
        token = await self.sessions.get_refresh_by_hash(hash_token(refresh_token))
        if not token or token.revoked_at or token.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Invalid refresh token")

        session = await self.sessions.get_session(token.session_id)
        if not session or session.revoked_at or session.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Session expired")

        user = await self.users.get_by_id(token.user_id)
        if not user or user.status != "active":
            raise UnauthorizedError("User inactive")

        # Rotate refresh token
        token.revoked_at = datetime.now(UTC)
        new_refresh_value = create_refresh_token_value()
        new_refresh = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            organization_id=user.organization_id,
            token_hash=hash_token(new_refresh_value),
            expires_at=session.expires_at,
        )
        await self.sessions.create_refresh_token(new_refresh)
        token.replaced_by_token_id = new_refresh.id

        roles, permissions = collect_permissions(user)
        access = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            permissions=permissions,
            session_id=session.id,
        )
        session.last_seen_at = datetime.now(UTC)

        await self.audit.log(
            action="token.refresh",
            entity_type="session",
            entity_id=session.id,
            organization_id=user.organization_id,
            actor_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )

        data = AuthSessionData(
            user=to_token_user(user, roles, permissions),
            csrf_token=session.csrf_token,
        )
        return data, access, new_refresh_value

    async def _record_attempt(
        self,
        email: str,
        organization_id: UUID | None,
        success: bool,
        ip_address: str | None,
        user_agent: str | None,
        failure_reason: str | None,
    ) -> None:
        await self.attempts.add(
            LoginAttempt(
                email=email,
                organization_id=organization_id,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=failure_reason,
            )
        )
