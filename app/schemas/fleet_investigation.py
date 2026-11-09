from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleInvestigationDetails(BaseModel):
    """Identify the vehicle involved in an investigation."""

    fleet_number: str
    registration_number: str
    make: str
    model: str
    manufacture_year: int | None


class InvestigationFinding(BaseModel):
    """Represent a deterministic operational finding."""

    id: UUID
    rule_id: str
    severity: str
    observed_value: float
    threshold: float
    unit: str
    message: str


class FleetEventInvestigationResponse(BaseModel):
    """Return an evidence-based fleet event investigation report."""

    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    source_event_id: str
    event_type: str
    occurred_at: datetime
    received_at: datetime

    investigation_status: Literal[
        "ready",
        "pending_processing",
        "processing_failed",
    ]

    vehicle: VehicleInvestigationDetails

    processing_status: str
    processed_at: datetime | None
    error_message: str | None

    original_payload: dict[str, Any]
    normalized_data: dict[str, Any] | None

    findings: list[InvestigationFinding]
    summary: str
    suggested_checks: list[str]
