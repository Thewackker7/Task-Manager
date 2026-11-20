from fastapi.testclient import TestClient

from app.main import create_app


def test_swagger_docs_are_available(client):
    assert client.get("/docs").status_code == 200


def test_openapi_schema_lists_all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]

    for path in (
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/users/me",
    ):
        assert path in paths


def test_unknown_route_returns_404_in_standard_error_shape(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_404"


def test_wrong_method_returns_405_in_standard_error_shape(client):
    response = client.delete("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "HTTP_405"


def test_unexpected_error_returns_generic_500_without_details():
    app = create_app()

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
    }
    assert "secret internal detail" not in response.text


def test_cors_allows_configured_origin(client):
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin(client):
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers
