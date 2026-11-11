from unittest.mock import Mock

import pytest
from app.core.config import Settings, settings
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.constants import TEST_API_KEY
from tests.webhook_helpers import make_signed_webhook_request

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


def test_fleet_events_endpoint_rejects_missing_webhook_headers():
    response = client.post("/fleet-events/", json={})

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing webhook authentication headers."}


def test_fleet_events_endpoint_does_not_accept_api_key_instead_of_signature():
    response = client.post(
        "/fleet-events/",
        json={},
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing webhook authentication headers."}


def test_webhook_rejects_non_numeric_timestamp():
    body, headers = make_signed_webhook_request({"probe": "test"})
    headers["X-Webhook-Timestamp"] = "not-a-timestamp"

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook timestamp."}


@pytest.mark.parametrize(
    "timestamp",
    [
        " 1234567890",
        "1234567890 ",
        "+1234567890",
        "-1234567890",
    ],
)
def test_webhook_rejects_timestamp_with_invalid_characters(timestamp):
    body, headers = make_signed_webhook_request({"probe": "test"})
    headers["X-Webhook-Timestamp"] = timestamp

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook timestamp."}


def test_webhook_rejects_expired_timestamp():
    body, headers = make_signed_webhook_request(
        {"probe": "test"},
        timestamp=1,
    )

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Webhook timestamp is outside the permitted time window."
    }


def test_webhook_rejects_tampered_request_body():
    body, headers = make_signed_webhook_request(
        {"probe": "original"},
    )
    tampered_body = body.replace(b"original", b"tampered")

    response = client.post(
        "/fleet-events/",
        content=tampered_body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook signature."}


def test_webhook_rejects_incorrect_signature():
    body, headers = make_signed_webhook_request({"probe": "test"})

    signature = headers["X-Webhook-Signature"]
    replacement = "0" if signature[-1] != "0" else "1"
    headers["X-Webhook-Signature"] = signature[:-1] + replacement

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook signature."}


@pytest.mark.parametrize(
    "signature",
    [
        "sha256=" + "g" * 64,
        "sha256=" + "a" * 32 + " " + "a" * 31,
        "sha256=" + "a" * 63,
    ],
)
def test_webhook_rejects_malformed_signature_format(signature):
    body, headers = make_signed_webhook_request({"probe": "test"})
    headers["X-Webhook-Signature"] = signature

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook signature format."}


@pytest.mark.parametrize("uppercase_signature", [False, True])
def test_webhook_accepts_correctly_signed_request(uppercase_signature):
    body, headers = make_signed_webhook_request({"probe": "test"})

    if uppercase_signature:
        prefix, digest = headers["X-Webhook-Signature"].split("=", 1)
        headers["X-Webhook-Signature"] = f"{prefix}={digest.upper()}"

    response = client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )

    # Authentication succeeded; the incomplete payload should
    # proceed to normal event validation.
    assert response.status_code == 422


def test_api_rejects_requests_when_server_api_key_is_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "fleet_api_key", None)

    response = client.get(
        "/vehicles/",
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "API authentication is not configured."}


def test_webhook_endpoint_rejects_requests_when_secret_is_unconfigured(
    monkeypatch,
):
    monkeypatch.setattr(settings, "fleet_webhook_secret", None)

    response = client.post("/fleet-events/", json={})

    assert response.status_code == 503
    assert response.json() == {"detail": "Webhook authentication is not configured."}


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


def test_blank_webhook_secret_setting_is_treated_as_unset():
    blank = Settings(
        database_url="postgresql://x",
        fleet_webhook_secret="   ",
    )

    assert blank.fleet_webhook_secret is None


def test_short_webhook_secret_setting_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://x",
            fleet_webhook_secret="too-short",
        )


def test_valid_webhook_secret_setting_is_accepted_and_trimmed():
    trimmed = Settings(
        database_url="postgresql://x",
        fleet_webhook_secret="  " + "s" * 40 + " ",
    )

    assert trimmed.fleet_webhook_secret.get_secret_value() == "s" * 40
