"""Apply the authoritative raw-SQL PostgreSQL fresh-bootstrap sequence.

This is a CI verifier/runner for disposable or empty PostgreSQL databases. It is
not an Alembic replacement and does not certify upgrades from unknown schemas.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SEQUENCE = (
    Path("portal/migrations/portal_schema.sql"),
    Path("portal/migrations/add_evidence_snapshots.sql"),
    Path("portal/migrations/add_audit_records.sql"),
    Path("portal/migrations/add_mission_control_command_ledger.sql"),
    Path("portal/migrations/add_mission_control_run_control_projection.sql"),
)
EXPECTED_TABLES = (
    "tenants",
    "roles",
    "users",
    "clients",
    "matters",
    "cases",
    "evidence_snapshots",
    "audit_records",
    "mission_control_commands",
    "mission_control_command_events",
    "mission_control_command_receipts",
    "mission_control_run_controls",
    "mission_control_run_control_events",
)


def psycopg2_url(raw_url: str) -> str:
    """Convert SQLAlchemy/async URLs to a psycopg2-compatible URL."""
    if raw_url.startswith("postgresql+asyncpg://"):
        raw_url = "postgresql://" + raw_url.removeprefix("postgresql+asyncpg://")
    if "ssl=disable" in raw_url:
        parts = urlsplit(raw_url)
        query = "&".join(
            part for part in parts.query.split("&") if part and part != "ssl=disable"
        )
        raw_url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    return raw_url


def apply_migrations(database_url: str, *, reset_public_schema: bool = False) -> list[str]:
    applied: list[str] = []
    with psycopg2.connect(psycopg2_url(database_url)) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            if reset_public_schema:
                cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
                cur.execute("CREATE SCHEMA public")
            for relative_path in MIGRATION_SEQUENCE:
                sql = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                cur.execute(sql)
                applied.append(str(relative_path).replace("\\", "/"))
    return applied


def assert_expected_tables(database_url: str) -> list[str]:
    with psycopg2.connect(psycopg2_url(database_url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        existing = {row[0] for row in cur.fetchall()}
    missing = sorted(set(EXPECTED_TABLES) - existing)
    if missing:
        raise RuntimeError(f"missing expected tables: {missing}")
    return sorted(existing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--reset-public-schema", action="store_true")
    parser.add_argument("--print-sequence", action="store_true")
    args = parser.parse_args()
    if args.print_sequence:
        for item in MIGRATION_SEQUENCE:
            print(str(item).replace("\\", "/"))
        return 0
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    applied = apply_migrations(args.database_url, reset_public_schema=args.reset_public_schema)
    tables = assert_expected_tables(args.database_url)
    print("applied=" + ",".join(applied))
    print("expected_tables_present=" + str(len(set(EXPECTED_TABLES) & set(tables))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
