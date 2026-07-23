"""
Pure database URL resolver for Alembic migrations.

This module contains the configuration-policy logic that determines which
database URL Alembic should use. It is intentionally free of any SQLAlchemy
engine creation, Alembic context access, or side effects — it is a pure
function that can be tested deterministically.

Precedence (highest to lowest):
    1. Caller-supplied connection (handled by env.py, not this resolver)
    2. Explicit non-placeholder sqlalchemy.url
    3. ALEMBIC_DATABASE_URL environment variable
    4. settings.DATABASE_URL (application fallback)

Usage in env.py:
    from portal.alembic.url_resolver import resolve_alembic_database_url
    resolved = resolve_alembic_database_url(
        configured_url=config.get_main_option("sqlalchemy.url"),
        environment=os.environ,
        settings_database_url=get_settings().DATABASE_URL,
    )
    config.set_main_option("sqlalchemy.url", resolved)
"""

import os
from typing import Optional

# Placeholder URL patterns from alembic.ini defaults that should NOT
# count as intentionally configured URLs.
PLACEHOLDER_PATTERNS = (
    "driver://",   # Alembic default template placeholder
    "sqlite://",    # bare sqlite in-memory, not a real test target
)


def is_placeholder_url(url: Optional[str]) -> bool:
    """Return True if the URL is None, empty, or an Alembic default placeholder.

    Placeholders are:
        - None or empty string
        - "driver://..." (Alembic default template)
        - "sqlite://" with no path (bare in-memory, not a real test target)
    Note: "sqlite:///path/to/file.db" is NOT a placeholder — it's a real file path.
    """
    if not url:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern in url:
            # "sqlite://" is only a placeholder if not followed by a path.
            # "sqlite:///file.db" has a path and is real.
            # "sqlite://" alone or "sqlite:// " is a placeholder.
            if pattern == "sqlite://":
                # Check if there's a path after "sqlite://"
                rest = url[url.index(pattern) + len(pattern):]
                if rest.startswith("/"):
                    # sqlite:///path — real URL, not a placeholder
                    continue
            return True
    return False


def normalize_database_url(url: str) -> str:
    """Convert async driver URLs to synchronous drivers for Alembic.

    Alembic uses sync SQLAlchemy engines, so async-only drivers like
    +asyncpg and +aiosqlite must be stripped to their sync equivalents.
    """
    return url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")


def resolve_alembic_database_url(
    *,
    configured_url: Optional[str],
    environment: Optional[dict] = None,
    settings_database_url: Optional[str] = None,
) -> Optional[str]:
    """Resolve the database URL according to the precedence contract.

    Parameters
    ----------
    configured_url
        The value of sqlalchemy.url currently set on the Alembic Config.
        May be None or a placeholder — both are treated as "not set".
    environment
        The environment dict (defaults to os.environ). Used to read
        ALEMBIC_DATABASE_URL.
    settings_database_url
        The application's DATABASE_URL from portal settings. Used as the
        final fallback.

    Returns
    -------
    The resolved, normalized URL string, or None if no URL is available.

    Precedence
    ----------
    1. If configured_url is set and is not a placeholder, return it as-is
       (it was intentionally set by the caller).
    2. If ALEMBIC_DATABASE_URL is in the environment and non-empty, return
       the normalized form of it.
    3. If settings_database_url is provided, return the normalized form.
    4. Otherwise return None (no URL available).
    """
    env = environment if environment is not None else os.environ

    # Precedence 2: explicit non-placeholder sqlalchemy.url
    if configured_url and not is_placeholder_url(configured_url):
        return configured_url

    # Precedence 3: ALEMBIC_DATABASE_URL environment variable
    alembic_env_url = env.get("ALEMBIC_DATABASE_URL")
    if alembic_env_url:
        return normalize_database_url(alembic_env_url)

    # Precedence 4: settings.DATABASE_URL fallback
    if settings_database_url:
        return normalize_database_url(settings_database_url)

    # No URL available
    return None
