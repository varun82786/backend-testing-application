"""Tests for the health check and documentation endpoints."""


def test_health_check(client):
    """GET /health returns 200 with status=healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_check_contains_version(client):
    """Health check response contains a semantic version string."""
    response = client.get("/health")
    data = response.json()
    version = data["version"]
    # Expect a semver-like format: major.minor.patch
    parts = version.split(".")
    assert len(parts) >= 2, f"Expected semver format, got: {version}"


def test_docs_available(client):
    """Swagger UI docs are served at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_available(client):
    """ReDoc docs are served at /redoc."""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema(client):
    """OpenAPI JSON schema is valid and contains expected paths."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Order Management System"


def test_openapi_contains_auth_paths(client):
    """OpenAPI schema includes authentication endpoints."""
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/me" in paths


def test_openapi_contains_business_paths(client):
    """OpenAPI schema includes core business entity endpoints."""
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    assert "/api/v1/customers/" in paths
    assert "/api/v1/products/" in paths
    assert "/api/v1/orders/" in paths
    assert "/api/v1/payments/" in paths
    assert "/api/v1/inventory/" in paths
    assert "/api/v1/shipments/" in paths
    assert "/api/v1/coupons/" in paths
