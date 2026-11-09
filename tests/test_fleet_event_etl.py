import pytest
from app.services.fleet_event_etl import transform_fleet_event


def test_speed_event_converts_string_to_number():
    result = transform_fleet_event(
        "SPEED",
        {"speed": "115", "unit": "km/h"},
    )

    assert result == {"speed_kph": 115.0}


def test_speed_event_converts_mph_to_kph():
    result = transform_fleet_event(
        "SPEED",
        {"speed": 60, "unit": "mph"},
    )

    assert result == {"speed_kph": 96.561}


def test_speed_event_rejects_negative_speed():
    with pytest.raises(ValueError, match="cannot be negative"):
        transform_fleet_event("SPEED", {"speed": -10})


def test_location_event_validates_coordinates():
    result = transform_fleet_event(
        "LOCATION",
        {"latitude": "-26.6731", "longitude": "27.9261"},
    )

    assert result == {
        "latitude": -26.6731,
        "longitude": 27.9261,
    }


def test_location_event_rejects_invalid_latitude():
    with pytest.raises(ValueError, match="latitude must be between"):
        transform_fleet_event(
            "LOCATION",
            {"latitude": 95, "longitude": 27.9},
        )


def test_ignition_event_converts_on_to_true():
    result = transform_fleet_event(
        "IGNITION",
        {"state": "ON"},
    )

    assert result == {"ignition_on": True}


def test_ignition_event_converts_off_to_false():
    result = transform_fleet_event(
        "IGNITION",
        {"state": "OFF"},
    )

    assert result == {"ignition_on": False}


def test_odometer_event_converts_miles_to_kilometres():
    result = transform_fleet_event(
        "ODOMETER",
        {"odometer": "100", "unit": "miles"},
    )

    assert result == {"odometer_km": 160.934}


def test_odometer_event_rejects_negative_reading():
    with pytest.raises(ValueError, match="cannot be negative"):
        transform_fleet_event(
            "ODOMETER",
            {"odometer": -100},
        )


def test_event_rejects_missing_required_data():
    with pytest.raises(ValueError, match="require a speed value"):
        transform_fleet_event("SPEED", {"unit": "km/h"})


def test_event_rejects_empty_payload():
    with pytest.raises(ValueError, match="non-empty object"):
        transform_fleet_event("SPEED", {})


def test_event_rejects_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported event type"):
        transform_fleet_event("FUEL", {"litres": 50})


def test_event_rejects_boolean_as_numeric_speed():
    with pytest.raises(ValueError, match="must be a number"):
        transform_fleet_event("SPEED", {"speed": True})
