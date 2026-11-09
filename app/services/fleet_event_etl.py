import math
from typing import Any


def _number(value: Any, field_name: str) -> float:
    """Convert a numeric value to a finite float, rejecting booleans."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number.")

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid number.") from exc

    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be a finite number.")

    return result


def _normalise_speed(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert speed readings to kilometres per hour."""
    if "speed" not in payload:
        raise ValueError("SPEED events require a speed value.")

    speed = _number(payload["speed"], "speed")

    if speed < 0:
        raise ValueError("speed cannot be negative.")

    unit = str(payload.get("unit", "km/h")).strip().lower()

    if unit in {"km/h", "kph"}:
        speed_kph = speed
    elif unit == "mph":
        speed_kph = speed * 1.609344
    else:
        raise ValueError("Speed unit must be km/h or mph.")

    return {"speed_kph": round(speed_kph, 3)}


def _normalise_location(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and standardise geographic coordinates."""
    if "latitude" not in payload or "longitude" not in payload:
        raise ValueError("LOCATION events require latitude and longitude values.")

    latitude = _number(payload["latitude"], "latitude")
    longitude = _number(payload["longitude"], "longitude")

    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180.")

    return {
        "latitude": latitude,
        "longitude": longitude,
    }


def _normalise_ignition(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert ignition state to a boolean."""
    if "state" not in payload:
        raise ValueError("IGNITION events require a state value.")

    state = payload["state"]

    if isinstance(state, bool):
        ignition_on = state
    elif isinstance(state, str):
        normalised_state = state.strip().upper()

        if normalised_state == "ON":
            ignition_on = True
        elif normalised_state == "OFF":
            ignition_on = False
        else:
            raise ValueError("Ignition state must be ON or OFF.")
    else:
        raise ValueError("Ignition state must be ON or OFF.")

    return {"ignition_on": ignition_on}


def _normalise_odometer(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert odometer readings to kilometres."""
    if "odometer" not in payload:
        raise ValueError("ODOMETER events require an odometer value.")

    odometer = _number(payload["odometer"], "odometer")

    if odometer < 0:
        raise ValueError("odometer cannot be negative.")

    unit = str(payload.get("unit", "km")).strip().lower()

    if unit == "km":
        odometer_km = odometer
    elif unit in {"miles", "mile", "mi"}:
        odometer_km = odometer * 1.609344
    else:
        raise ValueError("Odometer unit must be km or miles.")

    return {"odometer_km": round(odometer_km, 3)}


def transform_fleet_event(
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate and transform a fleet event into standardised data."""
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Event payload must be a non-empty object.")

    normalisers = {
        "SPEED": _normalise_speed,
        "LOCATION": _normalise_location,
        "IGNITION": _normalise_ignition,
        "ODOMETER": _normalise_odometer,
    }

    normaliser = normalisers.get(event_type.strip().upper())

    if normaliser is None:
        raise ValueError(f"Unsupported event type: {event_type}")

    return normaliser(payload)
