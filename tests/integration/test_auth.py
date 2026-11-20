from app.models.user import User
from tests.conftest import USER_EMAIL, USER_PASSWORD

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _login(client, username=USER_EMAIL, password=USER_PASSWORD):
    return client.post(LOGIN, data={"username": username, "password": password})


# ---------- registration ----------
def test_register_creates_user(client):
    response = client.post(
        REGISTER,
        json={"email": "bob@example.com", "password": "a-good-password", "full_name": "Bob"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "bob@example.com"
    assert body["full_name"] == "Bob"
    assert body["is_active"] is True
    assert body["id"] and body["created_at"]


def test_register_response_never_contains_password_data(client):
    response = client.post(
        REGISTER, json={"email": "bob@example.com", "password": "a-good-password"}
    )

    assert "password" not in response.text
    assert "argon2" not in response.text


def test_register_stores_only_a_hash_in_the_database(client, db_session):
    client.post(REGISTER, json={"email": "bob@example.com", "password": "a-good-password"})

    user = db_session.query(User).filter_by(email="bob@example.com").one()
    assert user.hashed_password != "a-good-password"
    assert user.hashed_password.startswith("$argon2id$")


def test_register_lowercases_email(client):
    response = client.post(
        REGISTER, json={"email": "Bob@Example.COM", "password": "a-good-password"}
    )

    assert response.json()["email"] == "bob@example.com"


def test_register_duplicate_email_returns_409(client, registered_user):
    response = client.post(REGISTER, json={"email": USER_EMAIL, "password": "another-password"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_duplicate_email_is_case_insensitive(client, registered_user):
    response = client.post(
        REGISTER, json={"email": USER_EMAIL.upper(), "password": "another-password"}
    )

    assert response.status_code == 409


def test_register_rejects_invalid_email(client):
    response = client.post(REGISTER, json={"email": "nope", "password": "a-good-password"})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "email"


def test_register_rejects_short_password_without_echoing_it(client):
    response = client.post(REGISTER, json={"email": "bob@example.com", "password": "short"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["details"][0]["field"] == "password"
    # The submitted value must never be sent back to the client.
    assert "input" not in error["details"][0]
    assert "short" not in response.text.replace("should have at least", "")


def test_register_rejects_missing_fields(client):
    assert client.post(REGISTER, json={}).status_code == 422


def test_register_rejects_unknown_fields(client):
    response = client.post(
        REGISTER,
        json={"email": "bob@example.com", "password": "a-good-password", "is_active": False},
    )

    assert response.status_code == 422


# ---------- login ----------
def test_login_returns_bearer_token(client, registered_user):
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == 30 * 60


def test_login_is_case_insensitive_for_email(client, registered_user):
    assert _login(client, username=USER_EMAIL.upper()).status_code == 200


def test_login_wrong_password_returns_401(client, registered_user):
    response = _login(client, password="wrong-password-here")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_unknown_email_gives_same_error_as_wrong_password(client, registered_user):
    wrong_password = _login(client, password="wrong-password-here")
    unknown_email = _login(client, username="ghost@example.com")

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_login_overlong_password_is_rejected_cheaply(client, registered_user):
    assert _login(client, password="x" * 5000).status_code == 401


def test_login_missing_fields_returns_422(client):
    assert client.post(LOGIN, data={}).status_code == 422


def test_inactive_user_cannot_log_in(client, db_session, registered_user):
    db_session.query(User).filter_by(email=USER_EMAIL).update({"is_active": False})
    db_session.commit()

    response = _login(client)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE_USER"


def test_inactive_user_with_wrong_password_learns_nothing(client, db_session, registered_user):
    db_session.query(User).filter_by(email=USER_EMAIL).update({"is_active": False})
    db_session.commit()

    assert _login(client, password="wrong-password-here").status_code == 401


def test_login_rejects_json_body(client, registered_user):
    # The OAuth2 password flow requires form data, not JSON.
    response = client.post(LOGIN, json={"username": USER_EMAIL, "password": USER_PASSWORD})

    assert response.status_code == 422


def test_register_handles_simultaneous_duplicate_registration(client, monkeypatch, registered_user):
    """If two requests pass the 'email free?' check at the same time, the database's unique
    index must still stop the second one, and the API must answer 409, not crash with 500."""
    from app.repositories.user import UserRepository

    monkeypatch.setattr(UserRepository, "get_by_email", lambda self, email: None)

    response = client.post(REGISTER, json={"email": USER_EMAIL, "password": "another-password"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    # The session must still be usable afterwards (the failed transaction was rolled back).
    assert client.get("/api/v1/health").status_code == 200
