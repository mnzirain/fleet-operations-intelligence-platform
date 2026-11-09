from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventType = Literal["SPEED", "LOCATION", "IGNITION", "ODOMETER"]

ProcessingStatus = Literal["received", "processing", "processed", "failed"]


class FleetEventCreate(BaseModel):
    """Validate an incoming event from an external fleet tracking system."""

    source_event_id: str = Field(min_length=1, max_length=100)
    vehicle_id: UUID
    event_type: EventType
    occurred_at: datetime
    payload: dict[str, Any] = Field(min_length=1)

    @field_validator("event_type", mode="before")
    @classmethod
    def normalise_event_type(cls, value: Any) -> Any:
        """Standardise event types to uppercase."""
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("occurred_at")
    @classmethod
    def normalise_timestamp(cls, value: datetime) -> datetime:
        """Require a timezone-aware timestamp and convert it to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone.")

        return value.astimezone(UTC)


class FleetEventResponse(BaseModel):
    """Define the fleet event data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_event_id: str
    vehicle_id: UUID
    event_type: EventType
    occurred_at: datetime
    received_at: datetime
    payload: dict[str, Any]
    normalized_data: dict[str, Any] | None
    processing_status: ProcessingStatus
    processed_at: datetime | None
    error_message: str | None
