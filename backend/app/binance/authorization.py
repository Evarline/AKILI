"""Starting a Binance authorization for one AKILI user.

`begin_authorization` composes the provider-neutral pieces in `app/oauth` with
AKILI's settings and identity:

1. Discover Binance's authorization server from the configured MCP server URL.
2. Refuse unless it supports Client ID Metadata Documents — AKILI has no client
   secret and no pre-registration, so CIMD is the only way it can be a client.
3. Generate PKCE and `state`.
4. Persist the request, owned by the calling user, with the verifier sealed
   and the expected issuer recorded, before any redirect happens.
5. Return the authorization URL for the browser.

Logging here names the user and the expiry only. The state, the verifier, the
challenge, and the full URL are never logged.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx2
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import CurrentUser
from app.core.config import Settings
from app.db.models import OAuthAuthorizationRequest
from app.oauth.authorization import AuthorizationRequestParams, build_authorization_url
from app.oauth.crypto import SecretBox
from app.oauth.discovery import discover
from app.oauth.errors import OAuthDiscoveryError, OAuthNotConfiguredError
from app.oauth.pkce import generate_pkce, generate_state

logger = logging.getLogger(__name__)

PROVIDER = "binance"
# A user has this long to finish on Binance's side before the request is void.
AUTHORIZATION_REQUEST_TTL = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class StartedAuthorization:
    authorization_url: str
    expires_at: datetime


async def begin_authorization(
    session: AsyncSession,
    user: CurrentUser,
    *,
    settings: Settings,
    http_client: httpx2.AsyncClient,
    box: SecretBox,
) -> StartedAuthorization:
    """Create an authorization request owned by `user` and return where to send them."""
    if not (settings.binance_mcp_server_url and settings.binance_cimd_url and settings.binance_redirect_uri):
        # Settings validation makes this unreachable when the flag is on; kept
        # so the function is safe to call directly.
        raise OAuthNotConfiguredError("Binance OAuth settings are incomplete")

    server = await discover(settings.binance_mcp_server_url, http_client)
    if not server.client_id_metadata_document_supported:
        raise OAuthDiscoveryError(
            "authorization server does not support Client ID Metadata Documents; "
            "AKILI has no other way to identify itself as a client"
        )

    pkce = generate_pkce()
    state = generate_state()
    expires_at = datetime.now(UTC) + AUTHORIZATION_REQUEST_TTL

    session.add(
        OAuthAuthorizationRequest(
            state=state,
            user_id=user.id,
            provider=PROVIDER,
            client_id=settings.binance_cimd_url,
            redirect_uri=settings.binance_redirect_uri,
            resource=server.resource,
            expected_issuer=server.issuer,
            code_verifier_ciphertext=box.seal(pkce.code_verifier),
            expires_at=expires_at,
        )
    )
    await session.commit()

    url = build_authorization_url(
        server.authorization_endpoint,
        AuthorizationRequestParams(
            client_id=settings.binance_cimd_url,
            redirect_uri=settings.binance_redirect_uri,
            state=state,
            code_challenge=pkce.code_challenge,
            resource=server.resource,
        ),
    )
    logger.info(
        "binance authorization started for user %s (expires %s)", user.id, expires_at.isoformat()
    )
    return StartedAuthorization(authorization_url=url, expires_at=expires_at)
