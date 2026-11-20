"""Shared fixtures.

Tests run against a real PostgreSQL database (never SQLite: it behaves differently).
- A separate database whose name ends in "_test" is used, so dev data is never touched.
- The schema is built by running the real Alembic migrations, which also tests them.
- Every test runs inside a transaction that is rolled back afterwards, so tests are isolated.
"""

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic.config import Config
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://taskuser:taskpass@localhost:5432/taskdb_test"


def _resolve_test_database_url() -> str:
    # Priority: real environment variable > .env file > default matching docker-compose.
    return (
        os.environ.get("TEST_DATABASE_URL")
        or dotenv_values(ROOT / ".env").get("TEST_DATABASE_URL")
        or DEFAULT_TEST_DATABASE_URL
    )


TEST_DATABASE_URL = _resolve_test_database_url()
assert make_url(TEST_DATABASE_URL).database.endswith("_test"), (
    "Refusing to run tests: the test database name must end with '_test' "
    "so a real database is never modified by accident."
)

# Force the app to use test settings. This must happen BEFORE the app is imported,
# because settings are read at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-definitely-long-enough-123"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

from app.api.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402


def _ensure_database_exists(url: str) -> None:
    """Create the test database if it doesn't exist yet."""
    parsed = make_url(url)
    admin_engine = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": parsed.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    try:
        _ensure_database_exists(TEST_DATABASE_URL)
    except OperationalError as exc:
        pytest.exit(
            "Cannot connect to PostgreSQL for tests. Is it running? "
            "(try: docker compose up -d db)\n" + str(exc),
            returncode=2,
        )

    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.downgrade(alembic_cfg, "base")  # start from a clean slate
    command.upgrade(alembic_cfg, "head")

    test_engine = create_engine(TEST_DATABASE_URL)
    yield test_engine
    test_engine.dispose()
    command.downgrade(alembic_cfg, "base")


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """A session inside an outer transaction that is rolled back after the test.

    "create_savepoint" means that when the app code calls commit() or rollback(), it only
    affects a savepoint, so the outer rollback still wipes everything.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client whose requests use the isolated test session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_db_down() -> Generator[TestClient, None, None]:
    """Test client whose database always fails, to test the error path."""

    def override_get_db() -> Generator[MagicMock, None, None]:
        broken = MagicMock()
        broken.execute.side_effect = OperationalError(
            "SELECT 1", {}, Exception("connection refused")
        )
        yield broken

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------- helpers for tests that need a logged-in user ----------

USER_EMAIL = "alice@example.com"
USER_PASSWORD = "correct-horse-battery"


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": USER_EMAIL, "password": USER_PASSWORD, "full_name": "Alice"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(client: TestClient, registered_user: dict) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": USER_EMAIL, "password": USER_PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
