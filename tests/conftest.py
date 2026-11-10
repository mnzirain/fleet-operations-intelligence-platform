import pytest
from app.core.config import settings
from pydantic import SecretStr
from tests.constants import TEST_API_KEY


@pytest.fixture(autouse=True)
def configure_test_api_key(monkeypatch):
    """Give every test a known API key without touching real configuration."""
    monkeypatch.setattr(settings, "fleet_api_key", SecretStr(TEST_API_KEY))
