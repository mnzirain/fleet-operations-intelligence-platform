import pytest
from app.core.config import settings
from pydantic import SecretStr
from tests.constants import TEST_API_KEY, TEST_WEBHOOK_SECRET


@pytest.fixture(autouse=True)
def configure_test_security(monkeypatch):
    """Configure known test credentials without touching real configuration."""
    monkeypatch.setattr(settings, "fleet_api_key", SecretStr(TEST_API_KEY))
    monkeypatch.setattr(
        settings,
        "fleet_webhook_secret",
        SecretStr(TEST_WEBHOOK_SECRET),
    )
