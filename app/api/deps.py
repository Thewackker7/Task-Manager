"""Shared FastAPI dependencies. Routes declare what they need; FastAPI supplies it."""

import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InactiveUserError, NotAuthenticatedError
from app.core.security import TokenError, decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService


def get_db() -> Generator[Session, None, None]:
    """Give each request its own database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Reusable type alias: `db: DbSession` in a route means "inject a session here".
DbSession = Annotated[Session, Depends(get_db)]

# Reads the "Authorization: Bearer <token>" header. tokenUrl powers the "Authorize" button in
# /docs. auto_error=False lets us raise our own error in our own JSON format.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    """Turn a bearer token into the logged-in user, or fail with 401/403."""
    if token is None:
        raise NotAuthenticatedError()

    try:
        user_id = uuid.UUID(decode_access_token(token))
    except (TokenError, ValueError):
        raise NotAuthenticatedError("Invalid or expired token.") from None

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        # Valid token, but the user no longer exists.
        raise NotAuthenticatedError("Invalid or expired token.")
    if not user.is_active:
        raise InactiveUserError()
    return user


# Add `user: CurrentUser` to any route to make it require login.
CurrentUser = Annotated[User, Depends(get_current_user)]
