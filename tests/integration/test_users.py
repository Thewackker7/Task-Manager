from datetime import timedelta

from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import USER_EMAIL

ME = "/api/v1/users/me"


def test_me_returns_current_user(client, registered_user, auth_headers):
    response = client.get(ME, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == registered_user["id"]
    assert body["email"] == USER_EMAIL
    assert "hashed_password" not in body


def test_me_without_token_returns_401(client):
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_garbage_token_returns_401(client):
    response = client.get(ME, headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_me_with_wrong_scheme_returns_401(client, auth_headers):
    token = auth_headers["Authorization"].split()[1]

    assert client.get(ME, headers={"Authorization": f"Basic {token}"}).status_code == 401


def test_me_with_expired_token_returns_401(client, registered_user):
    expired = create_access_token(registered_user["id"], expires_delta=timedelta(seconds=-1))

    response = client.get(ME, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_me_with_token_whose_subject_is_not_a_uuid_returns_401(client):
    token = create_access_token("not-a-uuid")

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_me_with_token_for_nonexistent_user_returns_401(client):
    token = create_access_token("00000000-0000-0000-0000-000000000000")

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_me_for_deactivated_user_returns_403(client, db_session, auth_headers):
    db_session.query(User).filter_by(email=USER_EMAIL).update({"is_active": False})
    db_session.commit()

    response = client.get(ME, headers=auth_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE_USER"
