"""Password hashing and JWT handling. Kept isolated so it is small, auditable and testable."""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

# Upper bound on password length. Hashing is deliberately expensive, so accepting
# megabyte-long passwords would let an attacker burn our CPU.
MAX_PASSWORD_LENGTH = 128

# Argon2id with the library's recommended defaults. Each hash includes its own random salt.
_hasher = PasswordHasher()

# A valid hash of a throwaway password. Used to make "unknown email" logins take as long
# as "wrong password" logins, so response time can't reveal which emails are registered.
DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except (VerificationError, InvalidHashError):
        return False


class TokenError(Exception):
    """The token is missing required data, expired, tampered with, or otherwise invalid."""


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT. `subject` identifies the user (we use the user id)."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "iat": now, "exp": expires, "type": "access"}
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str:
    """Verify a JWT and return its subject. Raises TokenError for any problem."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            # Always pin the allowed algorithm. Never trust the one named inside the token.
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("type") != "access":
        raise TokenError("Wrong token type")
    return payload["sub"]
