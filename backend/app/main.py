"""AKILI backend application.

Scope so far: the FastAPI app, typed configuration, database plumbing, health
endpoints, the chat endpoint that has the runtime model interpret a user
message and answer a market question from public market data AKILI fetched for
it, a development-only identity mechanism that gives every conversation an
owner, and the start of AKILI's own Binance OAuth flow (client metadata document
and the redirect to Binance; no callback, tokens, or account access yet). There
is no real authentication, no planning, no approval, and no execution — see
docs/01-AGENT-CONTRACT.md for what later phases must implement.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.service import InvalidModelOutputError
from app.api.binance import router as binance_router
from app.api.binance_oauth import router as binance_oauth_router
from app.api.chat import router as chat_router
from app.api.client_metadata import router as client_metadata_router
from app.auth.errors import AuthError, DevelopmentAuthForbiddenError
from app.binance.exceptions import (
    BinanceAuthenticationError,
    BinanceRateLimitError,
    BinanceTimestampError,
    InvalidIntervalError,
    InvalidSymbolError,
    MarketDataError,
)
from app.core.config import get_settings
from app.db.session import DatabaseNotConfiguredError, dispose_engine, get_db
from app.llm.base import LLMConfigurationError, LLMError, LLMResponseError
from app.oauth.errors import OAuthError

logger = logging.getLogger(__name__)
# Reading settings at import is the fail-fast point: an invalid identity
# configuration (e.g. the development fixed user outside development) raises
# here and the process never starts.
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Manage resources tied to the application's lifetime.

    Nothing to set up: the engine is created lazily on first use, so startup
    does not require a reachable database. The active identity mode is logged
    so every deployment log states it plainly. On shutdown the connection pool
    is closed so PostgreSQL connections are not left dangling.
    """
    if settings.auth_mode == "development_fixed_user":
        logger.warning(
            "AUTH_MODE=development_fixed_user: every request is served as one fixed "
            "user. This is a DEVELOPMENT identity mechanism, not authentication."
        )
    else:
        logger.info("AUTH_MODE=%s: routes that require a user answer 401", settings.auth_mode)
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.exception_handler(DatabaseNotConfiguredError)
async def database_not_configured(
    _: Request, exc: DatabaseNotConfiguredError
) -> JSONResponse:
    """Answer 503 when the database is not configured, instead of a 500.

    The error is raised inside the get_db dependency, before any route body
    runs, so a try/except in a route cannot catch it. Handling it here covers
    every route that depends on the database, now and in later phases.
    """
    logger.error("%s", exc)  # the message names the setting, never a value
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database unavailable"},
    )


@app.exception_handler(AuthError)
async def auth_error(_: Request, exc: AuthError) -> JSONResponse:
    """Identity failures. One 401 for every "who are you" failure, so the
    response never reveals whether a user id exists or is disabled."""
    if isinstance(exc, DevelopmentAuthForbiddenError):
        # Already logged as a security event where it was detected.
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Authentication unavailable"},
        )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Not authenticated"},
    )


@app.exception_handler(LLMError)
async def llm_error(_: Request, exc: LLMError) -> JSONResponse:
    """Map provider failures to safe responses. Raw provider text never leaves.

    Configuration and availability problems are 503 (try later / fix deployment);
    an answer that came back unusable is 502. Nothing here is ever a 200.
    """
    logger.warning("LLM failure: %s", exc.error_class)
    if isinstance(exc, LLMResponseError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "The assistant returned an unusable response"},
        )
    if isinstance(exc, LLMConfigurationError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "The assistant is not configured"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The assistant is temporarily unavailable"},
    )


@app.exception_handler(InvalidModelOutputError)
async def invalid_model_output(_: Request, exc: InvalidModelOutputError) -> JSONResponse:
    """The model's answer failed AKILI's contract. Rejected, never repaired."""
    logger.warning("Model output rejected: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "The assistant returned an unusable response"},
    )


@app.exception_handler(MarketDataError)
async def market_data_error(_: Request, exc: MarketDataError) -> JSONResponse:
    """A read-only market-data call failed, so the turn failed.

    AKILI never continues on an estimate when a fetch fails (contract INV-16),
    and never repeats Binance's own error text: only the error class is logged.
    An unknown or unsupported market is the caller's answer to correct; anything
    else is a temporary unavailability.
    """
    logger.warning("Market data failure: %s", exc.error_class)
    if isinstance(exc, (InvalidSymbolError, InvalidIntervalError)):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "AKILI could not look up that market"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Market data is temporarily unavailable"},
    )


@app.exception_handler(BinanceAuthenticationError)
async def binance_authentication_error(_: Request, exc: BinanceAuthenticationError) -> JSONResponse:
    """Never expose Binance's credential or signature details."""
    logger.warning("Binance authentication failed: %s", exc.error_class)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "Binance rejected the configured API credentials"},
    )


@app.exception_handler(BinanceTimestampError)
async def binance_timestamp_error(_: Request, exc: BinanceTimestampError) -> JSONResponse:
    logger.warning("Binance timestamp rejected: %s", exc.error_class)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Binance rejected the request timestamp"},
    )


@app.exception_handler(BinanceRateLimitError)
async def binance_rate_limit_error(_: Request, exc: BinanceRateLimitError) -> JSONResponse:
    logger.warning("Binance rate limit reached: %s", exc.error_class)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Binance rate limit reached; try again later"},
    )


@app.exception_handler(OAuthError)
async def oauth_error(_: Request, exc: OAuthError) -> JSONResponse:
    """Binance authorization could not be started: discovery failed or the
    client is not configured. Only the error class is logged; nothing from the
    remote server or the configuration reaches the caller."""
    logger.warning("OAuth failure: %s", exc.error_class)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Binance authorization is unavailable"},
    )


app.include_router(chat_router)
app.include_router(binance_router)
app.include_router(binance_oauth_router)
app.include_router(client_metadata_router)


class HealthResponse(BaseModel):
    """Body returned by GET /health."""

    status: str
    version: str


class DatabaseHealthResponse(BaseModel):
    """Body returned by GET /health/db."""

    status: str
    database: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the service is up.

    Deliberately touches nothing external, so it stays fast and cannot fail for
    reasons unrelated to the process being alive.
    """
    return HealthResponse(status="ok", version=settings.app_version)


@app.get("/health/db", response_model=DatabaseHealthResponse)
async def health_db(session: AsyncSession = Depends(get_db)) -> DatabaseHealthResponse:
    """Report whether PostgreSQL is reachable, via a minimal SELECT 1.

    Kept separate from /health so that a database outage does not make the
    process itself look dead.
    """
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        # Log with the password masked, and tell the caller nothing about the
        # connection details or the underlying driver error.
        logger.warning(
            "Database health check failed for %s: %s",
            settings.safe_database_url,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return DatabaseHealthResponse(status="ok", database="reachable")
