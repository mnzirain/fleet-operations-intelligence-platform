from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "Fleet Operations Intelligence Platform"
    assert data["status"] == "running"
    assert "environment" in data


def test_health_endpoint():
    """Verify that the application health endpoint works."""
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
