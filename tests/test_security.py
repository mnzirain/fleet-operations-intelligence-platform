from unittest.mock import Mock

import pytest
from app.core.config import Settings, settings
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.constants import TEST_API_KEY

client = TestClient(app)

VEHICLE_ID = "6fe69179-961c-49fa-be52-6975ab55c991"


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


def test_vehicle_delete_rejects_missing_api_key():
    response = client.delete(f"/vehicles/{VEHICLE_ID}")

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
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: mock_db)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }

    mock_db.execute.assert_called_once()


def test_blank_api_key_setting_is_treated_as_unset():
    blank = Settings(database_url="postgresql://x", fleet_api_key="   ")

    assert blank.fleet_api_key is None


def test_short_api_key_setting_is_rejected():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://x", fleet_api_key="short")


def test_valid_api_key_setting_is_accepted_and_trimmed():
    trimmed = Settings(
        database_url="postgresql://x",
        fleet_api_key="  " + "k" * 20 + " ",
    )

    assert trimmed.fleet_api_key.get_secret_value() == "k" * 20
