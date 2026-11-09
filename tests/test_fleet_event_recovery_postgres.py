from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import settings
from app.models.fleet_event import FleetEvent
from app.models.fleet_event_finding import FleetEventFinding
from app.models.vehicle import Vehicle
from app.services.fleet_event_recovery import recover_received_fleet_events
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


def test_postgres_recovery_rolls_back_and_succeeds_on_retry(monkeypatch):
    """Verify PostgreSQL rolls back failed recovery and permits a later retry."""
    monkeypatch.setattr(settings, "fleet_max_speed_kph", 100.0)

    test_url = make_url(settings.database_url).set(database="fleet_operations_test")
    engine = create_engine(test_url)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    constraint_name = "ck_test_reject_high_findings"
    vehicle_id = None
    event_id = None

    try:
        with TestSession() as db:
            vehicle = Vehicle(
                fleet_number=f"TEST-{uuid4().hex[:12]}",
                registration_number=f"TST-{uuid4().hex[:10]}",
                make="Test",
                model="Integration",
            )
            db.add(vehicle)
            db.flush()

            event = FleetEvent(
                source_event_id=f"recovery-test-{uuid4()}",
                vehicle_id=vehicle.id,
                event_type="SPEED",
                occurred_at=datetime.now(UTC),
                payload={"speed": 115, "unit": "km/h"},
                processing_status="received",
            )
            db.add(event)
            db.commit()

            vehicle_id = vehicle.id
            event_id = event.id

        # Deliberately reject high-severity findings in the test database.
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE fleet_event_findings
                    ADD CONSTRAINT {constraint_name}
                    CHECK (severity <> 'high')
                    """
                )
            )

        # The finding insert must fail, and recovery must roll back.
        with TestSession() as db:
            with pytest.raises(IntegrityError):
                recover_received_fleet_events(db, batch_size=1)

        # Verify persisted state using a fresh database session.
        with TestSession() as db:
            stored_event = db.get(FleetEvent, event_id)

            assert stored_event.processing_status == "received"
            assert stored_event.normalized_data is None
            assert stored_event.processed_at is None
            assert stored_event.payload == {
                "speed": 115,
                "unit": "km/h",
            }

            finding_count = (
                db.query(FleetEventFinding)
                .filter(FleetEventFinding.fleet_event_id == event_id)
                .count()
            )
            assert finding_count == 0

        # Remove the deliberate failure condition.
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE fleet_event_findings
                    DROP CONSTRAINT {constraint_name}
                    """
                )
            )

        # Retry recovery. It should now process the event successfully.
        with TestSession() as db:
            results = recover_received_fleet_events(db, batch_size=1)
            assert results == {"processed": 1, "failed": 0}

        # Verify the successful retry and exactly one finding.
        with TestSession() as db:
            stored_event = db.get(FleetEvent, event_id)

            assert stored_event.processing_status == "processed"
            assert stored_event.normalized_data["speed_kph"] == 115.0
            assert stored_event.processed_at is not None
            assert stored_event.error_message is None

            findings = (
                db.query(FleetEventFinding)
                .filter(FleetEventFinding.fleet_event_id == event_id)
                .all()
            )

            assert len(findings) == 1
            assert findings[0].rule_id == "SPEED_LIMIT_EXCEEDED"
            assert findings[0].severity == "high"

    finally:
        # Remove the temporary constraint and test records.
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE fleet_event_findings
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                    """
                )
            )

        if event_id is not None:
            with TestSession() as db:
                db.query(FleetEventFinding).filter(
                    FleetEventFinding.fleet_event_id == event_id
                ).delete(synchronize_session=False)

                db.query(FleetEvent).filter(FleetEvent.id == event_id).delete(
                    synchronize_session=False
                )

                if vehicle_id is not None:
                    db.query(Vehicle).filter(Vehicle.id == vehicle_id).delete(
                        synchronize_session=False
                    )

                db.commit()

        engine.dispose()
