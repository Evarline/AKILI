"""Provider-neutral OAuth infrastructure: settings, PKCE, URL building, sealing,
and discovery against a fake authorization server. No database, no network.

The fake server reproduces exactly what Binance's live metadata endpoints
returned during the Phase 6.1 investigation, so discovery is tested against
the real shape (path-based PRM 404, root PRM 200, ASM 200, OIDC 404).
"""

import asyncio
import base64
import hashlib
import json
from dataclasses import asdict
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from app.core.config import CIMD_PATH, Settings
from app.oauth.authorization import AuthorizationRequestParams, build_authorization_url
from app.oauth.crypto import SealedValueError, SecretBox
from app.oauth.discovery import discover
from app.oauth.errors import OAuthDiscoveryError
from app.oauth.pkce import PKCEPair, generate_pkce, generate_state

MCP_URL = "https://agent.binance.com/mcp/agentic"
CIMD_URL = f"https://akili.example.test{CIMD_PATH}"
REDIRECT_URI = "https://akili.example.test/api/v1/binance/oauth/callback"

# Verbatim shapes observed live on 2026-09-06.
BINANCE_PRM = {
    "resource": "https://agent.binance.com/mcp/agentic",
    "authorization_servers": ["https://agent.binance.com"],
}
BINANCE_ASM = {
    "issuer": "https://agent.binance.com",
    "authorization_endpoint": "https://accounts.binance.com/agentic-oauth/authorize",
    "token_endpoint": "https://accounts.binance.com/oauth-agentic/token",
    "token_endpoint_auth_methods_supported": ["none"],
    "response_types_supported": ["code"],
    "grant_types_supported": ["authorization_code"],
    "code_challenge_methods_supported": ["S256"],
    "client_id_metadata_document_supported": True,
}

BINANCE_ENV_VARS = (
    "BINANCE_OAUTH_ENABLED",
    "BINANCE_MCP_SERVER_URL",
    "BINANCE_CIMD_URL",
    "BINANCE_REDIRECT_URI",
    "OAUTH_ENCRYPTION_KEY",
)


def fernet_key() -> str:
    return Fernet.generate_key().decode()


def make_binance_transport(
    prm: dict[str, Any] | None = BINANCE_PRM,
    asm: dict[str, Any] | None = BINANCE_ASM,
    *,
    fail_with: Exception | None = None,
) -> httpx2.MockTransport:
    """A fake agent.binance.com serving the two metadata documents."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if fail_with is not None:
            raise fail_with
        url = str(request.url)
        if url == "https://agent.binance.com/.well-known/oauth-protected-resource" and prm is not None:
            return httpx2.Response(200, json=prm)
        if url == "https://agent.binance.com/.well-known/oauth-authorization-server" and asm is not None:
            return httpx2.Response(200, json=asm)
        return httpx2.Response(404, text="Can not found routing,please contact the administrator")

    return httpx2.MockTransport(handler)


def run_discover(transport: httpx2.MockTransport, server_url: str = MCP_URL):
    async def go():
        async with httpx2.AsyncClient(transport=transport) as client:
            return await discover(server_url, client)

    return asyncio.run(go())


# --------------------------------------------------------------------------- #
# Settings                                                                     #
# --------------------------------------------------------------------------- #


@pytest.fixture
def clean_binance_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in BINANCE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def make_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def enabled_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "binance_oauth_enabled": True,
        "binance_mcp_server_url": MCP_URL,
        "binance_cimd_url": CIMD_URL,
        "binance_redirect_uri": REDIRECT_URI,
        "oauth_encryption_key": SecretStr(fernet_key()),
    }
    values.update(overrides)
    return make_settings(**values)


def test_binance_oauth_is_disabled_by_default_and_needs_nothing(clean_binance_env: None) -> None:
    s = make_settings()
    assert s.binance_oauth_enabled is False
    assert s.binance_cimd_url is None and s.oauth_encryption_key is None


def test_enabled_binance_oauth_accepts_a_complete_configuration(clean_binance_env: None) -> None:
    s = enabled_settings()
    assert s.binance_cimd_url == CIMD_URL  # byte-for-byte, no URL normalisation


@pytest.mark.parametrize(
    "missing", ["binance_mcp_server_url", "binance_cimd_url", "binance_redirect_uri", "oauth_encryption_key"]
)
def test_enabled_binance_oauth_requires_every_setting(clean_binance_env: None, missing: str) -> None:
    with pytest.raises(ValidationError, match="BINANCE_OAUTH_ENABLED=true requires"):
        enabled_settings(**{missing: None})


@pytest.mark.parametrize(
    "bad_cimd",
    [
        "https://akili.example.test/client.json",  # wrong path: document would not name itself
        f"http://akili.example.test{CIMD_PATH}",  # not https
        f"https://akili.example.test{CIMD_PATH}?v=1",  # query
    ],
)
def test_cimd_url_must_be_https_at_the_served_path(clean_binance_env: None, bad_cimd: str) -> None:
    with pytest.raises(ValidationError, match="BINANCE_CIMD_URL"):
        enabled_settings(binance_cimd_url=bad_cimd)


@pytest.mark.parametrize(
    "bad_redirect",
    ["http://akili.example.test/cb", "https://akili.example.test", "https://akili.example.test/cb#frag"],
)
def test_redirect_uri_must_be_https_or_loopback_with_a_path(clean_binance_env: None, bad_redirect: str) -> None:
    with pytest.raises(ValidationError, match="BINANCE_REDIRECT_URI"):
        enabled_settings(binance_redirect_uri=bad_redirect)


def test_loopback_http_redirect_is_allowed_for_development(clean_binance_env: None) -> None:
    s = enabled_settings(binance_redirect_uri="http://127.0.0.1:8000/api/v1/binance/oauth/callback")
    assert s.binance_redirect_uri.startswith("http://127.0.0.1")


def test_encryption_key_must_be_a_fernet_key_and_is_never_echoed(clean_binance_env: None) -> None:
    with pytest.raises(ValidationError) as excinfo:
        enabled_settings(oauth_encryption_key=SecretStr("not-a-key-CANARY"))
    assert "not a valid Fernet key" in str(excinfo.value)
    assert "CANARY" not in str(excinfo.value)


# --------------------------------------------------------------------------- #
# PKCE and state                                                               #
# --------------------------------------------------------------------------- #


def s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def test_pkce_is_s256_over_a_valid_verifier() -> None:
    pair = generate_pkce()
    assert pair.method == "S256"
    assert 43 <= len(pair.code_verifier) <= 128  # RFC 7636 §4.1
    assert set(pair.code_verifier) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    )
    assert pair.code_challenge == s256(pair.code_verifier)
    assert "=" not in pair.code_challenge


def test_pkce_pairs_are_unique_and_the_verifier_is_hidden_from_repr() -> None:
    a, b = generate_pkce(), generate_pkce()
    assert a.code_verifier != b.code_verifier
    assert a.code_verifier not in repr(a)
    assert a.code_challenge in repr(a)
    assert isinstance(a, PKCEPair)


def test_state_is_long_random_and_url_safe() -> None:
    states = {generate_state() for _ in range(50)}
    assert len(states) == 50
    for state in states:
        assert len(state) >= 43
        assert set(state) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


# --------------------------------------------------------------------------- #
# Authorization URL                                                            #
# --------------------------------------------------------------------------- #


def params() -> AuthorizationRequestParams:
    return AuthorizationRequestParams(
        client_id=CIMD_URL,
        redirect_uri=REDIRECT_URI,
        state="STATE",
        code_challenge="CHALLENGE",
        resource=MCP_URL,
    )


def test_authorization_url_has_exactly_the_required_parameters_and_no_scope() -> None:
    url = build_authorization_url(BINANCE_ASM["authorization_endpoint"], params())

    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == BINANCE_ASM["authorization_endpoint"]
    query = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
    assert query == {
        "response_type": ["code"],
        "client_id": [CIMD_URL],
        "redirect_uri": [REDIRECT_URI],
        "state": ["STATE"],
        "code_challenge": ["CHALLENGE"],
        "code_challenge_method": ["S256"],
        "resource": [MCP_URL],
    }
    assert "scope" not in query


def test_authorization_url_appends_to_an_endpoint_that_already_has_a_query() -> None:
    url = build_authorization_url("https://as.example/authorize?tenant=x", params())
    query = parse_qs(urlsplit(url).query)
    assert query["tenant"] == ["x"] and query["response_type"] == ["code"]


# --------------------------------------------------------------------------- #
# Sealing                                                                      #
# --------------------------------------------------------------------------- #


def test_secret_box_round_trips_and_rejects_other_keys() -> None:
    box = SecretBox(fernet_key())
    sealed = box.seal("verifier-CANARY")

    assert b"verifier-CANARY" not in sealed
    assert box.open(sealed) == "verifier-CANARY"
    with pytest.raises(SealedValueError):
        SecretBox(fernet_key()).open(sealed)
    assert "CANARY" not in repr(box)


# --------------------------------------------------------------------------- #
# Discovery                                                                    #
# --------------------------------------------------------------------------- #


def test_discovery_against_the_binance_shaped_server() -> None:
    server = run_discover(make_binance_transport())

    assert server.issuer == "https://agent.binance.com"
    assert server.authorization_endpoint == "https://accounts.binance.com/agentic-oauth/authorize"
    assert server.token_endpoint == "https://accounts.binance.com/oauth-agentic/token"
    assert server.resource == "https://agent.binance.com/mcp/agentic"
    assert server.client_id_metadata_document_supported is True
    assert server.code_challenge_methods_supported == ("S256",)


def test_discovery_fails_without_protected_resource_metadata() -> None:
    with pytest.raises(OAuthDiscoveryError, match="protected resource metadata"):
        run_discover(make_binance_transport(prm=None))


def test_discovery_fails_without_authorization_server_metadata() -> None:
    with pytest.raises(OAuthDiscoveryError, match="authorization server metadata"):
        run_discover(make_binance_transport(asm=None))


def test_discovery_rejects_an_issuer_that_does_not_match_where_it_was_found() -> None:
    asm = {**BINANCE_ASM, "issuer": "https://evil.example"}
    with pytest.raises(OAuthDiscoveryError, match="issuer mismatch"):
        run_discover(make_binance_transport(asm=asm))


def test_discovery_rejects_a_resource_for_a_different_server() -> None:
    prm = {**BINANCE_PRM, "resource": "https://agent.binance.com/other"}
    with pytest.raises(OAuthDiscoveryError, match="different resource"):
        run_discover(make_binance_transport(prm=prm))


def test_discovery_requires_s256() -> None:
    asm = {**BINANCE_ASM, "code_challenge_methods_supported": ["plain"]}
    with pytest.raises(OAuthDiscoveryError, match="S256"):
        run_discover(make_binance_transport(asm=asm))


def test_discovery_reports_missing_cimd_support_instead_of_assuming_it() -> None:
    asm = {k: v for k, v in BINANCE_ASM.items() if k != "client_id_metadata_document_supported"}
    server = run_discover(make_binance_transport(asm=asm))
    assert server.client_id_metadata_document_supported is False


def test_discovery_turns_network_failure_into_a_discovery_error() -> None:
    with pytest.raises(OAuthDiscoveryError):
        run_discover(make_binance_transport(fail_with=httpx2.ConnectError("boom")))


def test_discovery_result_carries_no_mcp_types() -> None:
    """The rest of the app consumes plain Python: strings, a bool, a tuple."""
    server = run_discover(make_binance_transport())
    for value in (server.issuer, server.authorization_endpoint, server.token_endpoint, server.resource):
        assert type(value) is str
    json.dumps(asdict(server))  # serialisable without any pydantic/mcp knowledge
