"""Application settings, loaded from environment variables (and an optional .env file).

Pydantic validates everything at startup: if a required value is missing or has the
wrong type, the app refuses to start instead of failing later in a confusing way.
"""

from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    """Build Settings once and reuse it (cached)."""
    return Settings()
