import pytest
from fastapi.testclient import TestClient


def test_home_page(client: TestClient):
    """Verify default root GET / returns plain text welcome to sitesense."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "welcome to sitesense"


def test_swagger_documentation_accessible(client: TestClient):
    """Verify Swagger UI is exposed and loads correctly."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower() or "SiteSense" in response.text


def test_openapi_schema(client: TestClient):
    """Verify OpenAPI schema is available at /api/v1/openapi.json with valid structure."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "SiteSense - Multimodal Operations Intelligence Platform"
    assert data["info"]["version"] == "1.0.0"


def test_health_check_and_database_connection(client: TestClient):
    """Verify /api/v1/health returns 200, is healthy, and confirms DB connection."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] in ("development", "test")
    assert data["database"]["connected"] is True
    assert data["database"]["latency_ms"] >= 0.0
    assert "uptime_seconds" in data


def test_health_probes(client: TestClient):
    """Verify /live and /ready endpoints for orchestration."""
    live_res = client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/api/v1/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_platform_modules_readiness(client: TestClient):
    """Verify /api/v1/modules reports readiness across all 8 modules (M1-M8)."""
    response = client.get("/api/v1/modules")
    assert response.status_code == 200
    data = response.json()
    assert data["total_modules"] == 8
    module_codes = [m["code"] for m in data["modules"]]
    assert module_codes == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]


def test_standardized_error_format_on_404(client: TestClient):
    """Verify 404 responses conform to the uniform error shape:
    { "error": { "code": ..., "message": ..., "detail": ... } }
    """
    response = client.get("/api/v1/non_existent_endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
    assert "detail" in data["error"]


def test_request_headers_correlation_and_timing(client: TestClient):
    """Verify response contains X-Request-ID and X-Process-Time-Ms headers."""
    response = client.get("/api/v1/health")
    assert "x-request-id" in response.headers
    assert "x-process-time-ms" in response.headers
    # Custom correlation ID propagation
    custom_id = "test-custom-trace-id-12345"
    res_custom = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers["x-request-id"] == custom_id
