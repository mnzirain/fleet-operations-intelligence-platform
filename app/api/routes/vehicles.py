from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"],
)


@router.post(
    "/",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    """Register a new vehicle in the fleet."""
    db_vehicle = Vehicle(**vehicle.model_dump())

    db.add(db_vehicle)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vehicle with one or more of these unique values already exists.",
        ) from exc

    db.refresh(db_vehicle)

    return db_vehicle


@router.get("/", response_model=list[VehicleResponse])
def list_vehicles(db: Session = Depends(get_db)):
    """Return all registered vehicles."""
    return db.query(Vehicle).order_by(Vehicle.created_at.desc()).all()


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID,
    vehicle: VehicleUpdate,
    db: Session = Depends(get_db),
):
    """Update the supplied fields of an existing vehicle."""
    db_vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    if db_vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )

    update_data = vehicle.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is None and field not in {"manufacture_year", "vin"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

        setattr(db_vehicle, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vehicle with one or more of these unique values already exists.",
        ) from exc

    db.refresh(db_vehicle)

    return db_vehicle
