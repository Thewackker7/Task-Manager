"""Tests that the database itself enforces our rules, even if application code has a bug."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def _user(email: str) -> User:
    return User(email=email, hashed_password="x")


def test_defaults_are_filled_in(db_session):
    user = _user("a@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.full_name is None


def test_duplicate_email_is_rejected_by_database(db_session):
    db_session.add(_user("a@example.com"))
    db_session.commit()
    db_session.add(_user("a@example.com"))

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_uppercase_email_is_rejected_by_database(db_session):
    db_session.add(_user("A@Example.com"))

    with pytest.raises(IntegrityError):
        db_session.commit()
