"""
Gate 4.6 Corrective: Alembic URL Precedence Matrix.

Tests the complete database URL resolution contract from
portal/alembic/url_resolver.py:

  1. Caller-supplied connection overrides everything (integration)
  2. Explicit non-placeholder sqlalchemy.url overrides env and settings
  3. ALEMBIC_DATABASE_URL overrides settings when no explicit URL
  4. settings.DATABASE_URL is used only as fallback
  5. Placeholder sqlalchemy.url is ignored (falls through to env/settings)
  6. Supplied connection does not create a second engine (integration)
  7. Non-disposable PostgreSQL database is rejected by the guard
  8. Temporary SQLite migration does not touch the application database (integration)

Tests 1 and 6 are integration tests that exercise Alembic's command.upgrade
through the real env.py entry point. Tests 2–5 and 7–8 test the pure resolver
and guard functions directly, then test 8 adds an integration proof that the
resolved URL targets the correct database.

No sys.modules manipulation, no importlib.reload, no test-ordering dependence.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from alembic.config import Config
from alembic import command

from portal.alembic.url_resolver import (
    resolve_alembic_database_url,
    is_placeholder_url,
    normalize_database_url,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

DISPOSABLE_DB_NAMES = {"gate4_test", "gate4_clean", "sintraprime_test", "test_"}


def _make_temp_sqlite_path(name: str = "alembic_prec") -> str:
    """Return a path to a non-existent temp SQLite file."""
    tmp = Path(tempfile.gettempdir()) / f"{name}_{os.getpid()}_{id(object())}.db"
    if tmp.exists():
        tmp.unlink()
    return str(tmp)


def _assert_alembic_revision(db_path: str, expected: str = "905b70986558") -> None:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
        assert len(rows) == 1, f"Expected 1 revision row, got {rows}"
        assert rows[0][0] == expected, f"Expected {expected}, got {rows[0][0]}"
    finally:
        conn.close()


def _assert_no_tables(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert len(tables) == 0, f"Expected no tables, got {[t[0] for t in tables]}"
    finally:
        conn.close()


def _assert_has_tables(db_path: str, min_count: int = 10) -> None:
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert len(tables) >= min_count, \
            f"Expected >= {min_count} tables, got {len(tables)}: {[t[0] for t in tables]}"
    finally:
        conn.close()


def _make_alembic_config(sqlalchemy_url: str = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", "portal/alembic")
    if sqlalchemy_url:
        cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    return cfg


# ── Env restoration fixture ────────────────────────────────────────────────────

@pytest.fixture
def restore_env():
    """Snapshot and restore all relevant environment variables."""
    keys = ["DATABASE_URL", "ALEMBIC_DATABASE_URL", "ALLOW_SCHEMA_CREATE_ALL"]
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Caller-supplied connection overrides everything (integration)
# ═══════════════════════════════════════════════════════════════════════════════

def test_caller_connection_overrides_everything(restore_env):
    """Integration: a caller-supplied connection overrides sqlalchemy.url,
    ALEMBIC_DATABASE_URL, and settings.DATABASE_URL."""
    connection_db = _make_temp_sqlite_path("conn_override_conn")
    settings_db = _make_temp_sqlite_path("conn_override_settings")
    alembic_env_db = _make_temp_sqlite_path("conn_override_env")

    connection_url = f"sqlite:///{connection_db}"
    settings_url = f"sqlite+aiosqlite:///{settings_db}"
    alembic_env_url = f"sqlite:///{alembic_env_db}"

    os.environ["DATABASE_URL"] = settings_url
    os.environ["ALEMBIC_DATABASE_URL"] = alembic_env_url

    try:
        engine = create_engine(connection_url)
        with engine.connect() as connection:
            cfg = _make_alembic_config(sqlalchemy_url=settings_url)
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        engine.dispose()

        _assert_alembic_revision(connection_db)
        _assert_no_tables(settings_db)
        _assert_no_tables(alembic_env_db)
    finally:
        for p in [connection_db, settings_db, alembic_env_db]:
            if os.path.exists(p):
                os.unlink(p)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Explicit sqlalchemy.url overrides env and settings (pure resolver)
# ═══════════════════════════════════════════════════════════════════════════════

def test_explicit_sqlalchemy_url_overrides_env_and_settings(restore_env):
    """Pure: a non-placeholder configured_url wins over ALEMBIC_DATABASE_URL
    and settings.DATABASE_URL."""
    explicit_url = "sqlite:///tmp/explicit_test.db"
    env_url = "sqlite:///tmp/env_test.db"
    settings_url = "sqlite+aiosqlite:///tmp/settings_test.db"

    result = resolve_alembic_database_url(
        configured_url=explicit_url,
        environment={"ALEMBIC_DATABASE_URL": env_url},
        settings_database_url=settings_url,
    )

    assert result == explicit_url, \
        f"Explicit URL should win; got {result}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: ALEMBIC_DATABASE_URL overrides settings (pure resolver)
# ═══════════════════════════════════════════════════════════════════════════════

def test_alembic_database_url_overrides_settings(restore_env):
    """Pure: ALEMBIC_DATABASE_URL wins over settings.DATABASE_URL when no
    explicit sqlalchemy.url is set."""
    env_url = "sqlite:///tmp/alembic_env_test.db"
    settings_url = "sqlite+aiosqlite:///tmp/settings_test.db"

    result = resolve_alembic_database_url(
        configured_url=None,
        environment={"ALEMBIC_DATABASE_URL": env_url},
        settings_database_url=settings_url,
    )

    assert result == env_url, \
        f"ALEMBIC_DATABASE_URL should win over settings; got {result}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: settings.DATABASE_URL is fallback only (pure resolver)
# ═══════════════════════════════════════════════════════════════════════════════

def test_settings_database_url_is_fallback_only(restore_env):
    """Pure: settings.DATABASE_URL is used only when no explicit URL and no
    ALEMBIC_DATABASE_URL are set."""
    settings_url = "sqlite+aiosqlite:///tmp/settings_fallback.db"

    result = resolve_alembic_database_url(
        configured_url=None,
        environment={},
        settings_database_url=settings_url,
    )

    # Should be normalized (async driver stripped)
    expected = normalize_database_url(settings_url)
    assert result == expected, \
        f"Settings fallback should be used; got {result}, expected {expected}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Placeholder sqlalchemy.url is ignored (pure resolver)
# ═══════════════════════════════════════════════════════════════════════════════

def test_placeholder_sqlalchemy_url_is_ignored(restore_env):
    """Pure: a placeholder URL (driver://, sqlite://) is treated as not-set,
    and resolution falls through to ALEMBIC_DATABASE_URL or settings."""
    env_url = "sqlite:///tmp/env_after_placeholder.db"

    # Placeholder "driver://"
    result = resolve_alembic_database_url(
        configured_url="driver://user:pass@dbhost/dbname",
        environment={"ALEMBIC_DATABASE_URL": env_url},
        settings_database_url="sqlite:///tmp/settings_placeholder.db",
    )
    assert result == env_url, \
        f"Placeholder should be ignored; ALEMBIC env should win; got {result}"

    # Placeholder "sqlite://"
    result2 = resolve_alembic_database_url(
        configured_url="sqlite://",
        environment={"ALEMBIC_DATABASE_URL": env_url},
        settings_database_url="sqlite:///tmp/settings_placeholder2.db",
    )
    assert result2 == env_url, \
        f"'sqlite://' placeholder should be ignored; got {result2}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Supplied connection does not create a second engine (integration)
# ═══════════════════════════════════════════════════════════════════════════════

def test_caller_connection_does_not_create_second_engine(restore_env):
    """Integration: when a caller supplies a valid connection, Alembic must
    NOT create a second engine. Proven by providing an invalid URL alongside
    a valid connection — if migration succeeds, the invalid URL was never
    used to create an engine."""
    connection_db = _make_temp_sqlite_path("no_second_engine")
    connection_url = f"sqlite:///{connection_db}"

    # Set an invalid DATABASE_URL that would fail if used to create an engine
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///nonexistent/invalid/path.db"
    os.environ.pop("ALEMBIC_DATABASE_URL", None)

    try:
        engine = create_engine(connection_url)
        with engine.connect() as connection:
            cfg = _make_alembic_config(
                sqlalchemy_url="driver://invalid_placeholder"
            )
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        engine.dispose()

        _assert_alembic_revision(connection_db)
    finally:
        import gc
        gc.collect()
        if os.path.exists(connection_db):
            try:
                os.unlink(connection_db)
            except PermissionError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Non-disposable PostgreSQL database is rejected
# ═══════════════════════════════════════════════════════════════════════════════

def test_non_disposable_postgresql_database_is_rejected(restore_env):
    """The migration guard rejects PostgreSQL URLs that don't contain a
    disposable database name."""
    from portal.tests.test_migration_backfill import _check_pg_is_disposable

    # Must reject non-disposable names
    for name in ["sintraprime", "production", "postgres", "unknown_database"]:
        url = f"postgresql+psycopg2://user:pass@localhost:5432/{name}"
        with pytest.raises((RuntimeError, Exception), match="non-disposable|isolation check FAILED"):
            _check_pg_is_disposable(url)

    # Must accept disposable names
    for name in ["gate4_test", "gate4_clean", "sintraprime_test", "test_db"]:
        url = f"postgresql+psycopg2://user:pass@localhost:5432/{name}"
        _check_pg_is_disposable(url)  # Should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Temporary SQLite migration does not touch app database (integration)
# ═══════════════════════════════════════════════════════════════════════════════

def test_temp_sqlite_migration_does_not_touch_app_database(restore_env):
    """Integration: migrating a temporary SQLite database does not create
    tables in the application database configured via DATABASE_URL."""
    temp_db = _make_temp_sqlite_path("temp_migrate")
    app_db = _make_temp_sqlite_path("app_untouched")

    temp_url = f"sqlite:///{temp_db}"
    app_url = f"sqlite+aiosqlite:///{app_db}"

    os.environ["DATABASE_URL"] = app_url
    os.environ.pop("ALEMBIC_DATABASE_URL", None)

    try:
        cfg = _make_alembic_config(sqlalchemy_url=temp_url)
        command.upgrade(cfg, "head")

        _assert_has_tables(temp_db)
        _assert_no_tables(app_db)
    finally:
        for p in [temp_db, app_db]:
            if os.path.exists(p):
                os.unlink(p)
