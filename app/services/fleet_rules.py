from typing import Any

from app.core.config import settings


def evaluate_speed_rule(
    normalized_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Evaluate whether a normalised speed reading exceeds the configured limit."""

    speed_kph = normalized_data.get("speed_kph")

    if speed_kph is None:
        return None

    threshold = settings.fleet_max_speed_kph

    if speed_kph <= threshold:
        return None

    return {
        "rule_id": "SPEED_LIMIT_EXCEEDED",
        "matched": True,
        "severity": "high",
        "observed_value": speed_kph,
        "threshold": threshold,
        "unit": "km/h",
        "message": (
            f"Vehicle speed of {speed_kph} km/h exceeded "
            f"the demonstration threshold of {threshold} km/h."
        ),
    }
