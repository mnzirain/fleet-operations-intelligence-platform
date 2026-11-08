from unittest.mock import Mock

from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "Fleet Operations Intelligence Platform"
    assert data["status"] == "running"
    assert "environment" in data


def test_health_endpoint():
    """Verify that the application health endpoint works."""
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_endpoint():
    """Verify that readiness succeeds when the database is available."""
    mock_db = Mock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "connected",
        }
        mock_db.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_database_unavailable():
    """Verify that readiness returns 503 when the database is unavailable."""
    mock_db = Mock()
    mock_db.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("Database connection failed"),
    )

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/health/ready")

        assert response.status_code == 503
        assert response.json() == {
            "detail": "Database unavailable",
        }
    finally:
        app.dependency_overrides.clear()
