"""FastAPI dependencies for auth, tenancy, and permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token, verify_csrf_token
from app.models.identity import User
from app.repositories.identity import SessionRepository, UserRepository
from app.services.auth_service import collect_permissions


@dataclass
class RequestContext:
    user: User
    organization_id: UUID
    session_id: UUID
    permissions: list[str]
    roles: list[str]
    correlation_id: str | None
    ip_address: str | None
    user_agent: str | None
    csrf_token: str


async def get_correlation_id(
    x_correlation_id: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_correlation_id


async def get_current_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
    csrf_token_cookie: Annotated[str | None, Cookie(alias="csrf_token")] = None,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedError("Authentication required")

    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org"])
    session_id = UUID(payload["sid"])

    sessions = SessionRepository(db)
    session = await sessions.get_session(session_id)
    if not session or session.revoked_at is not None:
        raise UnauthorizedError("Session revoked or not found")

    users = UserRepository(db)
    user = await users.get_by_id(user_id)
    if not user or user.organization_id != org_id or user.status != "active":
        raise UnauthorizedError("User not authorized")

    # CSRF for cookie-based mutating requests
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and access_token:
        if not verify_csrf_token(csrf_token_cookie or session.csrf_token, x_csrf_token):
            raise ForbiddenError("CSRF validation failed")

    roles, permissions = collect_permissions(user)
    return RequestContext(
        user=user,
        organization_id=org_id,
        session_id=session_id,
        permissions=permissions,
        roles=roles,
        correlation_id=x_correlation_id or request.headers.get("X-Request-ID"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        csrf_token=session.csrf_token,
    )


def require_permissions(*required: str):
    async def checker(
        ctx: Annotated[RequestContext, Depends(get_current_context)],
    ) -> RequestContext:
        missing = [p for p in required if p not in ctx.permissions]
        if missing and not ctx.user.is_super_admin:
            raise ForbiddenError(
                "Missing required permissions",
                details={"missing": missing},
            )
        return ctx

    return checker


CurrentContext = Annotated[RequestContext, Depends(get_current_context)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
