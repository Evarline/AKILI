"""`get_current_user`: the one seam between "who is calling" and "what they may touch".

Every route that reads or writes user-owned data declares
`current_user: CurrentUser = Depends(get_current_user)` and passes it down.
Services never look at the request.
"""

import logging
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import DevelopmentAuthForbiddenError, NotAuthenticatedError
from app.auth.models import CurrentUser
from app.auth.principals import DevelopmentFixedUserResolver, DisabledResolver, PrincipalResolver
from app.core.config import get_settings
from app.db.models import USER_ORIGIN_DEVELOPMENT, USER_STATUS_ACTIVE, User
from app.db.session import get_db

logger = logging.getLogger(__name__)


@lru_cache
def get_principal_resolver() -> PrincipalResolver:
    """The process-wide resolver, chosen once from settings.

    Also the FastAPI dependency tests override to impersonate a user. The
    "development_fixed_user" branch is reachable only if settings validation
    passed (APP_ENV=development, loopback host, an id configured).
    """
    settings = get_settings()
    if settings.auth_mode == "development_fixed_user":
        assert settings.dev_fixed_user_id is not None  # guaranteed by Settings validation
        return DevelopmentFixedUserResolver(settings.dev_fixed_user_id)
    return DisabledResolver()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
    resolver: PrincipalResolver = Depends(get_principal_resolver),
) -> CurrentUser:
    """Resolve the caller to an active AKILI user, or refuse the request.

    Every refusal is the same 401, so nothing about which users exist leaks.
    """
    principal = await resolver.resolve(request)
    if principal is None:
        raise NotAuthenticatedError("no principal")

    user = await session.get(User, principal.user_id)
    if user is None or user.status != USER_STATUS_ACTIVE:
        # Log the class of failure, never the id: an attacker probing ids
        # should learn nothing from the logs either.
        logger.info("current-user refused: %s", "unknown" if user is None else "inactive")
        raise NotAuthenticatedError("no active user")

    # Defence in depth. Settings already refuse to start with the development
    # resolver outside development; this catches a DEVELOPMENT-origin row being
    # served by any resolver in any other environment (e.g. a copied database).
    if user.origin == USER_ORIGIN_DEVELOPMENT and get_settings().app_env != "development":
        logger.error(
            "SECURITY: development-origin user resolved via %s in APP_ENV=%s; refusing",
            principal.method,
            get_settings().app_env,
        )
        raise DevelopmentAuthForbiddenError("development identity outside development")

    return CurrentUser(id=user.id)
