"""Authentication schemas."""

from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    """Login with username (preferred) — email is not required from the UI."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    organization_slug: str | None = None


class RegisterLearnerRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    organization_slug: str
    invite_token: str | None = None


class PasswordResetRequest(APIModel):
    email: EmailStr
    organization_slug: str


class PasswordResetConfirm(APIModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenUser(APIModel):
    id: UUID
    username: str
    first_name: str
    last_name: str
    organization_id: UUID
    organization_slug: str
    organization_name: str
    roles: list[str]
    permissions: list[str]
    is_super_admin: bool = False
    # Intentionally no email — UI must not display it after login.


class AuthSessionData(APIModel):
    user: TokenUser
    csrf_token: str
