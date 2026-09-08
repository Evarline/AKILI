"""Sealing per-request OAuth secrets at rest.

Fernet (AES-128-CBC + HMAC-SHA256, versioned, with a timestamp) from
`cryptography`, keyed by OAUTH_ENCRYPTION_KEY. Today this seals the PKCE code
verifier while an authorization request is in flight; a later phase seals
access tokens with the same box. A database read alone therefore yields no
usable secret — the key lives only in the backend's environment.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.oauth.errors import OAuthNotConfiguredError


class SealedValueError(ValueError):
    """The ciphertext could not be opened: wrong key, tampered, or not ours."""


class SecretBox:
    """Symmetric seal/open for short secrets. Holds the key; never exposes it."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def seal(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def open(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise SealedValueError("ciphertext could not be opened") from exc

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return "SecretBox(<key hidden>)"


def get_secret_box() -> SecretBox:
    """FastAPI dependency: the box keyed from settings. Overridable in tests."""
    key = get_settings().oauth_encryption_key
    if key is None:
        raise OAuthNotConfiguredError("OAUTH_ENCRYPTION_KEY is not configured")
    return SecretBox(key.get_secret_value())
