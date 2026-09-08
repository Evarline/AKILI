"""Authorization-server discovery for an MCP server (MCP authorization spec).

Two documents, fetched with the URL rules the MCP SDK implements:

1. Protected Resource Metadata (RFC 9728) at the MCP server's origin — which
   `resource` the server is, and which authorization server(s) protect it.
2. Authorization Server Metadata (RFC 8414) at that authorization server —
   endpoints and capabilities. The `issuer` it states must equal the URL it was
   discovered from, otherwise the document is rejected.

The result is a small frozen value the rest of the application can use without
importing any `mcp` type. Discovery is read-only and unauthenticated.
"""

import logging
from dataclasses import dataclass

import httpx2
from mcp.client.auth.exceptions import OAuthFlowError
from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    build_protected_resource_metadata_discovery_urls,
    validate_metadata_issuer,
)
from mcp.shared.auth import OAuthMetadata, ProtectedResourceMetadata
from mcp.shared.auth_utils import check_resource_allowed, resource_url_from_server_url
from pydantic import ValidationError

from app.oauth.errors import OAuthDiscoveryError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuthorizationServer:
    """What AKILI needs to know to send a user to authorize."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    # RFC 8707 resource indicator to send: the MCP server's canonical URL, or
    # the PRM's `resource` when it is a valid parent of it (same rule as the SDK).
    resource: str
    client_id_metadata_document_supported: bool
    code_challenge_methods_supported: tuple[str, ...]


async def discover(server_url: str, client: httpx2.AsyncClient) -> AuthorizationServer:
    """Discover the authorization server protecting `server_url`, or raise.

    Raises:
        OAuthDiscoveryError: no usable metadata, issuer mismatch, resource
            mismatch, or an authorization server AKILI cannot work with.
    """
    prm = await _discover_protected_resource(server_url, client)
    auth_server_url = str(prm.authorization_servers[0])
    asm = await _discover_authorization_server(auth_server_url, server_url, client)

    canonical = resource_url_from_server_url(server_url)
    prm_resource = str(prm.resource)
    if not check_resource_allowed(requested_resource=canonical, configured_resource=prm_resource):
        raise OAuthDiscoveryError("protected resource metadata names a different resource")

    methods = tuple(asm.code_challenge_methods_supported or ())
    if methods and "S256" not in methods:
        raise OAuthDiscoveryError("authorization server does not support PKCE S256")
    if "code" not in asm.response_types_supported:
        raise OAuthDiscoveryError("authorization server does not support the code response type")

    return AuthorizationServer(
        issuer=str(asm.issuer),
        authorization_endpoint=str(asm.authorization_endpoint),
        token_endpoint=str(asm.token_endpoint),
        resource=prm_resource,
        client_id_metadata_document_supported=asm.client_id_metadata_document_supported is True,
        code_challenge_methods_supported=methods,
    )


async def _get(client: httpx2.AsyncClient, url: str) -> httpx2.Response | None:
    """GET a metadata document. Network failure is a discovery failure, not a crash."""
    try:
        return await client.get(url, headers={"accept": "application/json"})
    except httpx2.HTTPError as exc:
        logger.warning("metadata request failed: %s (%s)", url, type(exc).__name__)
        return None


async def _discover_protected_resource(
    server_url: str, client: httpx2.AsyncClient
) -> ProtectedResourceMetadata:
    # Path-based well-known URI first, then root — the spec's fallback order.
    for url in build_protected_resource_metadata_discovery_urls(None, server_url):
        response = await _get(client, url)
        if response is None or response.status_code != 200:
            continue
        try:
            return ProtectedResourceMetadata.model_validate_json(response.content)
        except ValidationError:
            logger.warning("invalid protected resource metadata at %s", url)
    raise OAuthDiscoveryError("no protected resource metadata found for the MCP server")


async def _discover_authorization_server(
    auth_server_url: str, server_url: str, client: httpx2.AsyncClient
) -> OAuthMetadata:
    for url in build_oauth_authorization_server_metadata_discovery_urls(auth_server_url, server_url):
        response = await _get(client, url)
        if response is None or response.status_code != 200:
            continue
        try:
            metadata = OAuthMetadata.model_validate_json(response.content)
        except ValidationError:
            logger.warning("invalid authorization server metadata at %s", url)
            continue
        try:
            validate_metadata_issuer(metadata, auth_server_url)
        except OAuthFlowError as exc:
            raise OAuthDiscoveryError("authorization server metadata issuer mismatch") from exc
        return metadata
    raise OAuthDiscoveryError("no authorization server metadata found")
