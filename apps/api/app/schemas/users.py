"""User management schemas."""

from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel


class UserCreate(APIModel):
    username: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role_codes: list[str] = Field(default_factory=lambda: ["learner"])
    send_invite: bool = True
    # Optional internal email — auto-generated when omitted. Never shown in candidate UI.
    email: EmailStr | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip()
        if " " in cleaned:
            raise ValueError("Username cannot contain spaces")
        return cleaned


class UserUpdate(APIModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    status: str | None = None
    role_codes: list[str] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(APIModel):
    id: UUID
    username: str
    first_name: str
    last_name: str
    status: str
    organization_id: UUID
    roles: list[str] = Field(default_factory=list)
    is_super_admin: bool = False
    has_recoverable_password: bool = False


class PasswordRevealOut(APIModel):
    user_id: UUID
    username: str
    first_name: str
    last_name: str
    password: str
