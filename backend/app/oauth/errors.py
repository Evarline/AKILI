"""OAuth infrastructure errors. Messages never contain secrets or remote payloads."""


class OAuthError(Exception):
    """Base for OAuth client failures. `main.py` maps these to a 503."""

    error_class: str = "OAUTH_ERROR"


class OAuthNotConfiguredError(OAuthError):
    """A required OAuth setting is absent. A deployment problem, not a user one."""

    error_class = "OAUTH_NOT_CONFIGURED"


class OAuthDiscoveryError(OAuthError):
    """The authorization server could not be discovered, or its metadata is
    unusable for AKILI (no CIMD support, no S256, resource mismatch, ...)."""

    error_class = "OAUTH_DISCOVERY_FAILED"
