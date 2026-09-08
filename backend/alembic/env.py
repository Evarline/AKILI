"""Alembic environment.

The database URL comes from the application settings (root .env), not from
alembic.ini — alembic.ini is committed to Git and must never hold credentials.
Run migrations from the backend/ directory, the same place the server runs from.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.db.base import Base

# Importing the model modules registers their tables on Base.metadata. Every
# module that defines models must be listed here for autogenerate to see it.
import app.db.models  # noqa: F401, E402

# Alembic Config object, providing access to the values in alembic.ini.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for `alembic revision --autogenerate`.
target_metadata = Base.metadata


def get_database_url() -> str:
    """Return the configured database URL, or fail without leaking credentials."""
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in the root .env file "
            "(see .env.example) before running Alembic."
        )
    return str(settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations without a DBAPI connection, emitting SQL to stdout."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run the migrations against it."""
    section = config.get_section(config.config_ini_section, {})
    # Injected into the section dict rather than via set_main_option, so that a
    # '%' in the password is not treated as configparser interpolation.
    section["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
