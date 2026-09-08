"""GET /.well-known/akili-mcp-client.json — AKILI's OAuth Client ID Metadata Document.

This public document *is* AKILI's client identity towards Binance: the URL it is
served at is the `client_id`, and the document must state that same URL as its
`client_id` (OAuth Client ID Metadata Document draft; MCP client registration).
Binance fetches it during authorization to learn AKILI's name and to check that
the `redirect_uri` in the request is one AKILI declared.

Everything in it is public by design. It contains no secret — AKILI is a public
client (`token_endpoint_auth_method: none`) — and it is generated from settings,
so it can never disagree with the URL it lives at (settings validation enforces
that BINANCE_CIMD_URL ends in this exact path). While Binance OAuth is disabled
the route answers 404, so a deployment that has not opted in publishes nothing.
"""

from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict

from app.core.config import CIMD_PATH, get_settings

router = APIRouter(tags=["oauth-client"])

# Binance may cache the document; an hour keeps redirect_uri changes reasonably
# quick to propagate while sparing a fetch per authorization.
CACHE_CONTROL = "public, max-age=3600"


class ClientMetadataDocument(BaseModel):
    """The fields AKILI publishes. Names are the RFC 7591 / CIMD wire names."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    client_name: str
    client_uri: str
    redirect_uris: list[str]
    grant_types: list[str] = ["authorization_code"]
    response_types: list[str] = ["code"]
    token_endpoint_auth_method: str = "none"


@router.get(CIMD_PATH, response_model=ClientMetadataDocument)
async def client_metadata(response: Response) -> ClientMetadataDocument:
    settings = get_settings()
    if not settings.binance_oauth_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    # Guaranteed by settings validation when the flag is on; asserted for typing.
    assert settings.binance_cimd_url is not None and settings.binance_redirect_uri is not None

    origin = urlsplit(settings.binance_cimd_url)
    response.headers["cache-control"] = CACHE_CONTROL
    return ClientMetadataDocument(
        client_id=settings.binance_cimd_url,
        client_name=settings.app_name,
        client_uri=urlunsplit((origin.scheme, origin.netloc, "/", "", "")),
        redirect_uris=[settings.binance_redirect_uri],
    )
