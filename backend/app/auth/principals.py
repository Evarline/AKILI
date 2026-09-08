"""Principal resolution: from an incoming request to "a user id, or nothing".

A `PrincipalResolver` is the single extension point for authentication. It gets
the request and returns a `Principal` or `None`; it never touches the database
and never decides whether the user is allowed in — `get_current_user` does that.

Two resolvers exist:

- `DisabledResolver` resolves nothing. It is the default, so a deployment that
  has not chosen an authentication mode exposes no protected route.
- `DevelopmentFixedUserResolver` resolves every request to one configured user
  id. It reads nothing from the request — no header, cookie, or query parameter
  can choose a different user — so there is nothing to forget to remove later.

Real authentication (a session cookie, a bearer token) is a third resolver, to
be added without changing anything that consumes a `Principal`.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi import Request


@dataclass(frozen=True, slots=True)
class Principal:
    """The claim a resolver makes: "this request is user `user_id`"."""

    user_id: UUID
    # Which mechanism produced the claim. Logged, never trusted for authorisation.
    method: str


class PrincipalResolver(Protocol):
    async def resolve(self, request: Request) -> Principal | None:
        """Return the principal for this request, or None if it is anonymous."""
        ...


class DisabledResolver:
    """Authentication is not configured: every request is anonymous."""

    method = "disabled"

    async def resolve(self, request: Request) -> Principal | None:
        return None


class DevelopmentFixedUserResolver:
    """DEVELOPMENT ONLY. Every request is the one configured user.

    Constructible only through settings that passed the development-only
    validation in `app/core/config.py`. The `request` argument is deliberately
    ignored: the caller has no way to influence who they are.
    """

    method = "development_fixed_user"

    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def resolve(self, request: Request) -> Principal | None:
        return Principal(user_id=self._user_id, method=self.method)
