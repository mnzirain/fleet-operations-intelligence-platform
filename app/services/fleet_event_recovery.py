from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import FleetEvent, FleetEventFinding
from app.services.fleet_event_etl import transform_fleet_event
from app.services.fleet_rules import evaluate_speed_rule


def recover_received_fleet_events(
    db: Session,
    batch_size: int = 100,
) -> dict[str, int]:
    """Reprocess received fleet events using the existing ETL and rules."""

    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    results = {
        "processed": 0,
        "failed": 0,
    }

    for _ in range(batch_size):
        try:
            event = (
                db.query(FleetEvent)
                .filter(FleetEvent.processing_status == "received")
                .order_by(FleetEvent.received_at, FleetEvent.id)
                .with_for_update(skip_locked=True)
                .first()
            )

            if event is None:
                db.rollback()
                break

            try:
                normalized_data = transform_fleet_event(
                    event.event_type,
                    event.payload,
                )
            except ValueError as exc:
                event.processing_status = "failed"
                event.error_message = str(exc)
                event.processed_at = datetime.now(UTC)

                db.commit()
                results["failed"] += 1
                continue

            finding_data = evaluate_speed_rule(normalized_data)

            event.normalized_data = normalized_data
            event.processing_status = "processed"
            event.processed_at = datetime.now(UTC)
            event.error_message = None

            if finding_data is not None:
                existing_finding = (
                    db.query(FleetEventFinding)
                    .filter(
                        FleetEventFinding.fleet_event_id == event.id,
                        FleetEventFinding.rule_id == finding_data["rule_id"],
                    )
                    .first()
                )

                if existing_finding is None:
                    finding = FleetEventFinding(
                        fleet_event_id=event.id,
                        rule_id=finding_data["rule_id"],
                        severity=finding_data["severity"],
                        observed_value=finding_data["observed_value"],
                        threshold=finding_data["threshold"],
                        unit=finding_data["unit"],
                        message=finding_data["message"],
                    )
                    db.add(finding)

            db.commit()
            results["processed"] += 1

        except Exception:
            db.rollback()
            raise

    return results
