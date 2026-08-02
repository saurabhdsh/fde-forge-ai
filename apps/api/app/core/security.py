"""Password hashing, JWT tokens, CSRF helpers, and recoverable password vault."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


@lru_cache
def _fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY for admin-recoverable password storage."""
    settings = get_settings()
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_password(password: str) -> str:
    return _fernet().encrypt(password.encode("utf-8")).decode("utf-8")


def decrypt_password(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    return password_hasher.check_needs_rehash(password_hash)


def create_access_token(
    *,
    subject: UUID,
    organization_id: UUID,
    permissions: list[str],
    session_id: UUID,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "org": str(organization_id),
        "sid": str(session_id),
        "perms": permissions,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(expected: str | None, provided: str | None) -> bool:
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)
