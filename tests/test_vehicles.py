from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

client = TestClient(app)

VEHICLE_ID = UUID("6fe69179-961c-49fa-be52-6975ab55c991")


def create_mock_vehicle():
    """Create a mock vehicle with realistic response attributes."""
    now = datetime.now(UTC)

    return SimpleNamespace(
        id=VEHICLE_ID,
        fleet_number="FLT-002",
        registration_number="XYZ-456-GP",
        make="Toyota",
        model="Hilux",
        manufacture_year=2022,
        vin=None,
        status="active",
        created_at=now,
        updated_at=now,
    )


def configure_mock_database(mock_db, vehicle):
    """Configure the mocked database query to return a vehicle."""
    mock_db.query.return_value.filter.return_value.first.return_value = vehicle


def test_get_vehicle_successfully():
    """Verify that a vehicle can be retrieved by its UUID."""
    mock_db = Mock()
    mock_vehicle = create_mock_vehicle()

    configure_mock_database(mock_db, mock_vehicle)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get(f"/vehicles/{VEHICLE_ID}")

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == str(VEHICLE_ID)
        assert data["fleet_number"] == "FLT-002"
        assert data["registration_number"] == "XYZ-456-GP"
        assert data["make"] == "Toyota"
        assert data["model"] == "Hilux"

        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_get_vehicle_not_found():
    """Verify that retrieving a non-existent vehicle returns 404."""
    mock_db = Mock()
    configure_mock_database(mock_db, None)

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get(f"/vehicles/{VEHICLE_ID}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Vehicle not found."}

        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_delete_vehicle_successfully():
    """Verify that an existing vehicle can be deleted."""
    mock_db = Mock()
    mock_vehicle = create_mock_vehicle()

    configure_mock_database(mock_db, mock_vehicle)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.delete(f"/vehicles/{VEHICLE_ID}")

        assert response.status_code == 204
        assert response.content == b""

        mock_db.delete.assert_called_once_with(mock_vehicle)
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_delete_vehicle_not_found():
    """Verify that deleting a non-existent vehicle returns 404."""
    mock_db = Mock()
    configure_mock_database(mock_db, None)

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.delete(f"/vehicles/{VEHICLE_ID}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Vehicle not found."}

        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_update_vehicle_successfully():
    """Verify that a vehicle can be partially updated."""
    mock_db = Mock()
    mock_vehicle = create_mock_vehicle()

    configure_mock_database(mock_db, mock_vehicle)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.patch(
            f"/vehicles/{VEHICLE_ID}",
            json={"status": "maintenance"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["fleet_number"] == "FLT-002"
        assert data["make"] == "Toyota"
        assert data["model"] == "Hilux"
        assert data["status"] == "maintenance"

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_vehicle)
    finally:
        app.dependency_overrides.clear()


def test_update_vehicle_not_found():
    """Verify that updating a non-existent vehicle returns 404."""
    mock_db = Mock()
    configure_mock_database(mock_db, None)

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.patch(
            f"/vehicles/{VEHICLE_ID}",
            json={"status": "maintenance"},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Vehicle not found."}

        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_update_vehicle_rejects_null_required_field():
    """Verify that required fields cannot be updated to null."""
    mock_db = Mock()
    mock_vehicle = create_mock_vehicle()

    configure_mock_database(mock_db, mock_vehicle)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.patch(
            f"/vehicles/{VEHICLE_ID}",
            json={"make": None},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "make cannot be null."}

        assert mock_vehicle.make == "Toyota"
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_update_vehicle_duplicate_value():
    """Verify that duplicate unique values return HTTP 409."""
    mock_db = Mock()
    mock_vehicle = create_mock_vehicle()

    configure_mock_database(mock_db, mock_vehicle)

    mock_db.commit.side_effect = IntegrityError(
        "UPDATE",
        {},
        Exception("Duplicate unique value"),
    )

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.patch(
            f"/vehicles/{VEHICLE_ID}",
            json={"fleet_number": "FLT-003"},
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": (
                "A vehicle with one or more of these unique values already exists."
            )
        }

        mock_db.rollback.assert_called_once()
    finally:
        app.dependency_overrides.clear()
