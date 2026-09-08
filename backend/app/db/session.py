"""Async SQLAlchemy engine, session factory, and the FastAPI session dependency."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when database access is attempted but DATABASE_URL is not set.

    A distinct type so the application can turn it into a 503 response rather
    than a generic 500. The message never contains credentials.
    """


def _require_database_url() -> str:
    """Return the configured database URL, or fail with a credential-free error."""
    settings = get_settings()
    if settings.database_url is None:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is not configured. Set it in the root .env file "
            "(see .env.example). There is no fallback database."
        )
    return str(settings.database_url)


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, created on first use.

    Created lazily so that importing the application does not require a
    reachable database — the plain /health endpoint stays useful either way.
    """
    return create_async_engine(_require_database_url(), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a database session per request.

    The session is closed when the request ends. Committing is the caller's
    responsibility, so a request that only reads never opens a write transaction.
    """
    async with get_sessionmaker()() as session:
        yield session


async def dispose_engine() -> None:
    """Close the connection pool, on application shutdown.

    Checks the cache rather than calling get_engine(), so shutting down never
    creates an engine that was never used.
    """
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
