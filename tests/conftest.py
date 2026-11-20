"""Shared fixtures.

Environment variables are set before the app is imported, because Settings are
read at import time. Stage 1 uses an in-memory SQLite database (enough for
`SELECT 1`). From Stage 2, when we have real tables, tests switch to PostgreSQL.
"""

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')

from app.api.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client wired to a healthy in-memory database."""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    testing_session = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

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
