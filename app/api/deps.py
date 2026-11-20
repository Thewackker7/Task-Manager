"""Shared FastAPI dependencies. Routes declare what they need; FastAPI supplies it."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Give each request its own database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Reusable type alias: `db: DbSession` in a route means "inject a session here".
DbSession = Annotated[Session, Depends(get_db)]
