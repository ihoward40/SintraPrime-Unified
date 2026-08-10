"""Apply the authoritative raw-SQL PostgreSQL fresh-bootstrap sequence.

This is the canonical provisioning tool for disposable or empty PostgreSQL
databases.  It executes migration files in the canonical dependency order that
matches the Alembic revision a1b2c3d4e5f6 (R3 baseline).

Deployment contract (R3-K Option B):
  Migrations ship as a separate provisioning artefact (source checkout).
  The installed application wheel does NOT bundle migration files.
  Provisioning command:
      python -m portal.scripts.postgresql_bootstrap --database-url $DATABASE_URL

R1 security preservation:
  This script does not create or alter the sintraprime_app runtime role.
  Role provisioning is performed by the infrastructure layer before this script runs.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[2]

# Canonical migration order — must match portal/alembic/versions/a1b2c3d4e5f6_r3_canonical_baseline.py
MIGRATION_SEQUENCE = (
    Path("portal/migrations/portal_schema.sql"),
    Path("portal/migrations/add_evidence_snapshots.sql"),
    Path("portal/migrations/add_audit_records.sql"),
    Path("portal/migrations/add_legal_authority_rules.sql"),
    Path("portal/migrations/add_voice_command_ledger.sql"),
    Path("portal/migrations/add_mission_control_command_ledger.sql"),
    Path("portal/migrations/add_mission_control_run_control_projection.sql"),
    Path("portal/migrations/add_matter_intelligence.sql"),
    Path("portal/migrations/add_deadline_evidence_intelligence.sql"),
    Path("portal/migrations/add_permissions_rbac.sql"),
    Path("portal/migrations/add_blackstone_evidence_ledger.sql"),
    Path("portal/migrations/add_mission_control_outbox.sql"),
    Path("portal/migrations/runtime_schema_baseline.sql"),
    Path("portal/migrations/runtime_schema_integrity_2026_07_27.sql"),
)

# Complete set of authoritative runtime tables.
# SQL-only intentional tables (agents, swarms, skills, knowledge_entries,
# execution_history, sessions) are included — they have documented SQL authority
# and deliberate absence of an ORM model.
EXPECTED_TABLES = (
    # Core portal schema
    "tenants",
    "roles",
    "users",
    "clients",
    "matters",
    "cases",
    "case_events",
    "case_deadlines",
    "case_notes",
    "case_tasks",
    "document_folders",
    "documents",
    "document_versions",
    "document_shares",
    "message_threads",
    "messages",
    "message_attachments",
    "time_entries",
    "expenses",
    "invoices",
    "invoice_line_items",
    "payments",
    "trust_accounts",
    "notifications",
    "audit_logs",
    # Extended portal schema
    "evidence_snapshots",
    "audit_records",
    "legal_authorities",
    "jurisdiction_rules",
    "professional_reviews",
    "voice_commands",
    "voice_command_events",
    "voice_command_receipts",
    "mission_control_commands",
    "mission_control_command_events",
    "mission_control_command_receipts",
    "mission_control_run_controls",
    "mission_control_run_control_events",
    "matter_parties",
    "matter_accounts",
    "matter_filings",
    "matter_communications",
    "matter_disputes",
    "matter_attachments",
    "matter_assessments",
    "matter_assessment_versions",
    "matter_audit_events",
    "matter_deadlines",
    "matter_deadline_versions",
    "matter_evidence_nodes",
    "matter_evidence_links",
    "matter_evidence_findings",
    # R3 — previously ORM-only, now SQL-covered
    "permissions",
    "role_permissions",
    "user_permissions",
    "evidence_ledger",
    "blackstone_evaluations",
    "mission_control_outbox",
    # SQL-only intentional (agent runtime subsystem)
    "agents",
    "swarms",
    "skills",
    "knowledge_entries",
    "execution_history",
    "sessions",
)


def psycopg2_url(raw_url: str) -> str:
    """Convert SQLAlchemy/async URLs to a psycopg2-compatible URL."""
    if raw_url.startswith("postgresql+asyncpg://"):
        raw_url = "postgresql://" + raw_url.removeprefix("postgresql+asyncpg://")
    if "ssl=disable" in raw_url:
        parts = urlsplit(raw_url)
        query = "&".join(part for part in parts.query.split("&") if part and part != "ssl=disable")
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
