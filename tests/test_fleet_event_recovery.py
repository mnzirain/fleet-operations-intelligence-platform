from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.core.config import settings
from app.models import FleetEventFinding
from app.services.fleet_event_recovery import recover_received_fleet_events


def test_recover_received_speed_event_creates_finding(monkeypatch):
    """Verify recovery processes a received speed event and creates a finding."""
    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)

    event = SimpleNamespace(
        id=uuid4(),
        event_type="SPEED",
        payload={"speed": 115, "unit": "km/h"},
        processing_status="received",
        received_at=datetime.now(UTC),
        normalized_data=None,
        processed_at=None,
        error_message=None,
    )

    mock_db = Mock()
    event_filter = mock_db.query.return_value.filter.return_value
    event_order = event_filter.order_by.return_value
    locked_events = event_order.with_for_update.return_value
    locked_events.first.side_effect = [event, None]
    event_filter.first.return_value = None

    added_instances = []
    mock_db.add.side_effect = added_instances.append

    results = recover_received_fleet_events(mock_db)

    assert results == {"processed": 1, "failed": 0}
    assert event.processing_status == "processed"
    assert event.normalized_data["speed_kph"] == 115.0
    assert event.processed_at is not None
    assert event.error_message is None

    findings = [
        instance
        for instance in added_instances
        if isinstance(instance, FleetEventFinding)
    ]

    assert len(findings) == 1
    assert findings[0].fleet_event_id == event.id
    assert findings[0].rule_id == "SPEED_LIMIT_EXCEEDED"
    assert findings[0].observed_value == 115.0
    assert findings[0].threshold == 100.0

    assert mock_db.commit.call_count == 1
    assert mock_db.rollback.call_count == 1


def test_recover_received_invalid_event_marks_event_failed():
    """Verify recovery preserves invalid telemetry and records its failure."""
    event = SimpleNamespace(
        id=uuid4(),
        event_type="SPEED",
        payload={"speed": -5, "unit": "km/h"},
        processing_status="received",
        received_at=datetime.now(UTC),
        normalized_data=None,
        processed_at=None,
        error_message=None,
    )

    mock_db = Mock()
    event_filter = mock_db.query.return_value.filter.return_value
    event_order = event_filter.order_by.return_value
    locked_events = event_order.with_for_update.return_value
    locked_events.first.side_effect = [event, None]

    results = recover_received_fleet_events(mock_db)

    assert results == {"processed": 0, "failed": 1}
    assert event.processing_status == "failed"
    assert event.payload == {"speed": -5, "unit": "km/h"}
    assert event.error_message is not None
    assert "speed" in event.error_message.lower()
    assert event.processed_at is not None

    mock_db.add.assert_not_called()
    assert mock_db.commit.call_count == 1
    assert mock_db.rollback.call_count == 1


def test_recover_received_normal_speed_event_creates_no_finding(monkeypatch):
    """Verify normal-speed recovery does not create an operational finding."""
    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)

    event = SimpleNamespace(
        id=uuid4(),
        event_type="SPEED",
        payload={"speed": 80, "unit": "km/h"},
        processing_status="received",
        received_at=datetime.now(UTC),
        normalized_data=None,
        processed_at=None,
        error_message=None,
    )

    mock_db = Mock()
    event_filter = mock_db.query.return_value.filter.return_value
    event_order = event_filter.order_by.return_value
    locked_events = event_order.with_for_update.return_value
    locked_events.first.side_effect = [event, None]

    results = recover_received_fleet_events(mock_db)

    assert results == {"processed": 1, "failed": 0}
    assert event.processing_status == "processed"
    assert event.normalized_data["speed_kph"] == 80.0
    assert event.processed_at is not None
    assert event.error_message is None

    mock_db.add.assert_not_called()
    assert mock_db.commit.call_count == 1
    assert mock_db.rollback.call_count == 1


def test_recover_received_event_does_not_duplicate_existing_finding(monkeypatch):
    """Verify recovery does not create a finding that already exists."""
    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)

    event = SimpleNamespace(
        id=uuid4(),
        event_type="SPEED",
        payload={"speed": 115, "unit": "km/h"},
        processing_status="received",
        received_at=datetime.now(UTC),
        normalized_data=None,
        processed_at=None,
        error_message=None,
    )

    existing_finding = SimpleNamespace(
        fleet_event_id=event.id,
        rule_id="SPEED_LIMIT_EXCEEDED",
    )

    mock_db = Mock()

    event_query = Mock()
    event_filter = event_query.filter.return_value
    event_order = event_filter.order_by.return_value
    locked_events = event_order.with_for_update.return_value
    locked_events.first.side_effect = [event, None]

    finding_query = Mock()
    finding_query.filter.return_value.first.return_value = existing_finding

    mock_db.query.side_effect = [event_query, finding_query, event_query]

    results = recover_received_fleet_events(mock_db)

    assert results == {"processed": 1, "failed": 0}
    assert event.processing_status == "processed"

    mock_db.add.assert_not_called()
    assert mock_db.commit.call_count == 1
    assert mock_db.rollback.call_count == 1


def test_recover_received_event_rolls_back_on_database_error():
    """Verify database errors trigger rollback and are propagated."""
    event = SimpleNamespace(
        id=uuid4(),
        event_type="SPEED",
        payload={"speed": 80, "unit": "km/h"},
        processing_status="received",
        received_at=datetime.now(UTC),
        normalized_data=None,
        processed_at=None,
        error_message=None,
    )

    mock_db = Mock()
    event_filter = mock_db.query.return_value.filter.return_value
    event_order = event_filter.order_by.return_value
    locked_events = event_order.with_for_update.return_value
    locked_events.first.return_value = event

    mock_db.commit.side_effect = RuntimeError("database unavailable")

    try:
        recover_received_fleet_events(mock_db)
    except RuntimeError as exc:
        assert str(exc) == "database unavailable"
    else:
        raise AssertionError("Expected database error to be propagated.")

    assert mock_db.commit.call_count == 1
    assert mock_db.rollback.call_count == 1
