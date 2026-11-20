def test_swagger_docs_are_available(client):
    assert client.get("/docs").status_code == 200


def test_openapi_schema_lists_health_route(client):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/health" in schema["paths"]


def test_unknown_route_returns_404(client):
    assert client.get("/api/v1/does-not-exist").status_code == 404


def test_cors_allows_configured_origin(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
