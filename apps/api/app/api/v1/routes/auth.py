"""Authentication routes."""

from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentContext, DbSession
from app.api.responses import success
from app.core.config import get_settings
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService, collect_permissions, to_token_user

router = APIRouter()


def _set_auth_cookies(response: Response, access: str, refresh: str, csrf: str) -> None:
    settings = get_settings()
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        "access_token",
        access,
        max_age=settings.access_token_expire_minutes * 60,
        **common,
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        **common,
    )
    response.set_cookie(
        "csrf_token",
        csrf,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> dict:
    service = AuthService(db)
    data, access, refresh = await service.login(
        username=payload.username,
        password=payload.password,
        organization_slug=payload.organization_slug,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    _set_auth_cookies(response, access, refresh, data.csrf_token)
    return success(data, correlation_id=request.headers.get("X-Correlation-ID"))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: DbSession,
    ctx: CurrentContext,
) -> dict:
    service = AuthService(db)
    await service.logout(
        session_id=ctx.session_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
        correlation_id=ctx.correlation_id,
    )
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return success({"message": "Logged out"}, correlation_id=ctx.correlation_id)


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
) -> dict:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Refresh token missing")
    service = AuthService(db)
    data, access, new_refresh = await service.refresh(
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    _set_auth_cookies(response, access, new_refresh, data.csrf_token)
    return success(data, correlation_id=request.headers.get("X-Correlation-ID"))


@router.get("/me")
async def me(ctx: CurrentContext) -> dict:
    from app.schemas.auth import AuthSessionData

    roles, permissions = collect_permissions(ctx.user)
    data = AuthSessionData(
        user=to_token_user(ctx.user, roles, permissions),
        csrf_token=ctx.csrf_token,
    )
    return success(data, correlation_id=ctx.correlation_id)
