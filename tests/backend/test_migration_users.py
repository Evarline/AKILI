"""The users/ownership migration against a real database, including the backfill.

Alembic runs as a subprocess from backend/, exactly as a developer runs it, with
DATABASE_URL pointed at the test database. Each scenario asserts both the
success path and that a refused migration leaves the schema untouched.
"""

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
import app.db.models  # noqa: F401  - registers every table on Base.metadata

settings = get_settings()

pytestmark = pytest.mark.skipif(
    settings.test_database_url is None, reason="TEST_DATABASE_URL is not configured"
)

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
PREVIOUS_REVISION = "91f62ba7bf45"
# The revision under test. Later revisions exist; these tests upgrade to this
# one explicitly, so they keep testing exactly this migration's behaviour.
THIS_REVISION = "a3c1d9e7f2b4"
# Every table any revision or `create_all` may have left behind, so a reset is
# a clean slate regardless of what ran before in the same test database.
ALL_TABLES = tuple(t.name for t in Base.metadata.sorted_tables) + ("alembic_version",)


def alembic(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run alembic as a subprocess with the given identity-related environment.

    Other identity variables are removed so only `env` speaks; the root .env is
    still read by Settings, which tests account for where it matters.
    """
    process_env = {
        k: v for k, v in os.environ.items() if k not in ("APP_ENV", "AUTH_MODE", "DEV_FIXED_USER_ID")
    }
    process_env["DATABASE_URL"] = str(settings.test_database_url)
    process_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=process_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def engine() -> Iterator[AsyncEngine]:
    engine = create_async_engine(str(settings.test_database_url), poolclass=NullPool)
    yield engine
    asyncio.run(engine.dispose())


def sql(engine: AsyncEngine, statement: str, **params: object) -> list[tuple]:
    async def go() -> list[tuple]:
        async with engine.begin() as conn:
            result = await conn.execute(text(statement), params)
            return [tuple(r) for r in result] if result.returns_rows else []

    return asyncio.run(go())


def reset_schema(engine: AsyncEngine) -> None:
    sql(engine, f"DROP TABLE IF EXISTS {', '.join(ALL_TABLES)} CASCADE")


def table_exists(engine: AsyncEngine, name: str) -> bool:
    return sql(engine, "SELECT to_regclass(:name) IS NOT NULL", name=name)[0][0]


def column_exists(engine: AsyncEngine, table: str, column: str) -> bool:
    rows = sql(
        engine,
        "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c",
        t=table,
        c=column,
    )
    return bool(rows)


def conversation_count(engine: AsyncEngine) -> int:
    return sql(engine, "SELECT count(*) FROM conversations")[0][0]


@pytest.fixture
def at_previous_revision_with_two_conversations(engine: AsyncEngine) -> Iterator[AsyncEngine]:
    reset_schema(engine)
    result = alembic("upgrade", PREVIOUS_REVISION, env={"APP_ENV": "development"})
    assert result.returncode == 0, result.stderr
    sql(engine, "INSERT INTO conversations (id) VALUES (:a), (:b)", a=uuid4(), b=uuid4())
    assert conversation_count(engine) == 2
    yield engine
    reset_schema(engine)


def assert_untouched(engine: AsyncEngine) -> None:
    """A refused migration rolled back: no users table, no column, rows intact."""
    assert not table_exists(engine, "users")
    assert not column_exists(engine, "conversations", "user_id")
    assert conversation_count(engine) == 2
    assert sql(engine, "SELECT version_num FROM alembic_version") == [(PREVIOUS_REVISION,)]


def test_backfill_refused_outside_development(at_previous_revision_with_two_conversations: AsyncEngine) -> None:
    engine = at_previous_revision_with_two_conversations

    result = alembic("upgrade", THIS_REVISION, env={"APP_ENV": "production", "DEV_FIXED_USER_ID": str(uuid4())})

    assert result.returncode != 0
    assert "only allowed in development" in result.stderr
    assert "Nothing was changed" in result.stderr
    assert_untouched(engine)


def test_backfill_refused_without_a_development_user_id(
    at_previous_revision_with_two_conversations: AsyncEngine,
) -> None:
    if settings.dev_fixed_user_id is not None:
        pytest.skip("the root .env sets DEV_FIXED_USER_ID, so 'unset' cannot be simulated")
    engine = at_previous_revision_with_two_conversations

    result = alembic("upgrade", THIS_REVISION, env={"APP_ENV": "development"})

    assert result.returncode != 0
    assert "DEV_FIXED_USER_ID" in result.stderr
    assert "Nothing was changed" in result.stderr
    assert_untouched(engine)


def test_backfill_assigns_existing_conversations_to_the_development_user(
    at_previous_revision_with_two_conversations: AsyncEngine,
) -> None:
    engine = at_previous_revision_with_two_conversations
    owner = uuid4()

    result = alembic("upgrade", THIS_REVISION, env={"APP_ENV": "development", "DEV_FIXED_USER_ID": str(owner)})

    assert result.returncode == 0, result.stderr
    assert sql(engine, "SELECT id, status, origin FROM users") == [(owner, "ACTIVE", "DEVELOPMENT")]
    assert conversation_count(engine) == 2  # nothing deleted
    assert sql(engine, "SELECT DISTINCT user_id FROM conversations") == [(owner,)]  # nothing orphaned
    nullable = sql(
        engine,
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'conversations' AND column_name = 'user_id'",
    )
    assert nullable == [("NO",)]
    assert sql(engine, "SELECT version_num FROM alembic_version") == [(THIS_REVISION,)]


def test_upgrade_with_no_conversations_creates_no_user(engine: AsyncEngine) -> None:
    reset_schema(engine)
    try:
        result = alembic("upgrade", THIS_REVISION, env={"APP_ENV": "development"})

        assert result.returncode == 0, result.stderr
        assert table_exists(engine, "users")
        assert sql(engine, "SELECT count(*) FROM users") == [(0,)]
    finally:
        reset_schema(engine)


def test_downgrade_keeps_conversations_and_drops_users(engine: AsyncEngine) -> None:
    reset_schema(engine)
    try:
        owner = uuid4()
        assert alembic("upgrade", THIS_REVISION, env={"APP_ENV": "development"}).returncode == 0
        sql(engine, "INSERT INTO users (id, status, origin) VALUES (:id, 'ACTIVE', 'DEVELOPMENT')", id=owner)
        sql(engine, "INSERT INTO conversations (id, user_id) VALUES (:a, :o), (:b, :o)", a=uuid4(), b=uuid4(), o=owner)

        result = alembic("downgrade", PREVIOUS_REVISION, env={"APP_ENV": "development"})

        assert result.returncode == 0, result.stderr
        assert not table_exists(engine, "users")
        assert not column_exists(engine, "conversations", "user_id")
        assert conversation_count(engine) == 2
    finally:
        reset_schema(engine)


def test_ownership_cascade_and_fk_enforced(engine: AsyncEngine) -> None:
    """The constraints the migration creates behave as designed."""
    reset_schema(engine)
    try:
        assert alembic("upgrade", THIS_REVISION, env={"APP_ENV": "development"}).returncode == 0
        owner: UUID = uuid4()
        sql(engine, "INSERT INTO users (id, status, origin) VALUES (:id, 'ACTIVE', 'DEVELOPMENT')", id=owner)
        sql(engine, "INSERT INTO conversations (id, user_id) VALUES (:a, :o)", a=uuid4(), o=owner)

        with pytest.raises(Exception, match="fk_conversations_user_id_users"):
            sql(engine, "INSERT INTO conversations (id, user_id) VALUES (:a, :o)", a=uuid4(), o=uuid4())

        sql(engine, "DELETE FROM users WHERE id = :id", id=owner)
        assert conversation_count(engine) == 0  # ON DELETE CASCADE
    finally:
        reset_schema(engine)
