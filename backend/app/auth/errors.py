"""Identity errors. `main.py` maps them to HTTP responses; messages hold no secrets."""


class AuthError(Exception):
    """Base for identity failures."""

    error_class: str = "AUTH_ERROR"


class NotAuthenticatedError(AuthError):
    """No principal could be resolved, or it names no active user.

    One error for every case on purpose: the response never distinguishes
    "unknown user" from "disabled user" from "no credentials", so nothing about
    the user table is enumerable from the outside.
    """

    error_class = "NOT_AUTHENTICATED"


class DevelopmentAuthForbiddenError(AuthError):
    """A DEVELOPMENT-origin user reached the dependency outside APP_ENV=development.

    Settings already refuse to start in that state; this is the second,
    independent guard at the point where the user row is read. It should never
    fire. If it does, it is logged as a security event and the request is
    refused without serving anyone.
    """

    error_class = "DEVELOPMENT_AUTH_FORBIDDEN"
