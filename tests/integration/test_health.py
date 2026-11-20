def test_health_returns_ok_when_database_is_up(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["environment"] == "testing"
    assert body["version"]


def test_health_returns_503_when_database_is_down(client_db_down):
    response = client_db_down.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


def test_health_does_not_leak_error_details(client_db_down):
    response = client_db_down.get("/api/v1/health")

    assert "connection refused" not in response.text
    assert "SELECT" not in response.text
