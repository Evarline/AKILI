"""Identity foundation — DEVELOPMENT identity, not production authentication.

What this package does
----------------------
It answers one question for a request: *which AKILI user is this?* The answer is
a `CurrentUser` value that routes pass to services, and that services use to
scope every query (`WHERE user_id = :current`). Conversations are owned this way
today; Binance connections will be owned this way in a later phase.

What it does not do
-------------------
It does not authenticate anyone. There is no login, no password, no session, no
token. The only resolver implemented is `DevelopmentFixedUserResolver`, which
serves every request as one pre-seeded user, and it can only be enabled in
`APP_ENV=development` on a loopback host (`app/core/config.py` refuses to build
settings otherwise). The default `AUTH_MODE=disabled` makes every protected
route answer 401.

How real authentication arrives later
-------------------------------------
By adding another `PrincipalResolver` (a session cookie, a bearer token) and a
`user_identities` table. `get_current_user`, `CurrentUser`, the services, and
the ownership columns stay exactly as they are.
"""

from app.auth.dependencies import get_current_user, get_principal_resolver
from app.auth.errors import AuthError, DevelopmentAuthForbiddenError, NotAuthenticatedError
from app.auth.models import CurrentUser
from app.auth.principals import (
    DevelopmentFixedUserResolver,
    DisabledResolver,
    Principal,
    PrincipalResolver,
)

__all__ = [
    "AuthError",
    "CurrentUser",
    "DevelopmentAuthForbiddenError",
    "DevelopmentFixedUserResolver",
    "DisabledResolver",
    "NotAuthenticatedError",
    "Principal",
    "PrincipalResolver",
    "get_current_user",
    "get_principal_resolver",
]
