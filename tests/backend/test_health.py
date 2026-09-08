"""Tests for the health endpoint.

Local and deterministic: no database, no network, no external service.
`backend/` is on the path via pyproject.toml, so the app imports as `app.*`.
"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_200_and_status_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_the_application_version() -> None:
    response = client.get("/health")

    assert response.json()["version"] == get_settings().app_version
