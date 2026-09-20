"""
Alembic environment configuration for SintraPrime Portal.

Supports both PostgreSQL (production) and SQLite (development).
Database URL resolution precedence (highest to lowest):

1. Caller-supplied connection via config.attributes["connection"]
2. Explicit sqlalchemy.url set by the caller (e.g., migration tests)
3. ALEMBIC_DATABASE_URL environment variable
4. settings.DATABASE_URL from portal config (fallback)

This precedence ensures migration integration tests can target a
temporary database without monkey-patching global settings or
accidentally touching the application database.

render_as_batch=True is enabled for SQLite ALTER TABLE support.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# ── Project path setup ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from portal.database import Base  # noqa: E402
from portal.config import get_settings  # noqa: E402

# Import all models so Alembic autogenerate can see them.
import portal.models  # noqa: E402, F401

# ── Alembic Config ──────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Target metadata for autogenerate ────────────────────────────────────────
target_metadata = Base.metadata

# ── Database URL resolution with precedence ─────────────────────────────────
# Delegates to the pure resolver in url_resolver.py so the precedence
# contract is testable without importing this script module.
#
# Precedence (highest to lowest):
#   1. Caller-supplied connection via config.attributes["connection"]
#      (handled in run_migrations_online, not here)
#   2. Explicit non-placeholder sqlalchemy.url already set by the caller
#   3. ALEMBIC_DATABASE_URL environment variable
#   4. settings.DATABASE_URL (application fallback)

from portal.alembic.url_resolver import resolve_alembic_database_url

configured_url = config.get_main_option("sqlalchemy.url")

resolved_url = resolve_alembic_database_url(
    configured_url=configured_url,
    environment=os.environ,
    settings_database_url=get_settings().DATABASE_URL,
)

if resolved_url:
    config.set_main_option("sqlalchemy.url", resolved_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL — no Engine needed.
    Calls to context.execute() emit SQL to script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Uses a caller-supplied connection if available (preferred for tests),
    otherwise creates an Engine from the resolved URL.
    """
    # Precedence 1: caller-supplied connection
    connection = config.attributes.get("connection")

    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()