from unittest.mock import Mock

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from tests.constants import TEST_API_KEY

client = TestClient(app)


def test_vehicles_endpoint_rejects_missing_api_key():
    response = client.get("/vehicles/")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}


def test_vehicles_endpoint_rejects_incorrect_api_key():
    response = client.get(
        "/vehicles/",
        headers={"X-API-Key": "incorrect-test-api-key"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}


def test_fleet_events_endpoint_rejects_missing_api_key():
    response = client.post("/fleet-events/", json={})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}


def test_api_rejects_requests_when_server_api_key_is_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "fleet_api_key", None)

    response = client.get(
        "/vehicles/",
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "API authentication is not configured."}


def test_root_endpoint_is_public():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_liveness_endpoint_is_public():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_endpoint_is_public(monkeypatch):
    mock_db = Mock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "connected",
        }

        mock_db.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()
