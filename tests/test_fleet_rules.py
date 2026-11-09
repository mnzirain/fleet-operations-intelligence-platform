from app.core.config import settings
from app.services.fleet_rules import evaluate_speed_rule


def test_speed_below_threshold_does_not_trigger_rule():
    result = evaluate_speed_rule({"speed_kph": 85.0})

    assert result is None


def test_speed_at_threshold_does_not_trigger_rule():
    result = evaluate_speed_rule({"speed_kph": settings.fleet_max_speed_kph})

    assert result is None


def test_speed_above_threshold_triggers_rule():
    result = evaluate_speed_rule({"speed_kph": 115.0})

    assert result is not None
    assert result["rule_id"] == "SPEED_LIMIT_EXCEEDED"
    assert result["matched"] is True
    assert result["severity"] == "high"
    assert result["observed_value"] == 115.0
    assert result["threshold"] == settings.fleet_max_speed_kph
    assert result["unit"] == "km/h"
