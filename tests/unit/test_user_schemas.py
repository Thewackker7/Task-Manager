import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


def test_valid_user_is_accepted():
    user = UserCreate(email="a@example.com", password="long-enough-pw")

    assert user.email == "a@example.com"
    assert user.full_name is None


def test_email_is_lowercased():
    assert UserCreate(email="Alice@Example.COM", password="long-enough-pw").email == (
        "alice@example.com"
    )


def test_password_is_hidden_in_repr():
    assert "long-enough-pw" not in repr(
        UserCreate(email="a@example.com", password="long-enough-pw")
    )


@pytest.mark.parametrize("bad_email", ["not-an-email", "a@", "@example.com", ""])
def test_invalid_email_is_rejected(bad_email):
    with pytest.raises(ValidationError):
        UserCreate(email=bad_email, password="long-enough-pw")


def test_short_password_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="short")


def test_overlong_password_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="x" * 129)


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="long-enough-pw", is_active=False)


def test_blank_full_name_becomes_none():
    assert (
        UserCreate(email="a@example.com", password="long-enough-pw", full_name="   ").full_name
        is None
    )
