from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import FleetEvent, FleetEventFinding
from app.schemas.fleet_investigation import (
    FleetEventInvestigationResponse,
    InvestigationFinding,
)


def get_fleet_event_investigation(
    db: Session,
    event_id: UUID,
) -> FleetEventInvestigationResponse | None:
    """Build a read-only investigation report for a fleet event."""

    event = (
        db.query(FleetEvent)
        .options(joinedload(FleetEvent.vehicle))
        .filter(FleetEvent.id == event_id)
        .first()
    )

    if event is None:
        return None

    database_findings = (
        db.query(FleetEventFinding)
        .filter(FleetEventFinding.fleet_event_id == event.id)
        .order_by(FleetEventFinding.created_at, FleetEventFinding.id)
        .all()
    )

    findings = [
        InvestigationFinding.model_validate(
            finding,
            from_attributes=True,
        )
        for finding in database_findings
    ]

    if event.processing_status == "processed":
        investigation_status = "ready"

        if findings:
            summary = (
                f"Event processed successfully. "
                f"{len(findings)} rule-based finding(s) recorded."
            )
        else:
            summary = (
                "Event processed successfully. No rule-based findings "
                "were recorded. This does not establish that no "
                "operational issue occurred."
            )

    elif event.processing_status == "received":
        investigation_status = "pending_processing"
        summary = "Event has been received but has not completed processing."

    elif event.processing_status == "failed":
        investigation_status = "processing_failed"
        summary = (
            "Event processing failed. Review the recorded error "
            "and original event payload."
        )

    else:
        raise ValueError(
            f"Unsupported event processing status: {event.processing_status}"
        )

    suggested_checks = [
        "Verify the event details against the original fleet tracking data.",
        "Confirm the vehicle and event timestamp are correct.",
    ]

    if findings:
        suggested_checks.append(
            "Review each recorded rule-based finding against the "
            "applicable operational policy."
        )

    if event.processing_status == "failed":
        suggested_checks.append(
            "Investigate the processing error before attempting recovery."
        )

    return FleetEventInvestigationResponse(
        event_id=event.id,
        source_event_id=event.source_event_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        investigation_status=investigation_status,
        vehicle={
            "fleet_number": event.vehicle.fleet_number,
            "registration_number": event.vehicle.registration_number,
            "make": event.vehicle.make,
            "model": event.vehicle.model,
            "manufacture_year": event.vehicle.manufacture_year,
        },
        processing_status=event.processing_status,
        processed_at=event.processed_at,
        error_message=event.error_message,
        original_payload=event.payload,
        normalized_data=event.normalized_data,
        findings=findings,
        summary=summary,
        suggested_checks=suggested_checks,
    )
