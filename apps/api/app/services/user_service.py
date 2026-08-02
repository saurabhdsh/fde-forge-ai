"""User management within an organization."""

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.security import decrypt_password, encrypt_password, hash_password
from app.models.identity import User, UserProfile, UserRole
from app.models.learner import LearnerProfile
from app.repositories.identity import RoleRepository, UserRepository
from app.schemas.users import PasswordRevealOut, UserCreate, UserOut, UserUpdate
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.audit = AuditService(session)

    def _to_out(self, user: User) -> UserOut:
        role_codes = [ur.role.code for ur in user.roles]
        return UserOut(
            id=user.id,
            username=(user.username or user.first_name),
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            organization_id=user.organization_id,
            roles=role_codes,
            is_super_admin=user.is_super_admin,
            has_recoverable_password=bool(user.password_encrypted),
        )

    def _set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        user.password_encrypted = encrypt_password(password)

    async def list_users(self, organization_id: UUID) -> list[UserOut]:
        users = await self.users.list_by_org(organization_id)
        return [self._to_out(u) for u in users]

    async def create_user(
        self,
        organization_id: UUID,
        payload: UserCreate,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserOut:
        existing = await self.users.get_by_username(organization_id, payload.username)
        if existing:
            raise ConflictError("Username already exists in the organization")

        password = payload.password or secrets.token_urlsafe(12)
        # Internal system email — never displayed in the candidate UI after login.
        internal_email = (
            str(payload.email).lower()
            if payload.email
            else f"{payload.username.lower()}@{organization_id.hex[:8]}.fdeforge.example.com"
        )
        if await self.users.get_by_email(organization_id, internal_email):
            raise ConflictError("Generated account identifier already exists; choose another username")

        user = User(
            organization_id=organization_id,
            email=internal_email,
            username=payload.username,
            password_hash=hash_password(password),
            password_encrypted=encrypt_password(password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            status="active",
            email_verified=False,
        )
        await self.users.create(user)

        profile = UserProfile(
            user_id=user.id,
            organization_id=organization_id,
            preferences={},
        )
        self.session.add(profile)

        for code in payload.role_codes:
            role = await self.roles.get_by_code(code, organization_id)
            if not role:
                raise ValidationAppError(f"Unknown role code: {code}")
            self.session.add(
                UserRole(user_id=user.id, role_id=role.id, organization_id=organization_id)
            )
            if code == "learner":
                self.session.add(
                    LearnerProfile(
                        user_id=user.id,
                        organization_id=organization_id,
                        onboarding_status="invited",
                    )
                )

        await self.session.flush()
        created = await self.users.get_by_id(user.id)
        assert created is not None

        await self.audit.log(
            action="user.create",
            entity_type="user",
            entity_id=user.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "username": user.username,
                "roles": payload.role_codes,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"temporary_password_issued": payload.password is None},
        )
        out = self._to_out(created)
        out._generated_password = password  # type: ignore[attr-defined]
        return out

    async def update_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        payload: UserUpdate,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserOut:
        user = await self.users.get_by_id(user_id)
        if not user or user.organization_id != organization_id:
            raise NotFoundError("User not found")

        before = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status,
            "roles": [ur.role.code for ur in user.roles],
        }

        if payload.first_name is not None:
            user.first_name = payload.first_name
        if payload.last_name is not None:
            user.last_name = payload.last_name
        if payload.username is not None:
            clash = await self.users.get_by_username(organization_id, payload.username)
            if clash and clash.id != user.id:
                raise ConflictError("Username already exists in the organization")
            user.username = payload.username
        if payload.status is not None:
            user.status = payload.status
        if payload.password is not None:
            self._set_password(user, payload.password)

        if payload.role_codes is not None:
            user.roles.clear()
            await self.session.flush()
            for code in payload.role_codes:
                role = await self.roles.get_by_code(code, organization_id)
                if not role:
                    raise ValidationAppError(f"Unknown role code: {code}")
                self.session.add(
                    UserRole(user_id=user.id, role_id=role.id, organization_id=organization_id)
                )

        await self.session.flush()
        updated = await self.users.get_by_id(user_id)
        assert updated is not None

        await self.audit.log(
            action="user.update",
            entity_type="user",
            entity_id=user.id,
            organization_id=organization_id,
            actor_id=actor_id,
            before=before,
            after={
                "first_name": updated.first_name,
                "last_name": updated.last_name,
                "status": updated.status,
                "roles": [ur.role.code for ur in updated.roles],
                "password_rotated": payload.password is not None,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if payload.role_codes is not None and before["roles"] != payload.role_codes:
            await self.audit.log(
                action="role.change",
                entity_type="user",
                entity_id=user.id,
                organization_id=organization_id,
                actor_id=actor_id,
                before={"roles": before["roles"]},
                after={"roles": payload.role_codes},
                correlation_id=correlation_id,
            )
        return self._to_out(updated)

    async def reveal_password(
        self,
        *,
        organization_id: UUID,
        target_user_id: UUID,
        actor: User,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PasswordRevealOut:
        """Admin-recoverable password reveal for self or org users."""
        can_manage = actor.is_super_admin or any(
            ur.role.code
            in {
                "platform_super_admin",
                "organization_admin",
                "academy_admin",
            }
            for ur in actor.roles
        )
        # Also allow via permission user.manage
        from app.services.auth_service import collect_permissions

        _, perms = collect_permissions(actor)
        if "user.manage" not in perms and not can_manage:
            raise ForbiddenError("Only admins can reveal account passwords")

        user = await self.users.get_by_id(target_user_id)
        if not user or user.organization_id != organization_id:
            raise NotFoundError("User not found")

        if not user.password_encrypted:
            raise NotFoundError(
                "No recoverable password stored for this user. Set a new password to enable reveal."
            )

        plaintext = decrypt_password(user.password_encrypted)
        if plaintext is None:
            raise ValidationAppError("Unable to decrypt stored password. Reset the password.")

        await self.audit.log(
            action="user.password_reveal",
            entity_type="user",
            entity_id=user.id,
            organization_id=organization_id,
            actor_id=actor.id,
            after={"username": user.username or user.first_name, "self": actor.id == user.id},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            # Never store the plaintext password in audit
        )

        return PasswordRevealOut(
            user_id=user.id,
            username=(user.username or user.first_name),
            first_name=user.first_name,
            last_name=user.last_name,
            password=plaintext,
        )

    async def delete_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user = await self.users.get_by_id(user_id)
        if not user or user.organization_id != organization_id:
            raise NotFoundError("User not found")
        if user.id == actor_id:
            raise ValidationAppError("You cannot delete your own account while signed in")

        username = user.username or user.first_name
        await self.audit.log(
            action="user.delete",
            entity_type="user",
            entity_id=user.id,
            organization_id=organization_id,
            actor_id=actor_id,
            before={"username": username, "roles": [ur.role.code for ur in user.roles]},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.session.delete(user)
        await self.session.flush()
