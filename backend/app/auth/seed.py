"""Create the development fixed user. DEVELOPMENT ONLY.

    cd backend && python -m app.auth.seed

Idempotent: running it twice leaves one row. It inserts the user id configured
as DEV_FIXED_USER_ID with origin DEVELOPMENT, and refuses to run unless the
settings are in development_fixed_user mode — which itself requires
APP_ENV=development. The request path never creates users; this command is the
only writer, so "who exists" is always an explicit act.
"""

import asyncio
import logging
import sys
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import USER_ORIGIN_DEVELOPMENT, USER_STATUS_ACTIVE, User
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class SeedRefusedError(RuntimeError):
    """The environment is not one where a development user may be created."""


async def seed_development_user(session: AsyncSession, user_id: UUID) -> bool:
    """Ensure the development user exists. Returns True if it was created now.

    Only ever creates a DEVELOPMENT-origin row. If the id already exists — of any
    origin or status — nothing is changed: this command creates, it never
    promotes or reactivates.
    """
    existing = await session.get(User, user_id)
    if existing is not None:
        return False
    session.add(User(id=user_id, status=USER_STATUS_ACTIVE, origin=USER_ORIGIN_DEVELOPMENT))
    await session.commit()
    return True


def _require_development_mode() -> UUID:
    settings = get_settings()
    if settings.auth_mode != "development_fixed_user" or settings.dev_fixed_user_id is None:
        raise SeedRefusedError(
            "Refusing to seed: set AUTH_MODE=development_fixed_user and DEV_FIXED_USER_ID "
            "in the root .env (development only)."
        )
    return settings.dev_fixed_user_id


async def _main() -> int:
    user_id = _require_development_mode()
    async with get_sessionmaker()() as session:
        created = await seed_development_user(session, user_id)
    print(f"development user {user_id}: {'created' if created else 'already present'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except SeedRefusedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
