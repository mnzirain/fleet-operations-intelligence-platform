from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models import FleetEvent, FleetEventFinding, Vehicle
from app.schemas.fleet_event import FleetEventCreate, FleetEventResponse
from app.schemas.fleet_investigation import FleetEventInvestigationResponse
from app.services.fleet_event_etl import transform_fleet_event
from app.services.fleet_event_investigation import (
    get_fleet_event_investigation,
)
from app.services.fleet_rules import evaluate_speed_rule

router = APIRouter(
    prefix="/fleet-events",
    tags=["Fleet Events"],
    dependencies=[Depends(require_api_key)],
)


def _is_same_event(
    existing: FleetEvent,
    incoming: FleetEventCreate,
) -> bool:
    """Check whether a repeated source event contains identical data."""
    return (
        existing.vehicle_id == incoming.vehicle_id
        and existing.event_type == incoming.event_type
        and existing.occurred_at == incoming.occurred_at
        and existing.payload == incoming.payload
    )


@router.post(
    "/",
    response_model=FleetEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_fleet_event(
    event: FleetEventCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    """Receive, transform, evaluate and persist a fleet tracking event."""
    existing_event = (
        db.query(FleetEvent)
        .filter(FleetEvent.source_event_id == event.source_event_id)
        .first()
    )

    if existing_event is not None:
        if _is_same_event(existing_event, event):
            response.status_code = status.HTTP_200_OK
            return existing_event

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This source event ID has already been used for different data.",
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == event.vehicle_id).first()

    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    db_event = FleetEvent(
        source_event_id=event.source_event_id,
        vehicle_id=event.vehicle_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        payload=event.payload,
        processing_status="received",
    )

    db.add(db_event)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        existing_event = (
            db.query(FleetEvent)
            .filter(FleetEvent.source_event_id == event.source_event_id)
            .first()
        )

        if existing_event is not None and _is_same_event(existing_event, event):
            response.status_code = status.HTTP_200_OK
            return existing_event

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The event could not be stored because of a data conflict.",
        ) from exc

    db.refresh(db_event)

    try:
        normalized_data = transform_fleet_event(
            event.event_type,
            event.payload,
        )
    except ValueError as exc:
        db_event.processing_status = "failed"
        db_event.error_message = str(exc)
        db_event.processed_at = datetime.now(UTC)

        db.commit()
        db.refresh(db_event)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    db_event.normalized_data = normalized_data
    db_event.processing_status = "processed"
    db_event.processed_at = datetime.now(UTC)

    finding_data = evaluate_speed_rule(normalized_data)

    if finding_data is not None:
        finding = FleetEventFinding(
            fleet_event_id=db_event.id,
            rule_id=finding_data["rule_id"],
            severity=finding_data["severity"],
            observed_value=finding_data["observed_value"],
            threshold=finding_data["threshold"],
            unit=finding_data["unit"],
            message=finding_data["message"],
        )
        db.add(finding)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(db_event)

    return db_event


@router.get(
    "/{event_id}/investigation",
    response_model=FleetEventInvestigationResponse,
)
def investigate_fleet_event(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    """Return a read-only investigation report for a fleet event."""
    report = get_fleet_event_investigation(db, event_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fleet event not found.",
        )

    return report
