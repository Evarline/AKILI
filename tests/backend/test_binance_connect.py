"""The CIMD document and GET /api/v1/binance/connect, end to end through the app.

Binance is replaced by a fake transport serving its real metadata shapes, so
nothing here touches the network. Identity uses the real `get_current_user`
with only the resolver overridden. Needs PostgreSQL (TEST_DATABASE_URL).
"""

import asyncio
import base64
import hashlib
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.binance_oauth import get_oauth_http_client
from app.auth.dependencies import get_principal_resolver
from app.auth.principals import DevelopmentFixedUserResolver, DisabledResolver, PrincipalResolver
from app.core.config import CIMD_PATH, get_settings
from app.db.base import Base
from app.db.models import USER_ORIGIN_DEVELOPMENT, OAuthAuthorizationRequest, User
from app.db.session import get_db
from app.main import app
from app.oauth.crypto import SecretBox
from tests.backend.test_oauth_infra import (
    BINANCE_ASM,
    BINANCE_PRM,
    CIMD_URL,
    MCP_URL,
    REDIRECT_URI,
    make_binance_transport,
)

settings = get_settings()

pytestmark = pytest.mark.skipif(
    settings.test_database_url is None, reason="TEST_DATABASE_URL is not configured"
)


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def test_sessionmaker() -> Iterator[async_sessionmaker]:
    engine = create_async_engine(str(settings.test_database_url), poolclass=NullPool)

    async def create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def drop() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(create())
    yield async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(drop())


@pytest.fixture
def encryption_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def binance_enabled(monkeypatch: pytest.MonkeyPatch, encryption_key: str) -> None:
    """Turn the feature on in the cached settings, exactly as a real .env would."""
    monkeypatch.setattr(settings, "binance_oauth_enabled", True)
    monkeypatch.setattr(settings, "binance_mcp_server_url", MCP_URL)
    monkeypatch.setattr(settings, "binance_cimd_url", CIMD_URL)
    monkeypatch.setattr(settings, "binance_redirect_uri", REDIRECT_URI)
    monkeypatch.setattr(settings, "oauth_encryption_key", SecretStr(encryption_key))


def create_user(sm: async_sessionmaker) -> UUID:
    user_id = uuid4()

    async def go() -> None:
        async with sm() as session:
            session.add(User(id=user_id, origin=USER_ORIGIN_DEVELOPMENT))
            await session.commit()

    asyncio.run(go())
    return user_id


def db_scalars(sm: async_sessionmaker, stmt: Any) -> list[Any]:
    async def go() -> list[Any]:
        async with sm() as session:
            return list((await session.execute(stmt)).scalars())

    return asyncio.run(go())


@contextmanager
def app_as(
    sm: async_sessionmaker,
    resolver: PrincipalResolver,
    transport: httpx2.MockTransport | None = None,
) -> Iterator[TestClient]:
    transport = transport or make_binance_transport()

    async def override_get_db():
        async with sm() as session:
            yield session

    async def override_http_client():
        async with httpx2.AsyncClient(transport=transport) as client:
            yield client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_principal_resolver] = lambda: resolver
    app.dependency_overrides[get_oauth_http_client] = override_http_client
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def connect(client: TestClient, **kwargs: Any):
    return client.get("/api/v1/binance/connect", follow_redirects=False, **kwargs)


def requests_for(sm: async_sessionmaker, user_id: UUID) -> list[OAuthAuthorizationRequest]:
    return db_scalars(
        sm, select(OAuthAuthorizationRequest).where(OAuthAuthorizationRequest.user_id == user_id)
    )


# --------------------------------------------------------------------------- #
# CIMD document                                                                #
# --------------------------------------------------------------------------- #


def test_cimd_document_is_not_published_while_disabled(test_sessionmaker: async_sessionmaker) -> None:
    assert settings.binance_oauth_enabled is False
    with app_as(test_sessionmaker, DisabledResolver()) as client:
        assert client.get(CIMD_PATH).status_code == 404


def test_cimd_document_names_itself_and_declares_the_redirect(
    test_sessionmaker: async_sessionmaker, binance_enabled: None, encryption_key: str
) -> None:
    with app_as(test_sessionmaker, DisabledResolver()) as client:  # public: no identity needed
        response = client.get(CIMD_PATH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "public, max-age=3600"
    body = response.json()
    assert body == {
        "client_id": CIMD_URL,
        "client_name": settings.app_name,
        "client_uri": "https://akili.example.test/",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    # The URL the document lives at is the URL it claims to be.
    assert urlsplit(body["client_id"]).path == CIMD_PATH
    assert body["client_id"] == settings.binance_cimd_url
    # A public client: nothing secret is in the document.
    for secret in (encryption_key, str(settings.database_url or "")):
        assert secret not in response.text
    assert "client_secret" not in response.text


# --------------------------------------------------------------------------- #
# GET /api/v1/binance/connect                                                  #
# --------------------------------------------------------------------------- #


def test_connect_does_not_exist_while_disabled(test_sessionmaker: async_sessionmaker) -> None:
    user_id = create_user(test_sessionmaker)
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id)) as client:
        response = connect(client)

    assert response.status_code == 404
    assert requests_for(test_sessionmaker, user_id) == []


def test_connect_requires_an_authenticated_user(test_sessionmaker: async_sessionmaker, binance_enabled: None) -> None:
    before = db_scalars(test_sessionmaker, select(func.count()).select_from(OAuthAuthorizationRequest))[0]
    with app_as(test_sessionmaker, DisabledResolver()) as client:
        response = connect(client)

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert db_scalars(test_sessionmaker, select(func.count()).select_from(OAuthAuthorizationRequest))[0] == before


def test_connect_redirects_to_binance_with_a_persisted_owned_request(
    test_sessionmaker: async_sessionmaker, binance_enabled: None, encryption_key: str
) -> None:
    user_id = create_user(test_sessionmaker)
    started = datetime.now(UTC)

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id)) as client:
        response = connect(client)

    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == BINANCE_ASM["authorization_endpoint"]
    query = parse_qs(location.query, strict_parsing=True)
    assert set(query) == {
        "response_type", "client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method", "resource",
    }
    assert query["response_type"] == ["code"]
    assert query["client_id"] == [CIMD_URL]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["code_challenge_method"] == ["S256"]
    assert query["resource"] == [BINANCE_PRM["resource"]]
    assert "scope" not in query

    # Exactly one request, owned by the caller, keyed by the state in the URL.
    rows = requests_for(test_sessionmaker, user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.state == query["state"][0]
    assert row.user_id == user_id
    assert row.provider == "binance"
    assert row.client_id == CIMD_URL
    assert row.redirect_uri == REDIRECT_URI
    assert row.resource == BINANCE_PRM["resource"]
    assert row.expected_issuer == BINANCE_ASM["issuer"]
    assert timedelta(minutes=9) < row.expires_at - started < timedelta(minutes=11)

    # The verifier is sealed at rest, and the challenge Binance saw is S256 of it.
    verifier = SecretBox(encryption_key).open(row.code_verifier_ciphertext)
    assert verifier.encode() not in row.code_verifier_ciphertext
    assert s256(verifier) == query["code_challenge"][0]


def test_each_connect_gets_a_fresh_state_and_verifier(
    test_sessionmaker: async_sessionmaker, binance_enabled: None
) -> None:
    user_id = create_user(test_sessionmaker)
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id)) as client:
        first = parse_qs(urlsplit(connect(client).headers["location"]).query)
        second = parse_qs(urlsplit(connect(client).headers["location"]).query)

    assert first["state"] != second["state"]
    assert first["code_challenge"] != second["code_challenge"]
    assert {r.state for r in requests_for(test_sessionmaker, user_id)} == {first["state"][0], second["state"][0]}


def test_no_request_parameter_can_choose_the_owner_or_the_state(
    test_sessionmaker: async_sessionmaker, binance_enabled: None
) -> None:
    me = create_user(test_sessionmaker)
    other = create_user(test_sessionmaker)

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(me)) as client:
        response = connect(
            client,
            params={"user_id": str(other), "state": "attacker-chosen", "redirect_uri": "https://evil.example/"},
            headers={"X-User-Id": str(other), "Authorization": f"Bearer {other}"},
        )

    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["state"] != ["attacker-chosen"]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert requests_for(test_sessionmaker, other) == []
    mine = requests_for(test_sessionmaker, me)
    assert len(mine) == 1 and mine[0].state == query["state"][0]


def test_secrets_are_not_written_to_logs(
    test_sessionmaker: async_sessionmaker,
    binance_enabled: None,
    encryption_key: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_id = create_user(test_sessionmaker)
    caplog.set_level(logging.DEBUG)

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id)) as client:
        location = connect(client).headers["location"]

    query = parse_qs(urlsplit(location).query)
    row = requests_for(test_sessionmaker, user_id)[0]
    verifier = SecretBox(encryption_key).open(row.code_verifier_ciphertext)

    logged = caplog.text
    assert verifier not in logged
    assert query["state"][0] not in logged
    assert query["code_challenge"][0] not in logged
    assert location not in logged
    assert encryption_key not in logged
    # Something was logged, so the assertions above are meaningful.
    assert "binance authorization started" in logged


def test_discovery_failure_is_a_503_and_persists_nothing(
    test_sessionmaker: async_sessionmaker, binance_enabled: None
) -> None:
    user_id = create_user(test_sessionmaker)
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id), make_binance_transport(prm=None)) as client:
        response = connect(client)

    assert response.status_code == 503
    assert response.json() == {"detail": "Binance authorization is unavailable"}
    assert requests_for(test_sessionmaker, user_id) == []


def test_server_without_cimd_support_is_refused(
    test_sessionmaker: async_sessionmaker, binance_enabled: None
) -> None:
    user_id = create_user(test_sessionmaker)
    asm = {**BINANCE_ASM, "client_id_metadata_document_supported": False}
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id), make_binance_transport(asm=asm)) as client:
        response = connect(client)

    assert response.status_code == 503
    assert requests_for(test_sessionmaker, user_id) == []


def test_deleting_the_user_removes_their_authorization_requests(
    test_sessionmaker: async_sessionmaker, binance_enabled: None
) -> None:
    user_id = create_user(test_sessionmaker)
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id)) as client:
        assert connect(client).status_code == 302
    assert len(requests_for(test_sessionmaker, user_id)) == 1

    async def delete_user() -> None:
        async with test_sessionmaker() as session:
            user = await session.get(User, user_id)
            await session.delete(user)
            await session.commit()

    asyncio.run(delete_user())
    assert requests_for(test_sessionmaker, user_id) == []
