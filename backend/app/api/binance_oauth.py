"""GET /api/v1/binance/connect — start AKILI's own Binance authorization.

Phase 6.2 ends at the redirect. The callback route that receives `code` and
`state`, the token exchange, and token storage are a later phase.
"""

from collections.abc import AsyncGenerator

import httpx2
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.binance.authorization import begin_authorization
from app.core.config import get_settings
from app.db.session import get_db
from app.oauth.crypto import SecretBox, get_secret_box

router = APIRouter(prefix="/api/v1/binance", tags=["binance"])


def require_binance_oauth_enabled() -> None:
    """While the feature is off, the route does not exist as far as callers can tell."""
    if not get_settings().binance_oauth_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")


async def get_oauth_http_client() -> AsyncGenerator[httpx2.AsyncClient]:
    """HTTP client for unauthenticated metadata discovery. Overridden in tests."""
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(10.0), follow_redirects=False) as client:
        yield client


@router.get(
    "/connect",
    # Feature gate first: a disabled feature is a 404 for everyone, before identity.
    dependencies=[Depends(require_binance_oauth_enabled)],
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
    summary="Redirect the browser to Binance to authorize AKILI",
)
async def connect(
    # The owner of the authorization request comes from identity, never from the
    # request: there are no parameters on this route.
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    http_client: httpx2.AsyncClient = Depends(get_oauth_http_client),
    box: SecretBox = Depends(get_secret_box),
) -> RedirectResponse:
    started = await begin_authorization(
        session, current_user, settings=get_settings(), http_client=http_client, box=box
    )
    # The URL carries `state` and the PKCE challenge: never cache it.
    return RedirectResponse(
        started.authorization_url,
        status_code=status.HTTP_302_FOUND,
        headers={"cache-control": "no-store"},
    )
