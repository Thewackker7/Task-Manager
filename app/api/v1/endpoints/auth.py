from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, auth_service: AuthServiceDep):
    """Create a new account."""
    return auth_service.register(data)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], auth_service: AuthServiceDep):
    """Exchange email + password for an access token.

    Follows the OAuth2 "password" convention: form-encoded body with fields `username`
    and `password`. Our username *is* the email address.
    """
    user = auth_service.authenticate(form.username, form.password)
    access_token, expires_in = auth_service.create_token_for(user)
    return Token(access_token=access_token, expires_in=expires_in)
