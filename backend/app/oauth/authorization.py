"""Building the authorization request URL (OAuth 2.1 authorization-code + PKCE)."""

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit


@dataclass(frozen=True, slots=True)
class AuthorizationRequestParams:
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    resource: str


def build_authorization_url(authorization_endpoint: str, params: AuthorizationRequestParams) -> str:
    """The URL the user's browser is sent to.

    Parameters, and why each is present:
    - response_type=code, code_challenge, code_challenge_method=S256: the
      authorization-code flow with PKCE that OAuth 2.1 and MCP require.
    - client_id: AKILI's Client ID Metadata Document URL.
    - redirect_uri: must be listed in that document.
    - state: binds the callback to the persisted request and its owner.
    - resource: RFC 8707 indicator naming the MCP server (MCP requires it in
      both the authorization and the token request).

    Deliberately absent: `scope`. Binance publishes no `scopes_supported` and
    sends no `scope` challenge, and the MCP spec says to omit the parameter in
    that case; the user chooses scopes on Binance's consent screen.
    """
    query = urlencode(
        {
            "response_type": "code",
            "client_id": params.client_id,
            "redirect_uri": params.redirect_uri,
            "state": params.state,
            "code_challenge": params.code_challenge,
            "code_challenge_method": "S256",
            "resource": params.resource,
        }
    )
    separator = "&" if urlsplit(authorization_endpoint).query else "?"
    return f"{authorization_endpoint}{separator}{query}"
