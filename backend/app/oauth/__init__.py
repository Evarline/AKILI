"""Provider-neutral OAuth 2.1 client infrastructure.

Phase 6.2 scope: everything needed to *start* an authorization-code flow as a
public client identified by a Client ID Metadata Document — discovery of the
authorization server from an MCP server URL, PKCE (S256), the authorization
URL, and sealing per-request secrets at rest. Nothing here exchanges a code,
handles a callback, or stores a token; those arrive in a later phase.

Nothing in this package is Binance-specific. The Binance adapter in
`app/binance/` composes these pieces with AKILI's settings and identity.

The metadata models, discovery URL rules, PKCE generator, and resource-URL
helpers come from the official MCP Python SDK (`mcp`), so AKILI follows the MCP
authorization specification by construction rather than by re-implementation.
The SDK's *interactive* OAuth provider is deliberately not used: it expects to
block inside one HTTP call until the user finishes in a browser, which does not
fit a web backend where the redirect and the callback are separate requests.
"""

from app.oauth.authorization import AuthorizationRequestParams, build_authorization_url
from app.oauth.crypto import SealedValueError, SecretBox, get_secret_box
from app.oauth.discovery import AuthorizationServer, discover
from app.oauth.errors import OAuthDiscoveryError, OAuthError, OAuthNotConfiguredError
from app.oauth.pkce import PKCEPair, generate_pkce, generate_state

__all__ = [
    "AuthorizationRequestParams",
    "AuthorizationServer",
    "OAuthDiscoveryError",
    "OAuthError",
    "OAuthNotConfiguredError",
    "PKCEPair",
    "SealedValueError",
    "SecretBox",
    "build_authorization_url",
    "discover",
    "generate_pkce",
    "generate_state",
    "get_secret_box",
]
