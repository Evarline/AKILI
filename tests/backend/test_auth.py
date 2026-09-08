"""Identity foundation tests.

Two groups. Settings and resolver tests need nothing external. The rest run the
app against PostgreSQL (TEST_DATABASE_URL) with the principal resolver — not
`get_current_user` — overridden, so the real dependency does the lookup,
status check, and origin guard, and the real service enforces ownership.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth import dependencies as dependencies_module
from app.auth import seed as seed_module
from app.auth.dependencies import get_current_user, get_principal_resolver
from app.auth.models import CurrentUser
from app.auth.principals import DevelopmentFixedUserResolver, DisabledResolver, PrincipalResolver
from app.auth.seed import SeedRefusedError, seed_development_user
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.models import (
    USER_ORIGIN_DEVELOPMENT,
    USER_ORIGIN_PROVISIONED,
    USER_STATUS_ACTIVE,
    USER_STATUS_DISABLED,
    Conversation,
    Message,
    User,
)
from app.db.session import get_db
from app.llm.factory import get_llm_provider
from app.main import app
from tests.backend.test_chat import FakeProvider, chat, model_says

settings = get_settings()

requires_test_db = pytest.mark.skipif(
    settings.test_database_url is None, reason="TEST_DATABASE_URL is not configured"
)

IDENTITY_ENV_VARS = ("APP_ENV", "AUTH_MODE", "DEV_FIXED_USER_ID", "BACKEND_HOST")


# --------------------------------------------------------------------------- #
# Settings: the development fixed user is only constructible where it is safe #
# --------------------------------------------------------------------------- #


@pytest.fixture
def clean_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make Settings see only the keyword arguments a test passes."""
    for name in IDENTITY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def make_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_authentication_is_disabled_by_default(clean_identity_env: None) -> None:
    s = make_settings()

    assert s.auth_mode == "disabled"
    assert s.dev_fixed_user_id is None
    assert s.backend_host == "127.0.0.1"


def test_fixed_user_is_allowed_in_development_on_loopback(clean_identity_env: None) -> None:
    user_id = uuid4()
    s = make_settings(
        app_env="development", auth_mode="development_fixed_user", dev_fixed_user_id=user_id
    )

    assert s.dev_fixed_user_id == user_id


@pytest.mark.parametrize("app_env", ["production", "staging", "test", "Development", ""])
def test_fixed_user_refused_outside_development(clean_identity_env: None, app_env: str) -> None:
    """Startup safety: settings cannot be built, so the process cannot start."""
    with pytest.raises(ValidationError, match="only allowed with APP_ENV=development"):
        make_settings(app_env=app_env, auth_mode="development_fixed_user", dev_fixed_user_id=uuid4())


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "akili.example.com", "::"])
def test_fixed_user_refused_on_non_loopback_host(clean_identity_env: None, host: str) -> None:
    with pytest.raises(ValidationError, match="loopback"):
        make_settings(
            app_env="development",
            auth_mode="development_fixed_user",
            dev_fixed_user_id=uuid4(),
            backend_host=host,
        )


def test_fixed_user_requires_an_id(clean_identity_env: None) -> None:
    with pytest.raises(ValidationError, match="DEV_FIXED_USER_ID"):
        make_settings(app_env="development", auth_mode="development_fixed_user")


def test_unknown_auth_mode_is_rejected(clean_identity_env: None) -> None:
    with pytest.raises(ValidationError):
        make_settings(auth_mode="session")


def test_disabled_mode_needs_no_id_in_any_environment(clean_identity_env: None) -> None:
    assert make_settings(app_env="production").auth_mode == "disabled"


# --------------------------------------------------------------------------- #
# Resolvers                                                                    #
# --------------------------------------------------------------------------- #


def fake_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": raw_headers, "query_string": b""})


def test_disabled_resolver_resolves_nobody() -> None:
    assert asyncio.run(DisabledResolver().resolve(fake_request())) is None


def test_fixed_user_resolver_ignores_the_request() -> None:
    """No header can choose a different user; the caller has no say."""
    fixed = uuid4()
    other = uuid4()
    resolver = DevelopmentFixedUserResolver(fixed)

    principal = asyncio.run(
        resolver.resolve(fake_request({"X-User-Id": str(other), "Authorization": f"Bearer {other}"}))
    )

    assert principal is not None
    assert principal.user_id == fixed
    assert principal.method == "development_fixed_user"


def test_resolver_factory_follows_settings(clean_identity_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    dev_settings = make_settings(
        app_env="development", auth_mode="development_fixed_user", dev_fixed_user_id=user_id
    )
    monkeypatch.setattr(dependencies_module, "get_settings", lambda: dev_settings)
    get_principal_resolver.cache_clear()
    try:
        resolver = get_principal_resolver()
        assert isinstance(resolver, DevelopmentFixedUserResolver)
        assert asyncio.run(resolver.resolve(fake_request())).user_id == user_id  # type: ignore[union-attr]

        monkeypatch.setattr(dependencies_module, "get_settings", lambda: make_settings())
        get_principal_resolver.cache_clear()
        assert isinstance(get_principal_resolver(), DisabledResolver)
    finally:
        get_principal_resolver.cache_clear()


# --------------------------------------------------------------------------- #
# Database-backed: users, get_current_user, ownership                          #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def test_sessionmaker() -> Iterator[async_sessionmaker]:
    if settings.test_database_url is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
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


def run(coro):  # noqa: ANN001, ANN201 - tiny test helper
    return asyncio.run(coro)


def create_user(
    sm: async_sessionmaker, *, status: str = USER_STATUS_ACTIVE, origin: str = USER_ORIGIN_DEVELOPMENT
) -> UUID:
    user_id = uuid4()

    async def go() -> None:
        async with sm() as session:
            session.add(User(id=user_id, status=status, origin=origin))
            await session.commit()

    run(go())
    return user_id


def db_scalars(sm: async_sessionmaker, stmt: Any) -> list[Any]:
    async def go() -> list[Any]:
        async with sm() as session:
            return list((await session.execute(stmt)).scalars())

    return run(go())


@contextmanager
def app_as(
    sm: async_sessionmaker, resolver: PrincipalResolver, provider: FakeProvider
) -> Iterator[TestClient]:
    """The app with a chosen resolver. `get_current_user` itself is the real one."""

    async def override_get_db():
        async with sm() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_principal_resolver] = lambda: resolver
    app.dependency_overrides[get_llm_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@requires_test_db
def test_user_row_defaults(test_sessionmaker: async_sessionmaker) -> None:
    user_id = create_user(test_sessionmaker)

    user = db_scalars(test_sessionmaker, select(User).where(User.id == user_id))[0]
    assert user.status == USER_STATUS_ACTIVE
    assert user.origin == USER_ORIGIN_DEVELOPMENT
    assert user.created_at.tzinfo is not None and user.updated_at.tzinfo is not None
    assert user.created_at <= datetime.now(UTC)
    # Nothing on the row could authenticate anyone.
    column_names = {c.name for c in User.__table__.columns}
    assert column_names == {"id", "status", "origin", "created_at", "updated_at"}


@requires_test_db
@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"status": "BOGUS", "origin": USER_ORIGIN_DEVELOPMENT}, id="bad-status"),
        pytest.param({"status": USER_STATUS_ACTIVE, "origin": "SEEDED"}, id="bad-origin"),
        pytest.param({"status": USER_STATUS_ACTIVE, "origin": None}, id="origin-required"),
    ],
)
def test_user_constraints_reject_invalid_rows(test_sessionmaker: async_sessionmaker, fields: dict) -> None:
    async def go() -> None:
        async with test_sessionmaker() as session:
            session.add(User(**fields))
            with pytest.raises(IntegrityError):
                await session.commit()

    run(go())


@requires_test_db
def test_active_user_is_resolved_and_owns_the_conversation(test_sessionmaker: async_sessionmaker) -> None:
    user_id = create_user(test_sessionmaker)
    provider = FakeProvider()
    provider.queue.append(model_says())

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id), provider) as client:
        response = chat(client, "Hello")

    assert response.status_code == 200
    conversation_id = UUID(response.json()["conversation_id"])
    owner = db_scalars(test_sessionmaker, select(Conversation.user_id).where(Conversation.id == conversation_id))
    assert owner == [user_id]


@requires_test_db
def test_disabled_user_is_401(test_sessionmaker: async_sessionmaker) -> None:
    user_id = create_user(test_sessionmaker, status=USER_STATUS_DISABLED)
    provider = FakeProvider()
    before = db_scalars(test_sessionmaker, select(func.count()).select_from(Conversation))[0]

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(user_id), provider) as client:
        response = chat(client, "Hello")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert provider.requests == []
    assert db_scalars(test_sessionmaker, select(func.count()).select_from(Conversation))[0] == before


@requires_test_db
def test_unknown_user_id_is_401_and_indistinguishable(test_sessionmaker: async_sessionmaker) -> None:
    provider = FakeProvider()

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(uuid4()), provider) as client:
        response = chat(client, "Hello")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}  # same body as "disabled"
    assert provider.requests == []


@requires_test_db
def test_disabled_authentication_exposes_nothing(test_sessionmaker: async_sessionmaker) -> None:
    """AUTH_MODE=disabled (the default): protected routes 401, health still works."""
    provider = FakeProvider()
    before = db_scalars(test_sessionmaker, select(func.count()).select_from(Conversation))[0]

    with app_as(test_sessionmaker, DisabledResolver(), provider) as client:
        response = chat(client, "Hello")
        health = client.get("/health")

    assert response.status_code == 401
    assert health.status_code == 200
    assert provider.requests == []
    assert db_scalars(test_sessionmaker, select(func.count()).select_from(Conversation))[0] == before


@requires_test_db
def test_request_cannot_choose_its_user(test_sessionmaker: async_sessionmaker) -> None:
    fixed = create_user(test_sessionmaker)
    other = create_user(test_sessionmaker)
    provider = FakeProvider()
    provider.queue.append(model_says())

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(fixed), provider) as client:
        # A user_id in the body is rejected outright (extra fields are forbidden).
        smuggled = client.post("/api/v1/chat", json={"message": "hi", "user_id": str(other)})
        # Headers naming another user change nothing.
        response = client.post(
            "/api/v1/chat",
            json={"message": "hi"},
            headers={"X-User-Id": str(other), "Authorization": f"Bearer {other}"},
        )

    assert smuggled.status_code == 422
    assert response.status_code == 200
    owner = db_scalars(
        test_sessionmaker,
        select(Conversation.user_id).where(Conversation.id == UUID(response.json()["conversation_id"])),
    )
    assert owner == [fixed]


@requires_test_db
def test_another_users_conversation_is_not_found(test_sessionmaker: async_sessionmaker) -> None:
    alice = create_user(test_sessionmaker)
    bob = create_user(test_sessionmaker)
    provider = FakeProvider()
    provider.queue.append(model_says())

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(alice), provider) as client:
        conversation_id = UUID(chat(client, "Alice's secret plan").json()["conversation_id"])

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(bob), provider) as client:
        intrusion = chat(client, "Show me", conversation_id)

    assert intrusion.status_code == 404
    assert intrusion.json() == {"detail": "Conversation not found"}  # same as an unknown id
    assert len(provider.requests) == 1  # Bob's turn never reached the model
    contents = db_scalars(
        test_sessionmaker,
        select(Message.content).where(Message.conversation_id == conversation_id),
    )
    assert contents == ["Alice's secret plan", "Here is an explanation."]  # nothing of Bob's

    # Alice herself can continue it.
    provider.queue.append(model_says())
    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(alice), provider) as client:
        assert chat(client, "Continue", conversation_id).status_code == 200


@requires_test_db
def test_development_origin_user_is_refused_outside_development(
    test_sessionmaker: async_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Second guard, independent of settings validation: a DEVELOPMENT-origin
    row must never be served when the app is not in development."""
    dev_user = create_user(test_sessionmaker, origin=USER_ORIGIN_DEVELOPMENT)
    provider = FakeProvider()
    monkeypatch.setattr(settings, "app_env", "production")

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(dev_user), provider) as client:
        response = chat(client, "Hello")

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication unavailable"}
    assert provider.requests == []


@requires_test_db
def test_provisioned_origin_user_is_served_outside_development(
    test_sessionmaker: async_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The origin guard is specific: it does not block real users."""
    real_user = create_user(test_sessionmaker, origin=USER_ORIGIN_PROVISIONED)
    provider = FakeProvider()
    provider.queue.append(model_says())
    monkeypatch.setattr(settings, "app_env", "production")

    with app_as(test_sessionmaker, DevelopmentFixedUserResolver(real_user), provider) as client:
        assert chat(client, "Hello").status_code == 200


@requires_test_db
def test_get_current_user_returns_a_plain_value(test_sessionmaker: async_sessionmaker) -> None:
    user_id = create_user(test_sessionmaker)

    async def go() -> CurrentUser:
        async with test_sessionmaker() as session:
            return await get_current_user(
                fake_request(), session=session, resolver=DevelopmentFixedUserResolver(user_id)
            )

    current = run(go())
    assert current == CurrentUser(id=user_id)
    assert not isinstance(current, User)


# --------------------------------------------------------------------------- #
# Seeding the development user                                                 #
# --------------------------------------------------------------------------- #


@requires_test_db
def test_seed_is_idempotent_and_creates_a_development_user(test_sessionmaker: async_sessionmaker) -> None:
    user_id = uuid4()

    async def go() -> tuple[bool, bool]:
        async with test_sessionmaker() as session:
            first = await seed_development_user(session, user_id)
        async with test_sessionmaker() as session:
            second = await seed_development_user(session, user_id)
        return first, second

    assert run(go()) == (True, False)
    users = db_scalars(test_sessionmaker, select(User).where(User.id == user_id))
    assert len(users) == 1
    assert users[0].origin == USER_ORIGIN_DEVELOPMENT and users[0].status == USER_STATUS_ACTIVE


@requires_test_db
def test_seed_never_reactivates_or_promotes(test_sessionmaker: async_sessionmaker) -> None:
    disabled = create_user(test_sessionmaker, status=USER_STATUS_DISABLED, origin=USER_ORIGIN_PROVISIONED)

    async def go() -> bool:
        async with test_sessionmaker() as session:
            return await seed_development_user(session, disabled)

    assert run(go()) is False
    user = db_scalars(test_sessionmaker, select(User).where(User.id == disabled))[0]
    assert user.status == USER_STATUS_DISABLED and user.origin == USER_ORIGIN_PROVISIONED


def test_seed_command_refuses_unless_in_fixed_user_mode(
    clean_identity_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(seed_module, "get_settings", lambda: make_settings())
    with pytest.raises(SeedRefusedError, match="development only"):
        seed_module._require_development_mode()

    user_id = uuid4()
    monkeypatch.setattr(
        seed_module,
        "get_settings",
        lambda: make_settings(
            app_env="development", auth_mode="development_fixed_user", dev_fixed_user_id=user_id
        ),
    )
    assert seed_module._require_development_mode() == user_id
