import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/app")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/app"
    assert settings.environment == "production"
    assert settings.cors_origins == ["https://app.example.com"]


def test_missing_database_url_prevents_startup(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("ENVIRONMENT", "staging-ish")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
