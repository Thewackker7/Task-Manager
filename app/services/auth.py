"""Business rules for registration and login. No HTTP code in here."""

from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.core.security import (
    DUMMY_HASH,
    MAX_PASSWORD_LENGTH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, data: UserCreate) -> User:
        email = normalize_email(data.email)

        if self.users.get_by_email(email):
            raise EmailAlreadyRegisteredError()

        try:
            return self.users.create(
                email=email,
                hashed_password=hash_password(data.password.get_secret_value()),
                full_name=data.full_name,
            )
        except IntegrityError:
            # Two requests registered the same email at the same moment: the pre-check above
            # passed for both, and the database's unique index stopped the second one.
            self.db.rollback()
            raise EmailAlreadyRegisteredError() from None

    def authenticate(self, email: str, password: str) -> User:
        if len(password) > MAX_PASSWORD_LENGTH:
            raise InvalidCredentialsError()

        user = self.users.get_by_email(normalize_email(email))

        if user is None:
            # Still do the expensive hash check so timing doesn't reveal that the email is unknown.
            verify_password(password, DUMMY_HASH)
            raise InvalidCredentialsError()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        # Only tell the caller the account is disabled after they proved they know the password.
        if not user.is_active:
            raise InactiveUserError()

        return user

    @staticmethod
    def create_token_for(user: User) -> tuple[str, int]:
        """Return (access_token, seconds_until_expiry)."""
        minutes = get_settings().access_token_expire_minutes
        token = create_access_token(str(user.id), expires_delta=timedelta(minutes=minutes))
        return token, minutes * 60
