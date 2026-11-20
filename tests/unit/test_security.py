from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------- passwords ----------
def test_hash_is_not_the_plain_password():
    hashed = hash_password("my-password-123")

    assert hashed != "my-password-123"
    assert hashed.startswith("$argon2id$")


def test_correct_password_verifies():
    assert verify_password("my-password-123", hash_password("my-password-123")) is True


def test_wrong_password_does_not_verify():
    assert verify_password("wrong-password", hash_password("my-password-123")) is False


def test_same_password_gets_different_hashes_because_of_salt():
    assert hash_password("my-password-123") != hash_password("my-password-123")


def test_garbage_hash_does_not_crash_verification():
    assert verify_password("anything", "not-a-real-hash") is False


# ---------- tokens ----------
def test_token_round_trip_returns_subject():
    token = create_access_token("user-123")

    assert decode_access_token(token) == "user-123"


def test_expired_token_is_rejected():
    token = create_access_token("user-123", expires_delta=timedelta(seconds=-1))

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token("user-123")
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}xx"

    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode(
        {
            "sub": "user-123",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "some-other-secret-key-that-is-long-enough-12345",
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_unsigned_token_with_alg_none_is_rejected():
    forged = jwt.encode(
        {
            "sub": "user-123",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        key=None,
        algorithm="none",
    )

    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_token_without_expiry_is_rejected():
    secret = get_settings().secret_key.get_secret_value()
    token = jwt.encode({"sub": "user-123", "iat": datetime.now(UTC)}, secret, algorithm="HS256")

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_token_of_wrong_type_is_rejected():
    secret = get_settings().secret_key.get_secret_value()
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "user-123", "iat": now, "exp": now + timedelta(hours=1), "type": "refresh"},
        secret,
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_random_string_is_rejected():
    with pytest.raises(TokenError):
        decode_access_token("not.a.token")
