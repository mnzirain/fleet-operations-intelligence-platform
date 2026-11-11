from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import FleetEvent, FleetEventFinding
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from tests.webhook_helpers import make_signed_webhook_request

client = TestClient(app)

VEHICLE_ID = uuid4()


def post_signed_event(payload):
    """Send a fleet event with a valid HMAC signature."""
    body, headers = make_signed_webhook_request(payload)

    return client.post(
        "/fleet-events/",
        content=body,
        headers=headers,
    )


def test_ingest_speed_event_creates_finding(monkeypatch):
    """Verify that an excessive speed event creates an operational finding."""
    mock_db = Mock()
    vehicle = SimpleNamespace(id=VEHICLE_ID)

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        vehicle,
    ]

    def add_to_mock_database(instance):
        if isinstance(instance, FleetEvent):
            instance.id = uuid4()
            instance.received_at = datetime.now(UTC)

    mock_db.add.side_effect = add_to_mock_database

    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-SPEED-001",
                "vehicle_id": str(VEHICLE_ID),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:00:00Z",
                "payload": {"speed": 115, "unit": "km/h"},
            }
        )

        assert response.status_code == 201

        data = response.json()

        assert data["source_event_id"] == "TEST-SPEED-001"
        assert data["processing_status"] == "processed"
        assert data["normalized_data"]["speed_kph"] == 115.0

        added_instances = [call.args[0] for call in mock_db.add.call_args_list]
        findings = [
            instance
            for instance in added_instances
            if isinstance(instance, FleetEventFinding)
        ]

        assert len(findings) == 1
        assert findings[0].rule_id == "SPEED_LIMIT_EXCEEDED"
        assert findings[0].severity == "high"
        assert findings[0].observed_value == 115.0
        assert findings[0].threshold == 100.0

        assert mock_db.commit.call_count == 2
    finally:
        app.dependency_overrides.clear()


def test_ingest_invalid_speed_event_preserves_failed_event():
    """Verify that invalid speed data is preserved as a failed event."""
    mock_db = Mock()
    vehicle = SimpleNamespace(id=VEHICLE_ID)

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        vehicle,
    ]

    def add_to_mock_database(instance):
        if isinstance(instance, FleetEvent):
            instance.id = uuid4()
            instance.received_at = datetime.now(UTC)

    mock_db.add.side_effect = add_to_mock_database
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-SPEED-INVALID-001",
                "vehicle_id": str(VEHICLE_ID),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:10:00Z",
                "payload": {"speed": -5, "unit": "km/h"},
            }
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "speed cannot be negative."}

        added_instances = [call.args[0] for call in mock_db.add.call_args_list]
        events = [
            instance for instance in added_instances if isinstance(instance, FleetEvent)
        ]

        assert len(events) == 1
        assert events[0].payload == {"speed": -5, "unit": "km/h"}
        assert events[0].processing_status == "failed"
        assert events[0].normalized_data is None
        assert events[0].error_message == "speed cannot be negative."
        assert events[0].processed_at is not None

        assert mock_db.commit.call_count == 2
    finally:
        app.dependency_overrides.clear()


def test_ingest_duplicate_event_returns_existing_event():
    """Verify that an identical event is not inserted twice."""
    occurred_at = datetime(2026, 11, 9, 7, 20, tzinfo=UTC)

    existing_event = SimpleNamespace(
        id=uuid4(),
        source_event_id="TEST-DUPLICATE-001",
        vehicle_id=VEHICLE_ID,
        event_type="SPEED",
        occurred_at=occurred_at,
        received_at=datetime.now(UTC),
        payload={"speed": 115, "unit": "km/h"},
        normalized_data={"speed_kph": 115.0},
        processing_status="processed",
        processed_at=datetime.now(UTC),
        error_message=None,
    )

    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing_event
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-DUPLICATE-001",
                "vehicle_id": str(VEHICLE_ID),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:20:00Z",
                "payload": {"speed": 115, "unit": "km/h"},
            }
        )

        assert response.status_code == 200
        assert response.json()["source_event_id"] == "TEST-DUPLICATE-001"
        assert response.json()["processing_status"] == "processed"

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_ingest_duplicate_event_with_different_payload_returns_conflict():
    """Verify that a reused event ID with different data returns HTTP 409."""
    mock_db = Mock()

    existing_event = SimpleNamespace(
        id=uuid4(),
        source_event_id="TEST-CONFLICT-001",
        vehicle_id=VEHICLE_ID,
        event_type="SPEED",
        occurred_at=datetime(2026, 11, 9, 7, 20, tzinfo=UTC),
        payload={"speed": 80, "unit": "km/h"},
    )

    mock_db.query.return_value.filter.return_value.first.return_value = existing_event
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-CONFLICT-001",
                "vehicle_id": str(VEHICLE_ID),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:20:00Z",
                "payload": {"speed": 115, "unit": "km/h"},
            }
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": "This source event ID has already been used for different data."
        }

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_ingest_event_with_unknown_vehicle_returns_not_found():
    """Verify that events for unregistered vehicles are rejected."""
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-UNKNOWN-VEHICLE-001",
                "vehicle_id": str(uuid4()),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:30:00Z",
                "payload": {"speed": 85, "unit": "km/h"},
            }
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Vehicle not found."}

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_ingest_normal_speed_event_creates_no_finding(monkeypatch):
    """Verify that normal speed events do not create findings."""
    mock_db = Mock()
    vehicle = SimpleNamespace(id=VEHICLE_ID)

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        vehicle,
    ]

    def add_to_mock_database(instance):
        if isinstance(instance, FleetEvent):
            instance.id = uuid4()
            instance.received_at = datetime.now(UTC)

    mock_db.add.side_effect = add_to_mock_database

    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = post_signed_event(
            {
                "source_event_id": "TEST-NORMAL-SPEED-001",
                "vehicle_id": str(VEHICLE_ID),
                "event_type": "SPEED",
                "occurred_at": "2026-11-09T07:40:00Z",
                "payload": {"speed": 85, "unit": "km/h"},
            }
        )

        assert response.status_code == 201

        data = response.json()

        assert data["processing_status"] == "processed"
        assert data["normalized_data"]["speed_kph"] == 85.0

        added_instances = [call.args[0] for call in mock_db.add.call_args_list]
        findings = [
            instance
            for instance in added_instances
            if isinstance(instance, FleetEventFinding)
        ]

        assert findings == []
        assert mock_db.commit.call_count == 2
    finally:
        app.dependency_overrides.clear()


def test_processing_database_failure_rolls_back_second_transaction(
    monkeypatch,
):
    """Verify that a failed processing commit triggers a rollback."""
    mock_db = Mock()
    vehicle = SimpleNamespace(id=VEHICLE_ID)

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        vehicle,
    ]

    def add_to_mock_database(instance):
        if isinstance(instance, FleetEvent):
            instance.id = uuid4()
            instance.received_at = datetime.now(UTC)

    mock_db.add.side_effect = add_to_mock_database

    mock_db.commit.side_effect = [
        None,
        SQLAlchemyError("Simulated processing database failure."),
    ]

    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with pytest.raises(
            SQLAlchemyError,
            match="Simulated processing database failure.",
        ):
            post_signed_event(
                {
                    "source_event_id": "TEST-DB-FAILURE-001",
                    "vehicle_id": str(VEHICLE_ID),
                    "event_type": "SPEED",
                    "occurred_at": "2026-11-09T07:50:00Z",
                    "payload": {"speed": 115, "unit": "km/h"},
                }
            )

        assert mock_db.commit.call_count == 2
        mock_db.rollback.assert_called_once_with()
    finally:
        app.dependency_overrides.clear()
