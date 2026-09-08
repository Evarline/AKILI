"""Application configuration, loaded from the single root .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import Fernet
from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthMode = Literal["disabled", "development_fixed_user"]

# Interfaces a development-only identity may be served on. Anything else means
# the process is reachable from other machines, where a fixed user is a hole.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# Where AKILI publishes its OAuth Client ID Metadata Document (CIMD). The
# client_id Binance sees is BINANCE_CIMD_URL, and the CIMD standard requires the
# document to state that same URL as its client_id — so BINANCE_CIMD_URL must be
# an HTTPS URL ending in exactly this path, or the document would describe a
# client other than itself.
CIMD_PATH = "/.well-known/akili-mcp-client.json"

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


def mask_dsn(dsn: PostgresDsn | str) -> str:
    """Return a connection URL with the password removed.

    Use this anywhere a database URL might reach a log line, an error message,
    or an API response. Never format a raw DSN into user-facing output.
    """
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(str(dsn))
    if parts.password is None:
        return str(dsn)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{parts.username}:***@{host}" if parts.username else f"***@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class Settings(BaseSettings):
    """Backend settings.

    Application fields have development-safe defaults, so the service starts with
    no .env file and no credentials. Database URLs deliberately have no default:
    there is no silent fallback to a local or in-memory database, so a missing
    DATABASE_URL surfaces as a clear error at the point of use rather than as a
    connection to the wrong place.

    Values are read from the process environment first, then from the root .env.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        # The root .env is shared with future components and already carries keys
        # this phase does not own (LLM, Binance). Ignore them rather than
        # failing to start.
        extra="ignore",
        # .env.example ships blank values such as `DATABASE_URL=`. Treat a blank
        # as "unset" so it falls back to the field default (None) and fails at
        # the point of use with a clear message, instead of a URL-parsing error
        # that would stop even the plain /health endpoint from starting.
        env_ignore_empty=True,
    )

    app_name: str = "AKILI"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    # Where the server is meant to listen. Not used to bind (uvicorn does that);
    # it is the declared intent that the identity guard below checks against.
    backend_host: str = "127.0.0.1"

    # Identity. This is NOT production authentication — see app/auth/.
    # "disabled" (the default) means every route that requires a user answers
    # 401, so a fresh deployment exposes nothing until someone chooses a mode.
    # "development_fixed_user" serves every request as one pre-seeded user and
    # is only constructible in APP_ENV=development on a loopback host.
    auth_mode: AuthMode = "disabled"
    dev_fixed_user_id: UUID | None = None

    # PostgreSQL. Must use the asyncpg driver: database access is async.
    database_url: PostgresDsn | None = None
    # Separate database for the test suite, so tests never touch development data.
    test_database_url: PostgresDsn | None = None

    # Runtime LLM. The provider and model are configuration, never code: no model
    # name is hard-coded anywhere in the repository. The key is a SecretStr so it
    # is masked in repr(), logs, and error messages; it is handed only to the
    # provider SDK client and is never part of any prompt.
    llm_provider: Literal["google"] = "google"
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = 60.0
    llm_max_output_tokens: int = 4096

    # How many recent messages of a conversation are sent to the model. The
    # window is bounded on purpose: history is never appended forever.
    agent_history_messages: int = 10

    # Binance Spot REST credentials. These are server-side only and are never
    # included in an LLM request or returned by an API route.
    binance_api_key: str | None = None
    binance_api_secret: SecretStr | None = None
    binance_use_testnet: bool = False

    # Binance Agentic MCP — AKILI's OWN OAuth client (Phase 6). Off by default:
    # while disabled, the CIMD document and the connect route both answer 404.
    # The URLs are plain strings, not URL types, so the value Binance receives as
    # client_id is byte-for-byte what was configured (no normalisation). Nothing
    # here is a Binance credential; AKILI is a public OAuth client with no secret.
    binance_oauth_enabled: bool = False
    binance_mcp_server_url: str | None = None  # e.g. https://agent.binance.com/mcp/agentic
    binance_cimd_url: str | None = None  # https://<akili-host>/.well-known/akili-mcp-client.json
    binance_redirect_uri: str | None = None  # https://<akili-host>/api/v1/binance/oauth/callback
    # Fernet key sealing per-request OAuth secrets at rest (PKCE verifier now,
    # tokens in a later phase). SECRET. Generate with
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    oauth_encryption_key: SecretStr | None = None

    @model_validator(mode="after")
    def _binance_oauth_configuration_is_complete(self) -> "Settings":
        """With Binance OAuth enabled, every piece must be present and coherent.

        Checked at startup rather than at the first click, so a half-configured
        client can never send Binance a client_id that does not match its own
        document, or a redirect the flow cannot receive.
        """
        if not self.binance_oauth_enabled:
            return self

        required = {
            "BINANCE_MCP_SERVER_URL": self.binance_mcp_server_url,
            "BINANCE_CIMD_URL": self.binance_cimd_url,
            "BINANCE_REDIRECT_URI": self.binance_redirect_uri,
            "OAUTH_ENCRYPTION_KEY": self.oauth_encryption_key,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ValueError(f"BINANCE_OAUTH_ENABLED=true requires {', '.join(missing)}")

        mcp = urlsplit(self.binance_mcp_server_url or "")
        if mcp.scheme != "https" or not mcp.netloc or mcp.fragment:
            raise ValueError("BINANCE_MCP_SERVER_URL must be an https URL without a fragment")

        cimd = urlsplit(self.binance_cimd_url or "")
        if cimd.scheme != "https" or not cimd.netloc or cimd.query or cimd.fragment:
            raise ValueError("BINANCE_CIMD_URL must be a plain https URL (no query or fragment)")
        if cimd.path != CIMD_PATH:
            raise ValueError(
                f"BINANCE_CIMD_URL must end in {CIMD_PATH} (got path {cimd.path!r}): the document "
                "served there must name itself as client_id"
            )

        redirect = urlsplit(self.binance_redirect_uri or "")
        loopback_http = redirect.scheme == "http" and redirect.hostname in LOOPBACK_HOSTS
        if not ((redirect.scheme == "https" and redirect.netloc) or loopback_http):
            raise ValueError(
                "BINANCE_REDIRECT_URI must be https, or http on a loopback host for development"
            )
        if not redirect.path or redirect.path == "/" or redirect.fragment:
            raise ValueError("BINANCE_REDIRECT_URI must have a path and no fragment")

        try:
            Fernet(self.oauth_encryption_key.get_secret_value().encode())  # type: ignore[union-attr]
        except (ValueError, TypeError) as exc:
            # Never echo the key. The generation command is in the field comment.
            raise ValueError("OAUTH_ENCRYPTION_KEY is not a valid Fernet key") from exc
        return self

    @model_validator(mode="after")
    def _development_identity_only_in_development(self) -> "Settings":
        """Refuse to build settings that would serve a fixed user outside development.

        Raising here means the process never starts (main.py reads settings at
        import), which is the intended failure mode: loud, before any request.
        """
        if self.auth_mode != "development_fixed_user":
            return self
        if self.app_env != "development":
            raise ValueError(
                "AUTH_MODE=development_fixed_user is only allowed with APP_ENV=development "
                f"(got APP_ENV={self.app_env!r}). Development identity is not authentication."
            )
        if self.backend_host not in LOOPBACK_HOSTS:
            raise ValueError(
                "AUTH_MODE=development_fixed_user requires BACKEND_HOST to be a loopback "
                f"address (got {self.backend_host!r}); a fixed user must not be reachable "
                "from other machines."
            )
        if self.dev_fixed_user_id is None:
            raise ValueError(
                "AUTH_MODE=development_fixed_user requires DEV_FIXED_USER_ID (a UUID you "
                "choose once; seed it with `python -m app.auth.seed`)."
            )
        return self

    @property
    def safe_database_url(self) -> str:
        """The development database URL with its password masked, for logging."""
        return mask_dsn(self.database_url) if self.database_url else "<unset>"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, reading the environment only once per process."""
    return Settings()
