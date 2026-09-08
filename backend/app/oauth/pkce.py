"""PKCE (RFC 7636) and `state` generation.

Both values are produced here and nowhere else, using the MCP SDK's generator
for PKCE so the verifier length and S256 challenge are exactly what the MCP
authorization specification requires. The verifier is a secret until the code
exchange; `PKCEPair` hides it from `repr()` so it cannot leak through a log
line that formats the object.
"""

import secrets
from dataclasses import dataclass, field
from typing import Literal

from mcp.client.auth.oauth2 import PKCEParameters

CodeChallengeMethod = Literal["S256"]

# 32 random bytes → 43 URL-safe characters. Unguessable and unique in practice.
STATE_BYTES = 32


@dataclass(frozen=True, slots=True)
class PKCEPair:
    code_verifier: str = field(repr=False)
    code_challenge: str
    method: CodeChallengeMethod = "S256"


def generate_pkce() -> PKCEPair:
    """A fresh verifier and its S256 challenge. Never reuse a pair."""
    params = PKCEParameters.generate()
    return PKCEPair(code_verifier=params.code_verifier, code_challenge=params.code_challenge)


def generate_state() -> str:
    """A fresh, unguessable `state` value that also keys the persisted request."""
    return secrets.token_urlsafe(STATE_BYTES)
