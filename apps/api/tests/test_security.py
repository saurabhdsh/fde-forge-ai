"""Unit tests for security helpers."""

from app.core.security import hash_password, hash_token, verify_password


def test_password_hash_and_verify() -> None:
    hashed = hash_password("SecurePass123!")
    assert verify_password(hashed, "SecurePass123!")
    assert not verify_password(hashed, "wrong")


def test_token_hash_stable() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abcd")
