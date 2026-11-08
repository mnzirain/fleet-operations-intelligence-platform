from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    """Validate data when registering a new vehicle."""

    fleet_number: str = Field(min_length=1, max_length=50)
    registration_number: str = Field(min_length=1, max_length=20)
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    manufacture_year: int | None = Field(default=None, ge=1886, le=2100)
    vin: str | None = Field(default=None, min_length=17, max_length=17)


class VehicleUpdate(BaseModel):
    """Validate fields when updating an existing vehicle."""

    fleet_number: str | None = Field(default=None, min_length=1, max_length=50)
    registration_number: str | None = Field(default=None, min_length=1, max_length=20)
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    manufacture_year: int | None = Field(default=None, ge=1886, le=2100)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    status: str | None = Field(default=None, min_length=1, max_length=30)


class VehicleResponse(BaseModel):
    """Define the vehicle data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fleet_number: str
    registration_number: str
    make: str
    model: str
    manufacture_year: int | None
    vin: str | None
    status: str
    created_at: datetime
    updated_at: datetime
