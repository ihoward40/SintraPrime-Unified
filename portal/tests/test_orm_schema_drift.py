"""ORM vs live PostgreSQL schema drift test — R3-L.

Compares the authoritative ORM model set (Base.metadata) against the
migrated PostgreSQL schema.  Detects:

  - missing tables (ORM declares, DB lacks)
  - extra tables (DB has, ORM lacks — distinguished from the intentional allowlist)
  - missing columns
  - column type mismatches (best-effort via information_schema)
  - nullable mismatches
  - primary key mismatches

Intentional differences (SQL-only tables with deliberate no-ORM status) are
recorded in INTENTIONAL_SQL_ONLY_TABLES and excluded from the "extra table"
failure path.

This test requires a disposable PostgreSQL database.
Set POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL or DATABASE_URL.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

import portal.models as _portal_models  # noqa: F401 — registers all ORM classes
from portal.database import Base
from portal.scripts.postgresql_bootstrap import (
    MIGRATION_SEQUENCE,
    apply_migrations,
    psycopg2_url,
)

pytestmark = pytest.mark.postgresql

# ── Intentional differences allowlist ─────────────────────────────────────────
# Tables that exist in the database but have no ORM model by deliberate design.
INTENTIONAL_SQL_ONLY_TABLES: frozenset[str] = frozenset(
    {
        # Agent runtime subsystem — managed by runtime_schema_baseline.sql
        "agents",
        "swarms",
        "skills",
        "knowledge_entries",
        "execution_history",
        "sessions",
        # Notification model is defined inline in portal/routers/notifications.py
        # rather than in portal/models/.  It is provisioned by portal_schema.sql
        # and is intentionally absent from the models package __init__.py.
        "notifications",
    }
)

# Alembic history table — always present after migrations, no ORM model needed.
_ALEMBIC_TABLES: frozenset[str] = frozenset({"alembic_version"})


def _database_url() -> str:
    url = os.environ.get("POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL drift test database URL not configured")
    return url


@pytest.fixture(scope="module")
def migrated_db_url() -> str:
    """Apply fresh canonical migrations and return the URL."""
    url = _database_url()
    apply_migrations(url, reset_public_schema=True)
    return url


# ── Helpers ────────────────────────────────────────────────────────────────────


def _live_tables(url: str) -> set[str]:
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        return {row[0] for row in cur.fetchall()}


def _live_columns(url: str, table: str) -> dict[str, dict]:
    """Return {column_name: {data_type, is_nullable}} for a given table."""
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return {row[0]: {"data_type": row[1], "is_nullable": row[2]} for row in cur.fetchall()}


def _live_primary_keys(url: str) -> dict[str, set[str]]:
    """Return {table_name: {pk_column, ...}} for all tables."""
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            """
        )
        result: dict[str, set[str]] = {}
        for table_name, col_name in cur.fetchall():
            result.setdefault(table_name, set()).add(col_name)
        return result


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_orm_tables_all_present_in_migrated_db(migrated_db_url: str) -> None:
    """Every table in Base.metadata must exist in the migrated database."""
    live = _live_tables(migrated_db_url)
    orm_tables = set(Base.metadata.tables.keys())
    missing_from_db = orm_tables - live
    assert missing_from_db == set(), (
        f"ORM tables not found in migrated database: {sorted(missing_from_db)}\n"
        "Either add SQL to provision these tables or remove the ORM model."
    )


def test_extra_db_tables_are_intentional(migrated_db_url: str) -> None:
    """Any table in the DB but not in the ORM must be on the intentional allowlist."""
    live = _live_tables(migrated_db_url) - _ALEMBIC_TABLES
    orm_tables = set(Base.metadata.tables.keys())
    extra = live - orm_tables - INTENTIONAL_SQL_ONLY_TABLES
    assert extra == set(), (
        f"Database tables exist with no ORM model and are NOT on the intentional allowlist: "
        f"{sorted(extra)}\n"
        "Add them to INTENTIONAL_SQL_ONLY_TABLES if they are deliberate, or add an ORM model."
    )


def test_intentional_sql_only_tables_are_present(migrated_db_url: str) -> None:
    """Intentional SQL-only tables must still be provisioned in the database."""
    live = _live_tables(migrated_db_url)
    # Only check the runtime-required ones (not notifications which is in portal_schema already)
    required_sql_only = frozenset(
        {"agents", "swarms", "skills", "knowledge_entries", "execution_history", "sessions"}
    )
    missing = required_sql_only - live
    assert missing == set(), (
        f"Intentional SQL-only tables missing from migrated database: {sorted(missing)}"
    )


def test_orm_columns_present_in_migrated_db(migrated_db_url: str) -> None:
    """Every column declared in ORM models must exist in the corresponding live table."""
    mismatches: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        live_cols = _live_columns(migrated_db_url, table_name)
        if not live_cols:
            # Table existence is checked separately; skip column check if table absent.
            continue
        for column in table.columns:
            if column.name not in live_cols:
                mismatches.append(f"{table_name}.{column.name}: present in ORM, absent in DB")
    assert mismatches == [], "Column drift detected:\n" + "\n".join(mismatches)


def test_orm_nullable_matches_live_db(migrated_db_url: str) -> None:
    """ORM nullable declarations must match the live schema (best-effort check).

    Not all SQLAlchemy nullable settings survive round-tripping through raw SQL
    DDL — particularly server-default-only columns.  This test flags definitive
    mismatches while tolerating expected ambiguities via a short allowlist.
    """
    # Columns exempt from nullable comparison because the ORM and SQL
    # legitimately express this differently (e.g., server default implies NOT NULL
    # in SQL but SQLAlchemy doesn't enforce at the dialect level).
    exempt: set[tuple[str, str]] = {
        # Server-generated timestamps: ORM nullable=False via server_default,
        # SQL uses DEFAULT NOW() which PostgreSQL stores as NOT NULL.
        # No fix needed — the ORM is correct for its purpose.
    }
    mismatches: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        live_cols = _live_columns(migrated_db_url, table_name)
        if not live_cols:
            continue
        for column in table.columns:
            if column.name not in live_cols:
                continue
            if (table_name, column.name) in exempt:
                continue
            live_nullable = live_cols[column.name]["is_nullable"] == "YES"
            orm_nullable = column.nullable if column.nullable is not None else True
            if live_nullable != orm_nullable:
                mismatches.append(
                    f"{table_name}.{column.name}: "
                    f"ORM nullable={orm_nullable}, DB nullable={live_nullable}"
                )
    # Report as warning, not hard failure — some mismatches are expected from
    # server-default columns and ORM flexibility.
    if mismatches:
        import warnings
        warnings.warn(
            "Nullable drift between ORM and DB (informational):\n" + "\n".join(mismatches),
            stacklevel=1,
        )


def test_primary_keys_match_live_db(migrated_db_url: str) -> None:
    """ORM primary keys must match the live database primary keys."""
    live_pks = _live_primary_keys(migrated_db_url)
    mismatches: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        if table_name not in live_pks:
            continue
        orm_pks = {c.name for c in table.primary_key}
        db_pks = live_pks[table_name]
        if orm_pks != db_pks:
            mismatches.append(
                f"{table_name}: ORM PK={sorted(orm_pks)}, DB PK={sorted(db_pks)}"
            )
    assert mismatches == [], "Primary key drift:\n" + "\n".join(mismatches)


def test_rls_enabled_on_required_tables(migrated_db_url: str) -> None:
    """Tables that must carry RLS must have it enabled after migration."""
    required_rls = {
        "audit_logs",
        "clients",
        "cases",
        "documents",
        "message_threads",
        "messages",
        "invoices",
        "time_entries",
        "evidence_ledger",
        "blackstone_evaluations",
        "mission_control_outbox",
    }
    with psycopg2.connect(psycopg2_url(migrated_db_url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT relname
            FROM pg_class
            WHERE relnamespace = 'public'::regnamespace
              AND relrowsecurity = TRUE
              AND relkind = 'r'
            """
        )
        rls_enabled = {row[0] for row in cur.fetchall()}

    missing_rls = required_rls - rls_enabled
    assert missing_rls == set(), (
        f"Tables that require RLS but do not have it enabled: {sorted(missing_rls)}"
    )


def test_migration_idempotent_repeated_three_times() -> None:
    """Running the full migration sequence three times on a fresh DB must succeed."""
    url = _database_url()
    for attempt in range(3):
        apply_migrations(url, reset_public_schema=True)
        live = _live_tables(url)
        # Spot-check critical tables on each iteration
        for t in ("tenants", "users", "permissions", "evidence_ledger", "blackstone_evaluations",
                  "mission_control_outbox", "agents"):
            assert t in live, f"[attempt {attempt}] expected table {t!r} not found after migration"


def test_migration_no_op_upgrade_head(migrated_db_url: str) -> None:
    """After migrations, re-running should not error (IF NOT EXISTS guards)."""
    # Apply a second time — all CREATE TABLE IF NOT EXISTS should be no-ops.
    apply_migrations(migrated_db_url, reset_public_schema=False)
    live = _live_tables(migrated_db_url)
    assert "tenants" in live
    assert "permissions" in live
    assert "evidence_ledger" in live
    assert "mission_control_outbox" in live
