import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.core.security import MAX_PASSWORD_LENGTH

MIN_PASSWORD_LENGTH = 8


class UserCreate(BaseModel):
    """What a client may send to register. Unknown fields are rejected, so nobody can
    sneak in extra data such as `is_active` or `id`."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    # SecretStr hides the value in logs and tracebacks (prints as '**********').
    password: SecretStr = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UserRead(BaseModel):
    """What the API returns about a user. Note: no password hash, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
