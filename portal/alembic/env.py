"""Alembic migration environment for SintraPrime Portal.

Supports both online (live database) and offline (SQL script) modes.
Uses SQLAlchemy async engine via run_sync wrapper for offline compatibility.

DATABASE_URL precedence (highest to lowest):
  1. SQLALCHEMY_URL environment variable
  2. DATABASE_URL environment variable
  3. alembic.ini sqlalchemy.url value
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Load all ORM models so Alembic autogenerate can see the full metadata ──────
# This import must happen before target_metadata is referenced.
import portal.models as _portal_models  # noqa: F401
from portal.database import Base

# ── Alembic Config object (provides access to values in alembic.ini) ───────────
config = context.config

# ── Logging ────────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Target metadata for autogenerate ──────────────────────────────────────────
target_metadata = Base.metadata


def _get_url() -> str:
    """Return the database URL from the environment or alembic.ini."""
    url = os.environ.get("SQLALCHEMY_URL") or os.environ.get("DATABASE_URL")
    if url:
        # Ensure async driver for async engine
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
        return url
    # Fall back to alembic.ini value (may use %(SQLALCHEMY_URL)s interpolation)
    return config.get_main_option("sqlalchemy.url")  # type: ignore[return-value]


# ── Offline mode ───────────────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without a live database connection."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ────────────────────────────────────────────────────────────────


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Tables managed by intentional SQL-only authority (not ORM) are excluded
        # from autogenerate drift detection.
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations via an async connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
