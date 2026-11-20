import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_SECRET = "a-secret-key-that-is-at-least-32-characters-long"


def _base_env(monkeypatch, **overrides):
    values = {"DATABASE_URL": "sqlite://", "SECRET_KEY": VALID_SECRET} | overrides
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_settings_load_from_environment(monkeypatch):
    _base_env(
        monkeypatch,
        DATABASE_URL="postgresql+psycopg://u:p@db:5432/app",
        ENVIRONMENT="production",
        CORS_ORIGINS='["https://app.example.com"]',
    )

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/app"
    assert settings.environment == "production"
    assert settings.cors_origins == ["https://app.example.com"]
    assert settings.access_token_expire_minutes == 30


def test_missing_database_url_prevents_startup(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_missing_secret_key_prevents_startup(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_short_secret_key_is_rejected(monkeypatch):
    _base_env(monkeypatch, SECRET_KEY="too-short")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_placeholder_secret_is_rejected_in_production(monkeypatch):
    _base_env(
        monkeypatch,
        ENVIRONMENT="production",
        SECRET_KEY="change-me-" + "x" * 40,
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_environment_is_rejected(monkeypatch):
    _base_env(monkeypatch, ENVIRONMENT="staging-ish")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("minutes", ["0", "-5"])
def test_non_positive_token_expiry_is_rejected(monkeypatch, minutes):
    _base_env(monkeypatch, ACCESS_TOKEN_EXPIRE_MINUTES=minutes)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secret_key_is_hidden_in_repr(monkeypatch):
    _base_env(monkeypatch)

    assert VALID_SECRET not in repr(Settings(_env_file=None))
