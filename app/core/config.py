"""Application settings, loaded from environment variables (and an optional .env file).

Pydantic validates everything at startup: if a required value is missing or has the
wrong type, the app refuses to start instead of failing later in a confusing way.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Task Manager API"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    # Required: no default on purpose. Example: postgresql+psycopg://user:pass@host:5432/db
    database_url: str

    # Origins (scheme + host + port) of browser apps allowed to call this API.
    # In .env this is written as JSON, e.g. ["http://localhost:3000"]
    cors_origins: list[str] = []

    # --- Authentication ---
    # Required. Signs JWTs: anyone who knows it can forge tokens for any user.
    # Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 30

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_long(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def expiry_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        return value

    @model_validator(mode="after")
    def no_placeholder_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.secret_key.get_secret_value().startswith(
            "change-me"
        ):
            raise ValueError("SECRET_KEY still has the placeholder value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Build Settings once and reuse it (cached)."""
    return Settings()
