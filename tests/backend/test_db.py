"""Database foundation tests.

The connectivity tests need a reachable PostgreSQL and are skipped when the
relevant URL is not configured, so the rest of the suite still runs on a machine
without a database. They use TEST_DATABASE_URL — a database separate from the
development one — and only read, so there is no data to clean up.
"""

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings, mask_dsn
from app.db import session as session_module
from app.main import app

settings = get_settings()

requires_test_db = pytest.mark.skipif(
    settings.test_database_url is None,
    reason="TEST_DATABASE_URL is not configured",
)
requires_dev_db = pytest.mark.skipif(
    settings.database_url is None,
    reason="DATABASE_URL is not configured",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client that runs the app's lifespan, so the pool is disposed after use."""
    with TestClient(app) as test_client:
        yield test_client


@requires_test_db
def test_async_engine_connects_to_postgresql() -> None:
    """SQLAlchemy opens an async connection and runs a trivial query."""

    async def select_one() -> int:
        engine = create_async_engine(str(settings.test_database_url))
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT 1"))
                return result.scalar_one()
        finally:
            await engine.dispose()

    assert asyncio.run(select_one()) == 1


@requires_test_db
def test_test_database_is_not_the_development_database() -> None:
    """Guard against the suite pointing at development data."""
    if settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    assert str(settings.test_database_url) != str(settings.database_url)


@requires_dev_db
def test_health_db_endpoint_reports_the_database_reachable(
    client: TestClient,
) -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


@requires_dev_db
def test_health_db_response_leaks_no_connection_details(client: TestClient) -> None:
    """The endpoint must never expose credentials, host, or driver details."""
    body = client.get("/health/db").text
    url = str(settings.database_url)

    assert url not in body
    for secret in (url.split("@")[0].split(":")[-1], "postgresql", "asyncpg"):
        assert secret not in body


def _pretend_database_url_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the session module see no DATABASE_URL, regardless of the real .env."""
    monkeypatch.setattr(
        session_module,
        "get_settings",
        lambda: SimpleNamespace(database_url=None),
    )
    # A previous test may have cached an engine built from the real URL.
    session_module.get_engine.cache_clear()
    session_module.get_sessionmaker.cache_clear()


def test_missing_database_url_fails_with_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No DATABASE_URL means a loud, credential-free error — never a fallback."""
    _pretend_database_url_is_missing(monkeypatch)

    with pytest.raises(
        session_module.DatabaseNotConfiguredError,
        match="DATABASE_URL is not configured",
    ):
        session_module._require_database_url()


def test_health_db_returns_503_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing URL surfaces as a clean 503, not a 500 with a traceback.

    The error is raised in the get_db dependency, so this exercises the
    app-level exception handler rather than the route's own try/except.
    """
    _pretend_database_url_is_missing(monkeypatch)

    with TestClient(app) as test_client:
        response = test_client.get("/health/db")
        plain_health = test_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert plain_health.status_code == 200


def test_mask_dsn_removes_the_password() -> None:
    masked = mask_dsn("postgresql+asyncpg://akili:sup3rsecret@127.0.0.1:5433/akili")

    assert "sup3rsecret" not in masked
    assert masked == "postgresql+asyncpg://akili:***@127.0.0.1:5433/akili"
