from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.api.routes.fleet_events import get_db
from app.main import app
from fastapi.testclient import TestClient


def make_event(
    processing_status="processed",
    normalized_data=None,
    error_message=None,
):
    vehicle = SimpleNamespace(
        fleet_number="FLT-001",
        registration_number="ABC-123-GP",
        make="Toyota",
        model="Hilux",
        manufacture_year=2023,
    )

    return SimpleNamespace(
        id=uuid4(),
        source_event_id="GPS-TEST-001",
        event_type="vehicle_telemetry",
        occurred_at="2026-11-09T10:00:00",
        received_at="2026-11-09T10:01:00",
        vehicle=vehicle,
        processing_status=processing_status,
        processed_at=None,
        error_message=error_message,
        payload={"speed": 120},
        normalized_data=normalized_data,
    )


def make_finding():
    return SimpleNamespace(
        id=uuid4(),
        rule_id="HIGH_SPEED",
        severity="warning",
        observed_value=120.0,
        threshold=100.0,
        unit="km/h",
        message="Vehicle exceeded the configured speed threshold.",
    )


def configure_mock_database(event, findings=None):
    mock_db = Mock()

    event_query = mock_db.query.return_value.options.return_value.filter.return_value
    event_query.first.return_value = event

    findings_query = (
        mock_db.query.return_value.filter.return_value.order_by.return_value
    )
    findings_query.all.return_value = findings or []

    return mock_db


def make_client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)


def test_investigation_returns_processed_event_and_findings():
    event = make_event(
        normalized_data={
            "speed_kmh": 120.0,
            "ignition_on": True,
        }
    )
    finding = make_finding()
    mock_db = configure_mock_database(event, [finding])
    client = make_client(mock_db)

    try:
        response = client.get(f"/fleet-events/{event.id}/investigation")

        assert response.status_code == 200

        data = response.json()

        assert data["event_id"] == str(event.id)
        assert data["investigation_status"] == "ready"
        assert data["vehicle"]["fleet_number"] == "FLT-001"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["rule_id"] == "HIGH_SPEED"
        assert data["normalized_data"]["speed_kmh"] == 120.0
        assert data["suggested_checks"]
    finally:
        app.dependency_overrides.clear()


def test_investigation_returns_processed_event_without_findings():
    event = make_event(normalized_data={"speed_kmh": 60.0})
    mock_db = configure_mock_database(event)
    client = make_client(mock_db)

    try:
        response = client.get(f"/fleet-events/{event.id}/investigation")

        assert response.status_code == 200

        data = response.json()

        assert data["investigation_status"] == "ready"
        assert data["findings"] == []
        assert "does not establish" in data["summary"].lower()
    finally:
        app.dependency_overrides.clear()


def test_investigation_returns_pending_event():
    event = make_event(processing_status="received")
    mock_db = configure_mock_database(event)
    client = make_client(mock_db)

    try:
        response = client.get(f"/fleet-events/{event.id}/investigation")

        assert response.status_code == 200

        data = response.json()

        assert data["investigation_status"] == "pending_processing"
        assert data["findings"] == []
        assert data["normalized_data"] is None
    finally:
        app.dependency_overrides.clear()


def test_investigation_returns_failed_event():
    event = make_event(
        processing_status="failed",
        error_message="Invalid telemetry payload.",
    )
    mock_db = configure_mock_database(event)
    client = make_client(mock_db)

    try:
        response = client.get(f"/fleet-events/{event.id}/investigation")

        assert response.status_code == 200

        data = response.json()

        assert data["investigation_status"] == "processing_failed"
        assert data["error_message"] == "Invalid telemetry payload."
        assert data["findings"] == []
    finally:
        app.dependency_overrides.clear()


def test_investigation_returns_404_for_unknown_event():
    mock_db = configure_mock_database(None)
    client = make_client(mock_db)

    try:
        response = client.get(f"/fleet-events/{uuid4()}/investigation")

        assert response.status_code == 404
        assert response.json()["detail"] == "Fleet event not found."
    finally:
        app.dependency_overrides.clear()
