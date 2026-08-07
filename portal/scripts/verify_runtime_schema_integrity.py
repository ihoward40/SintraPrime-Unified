#!/usr/bin/env python3
"""
Runtime Schema Integrity Migration Verifier

Applies portal/migrations/runtime_schema_integrity_2026_07_27.sql to a target
PostgreSQL database and validates the resulting constraints/indexes.

Usage:
    python portal/scripts/verify_runtime_schema_integrity.py <DATABASE_URL>

Example:
    python portal/scripts/verify_runtime_schema_integrity.py \
        "postgresql+asyncpg://sintraprime:***@127.0.0.1:5433/sintraprime_unified"
"""

from __future__ import annotations

import asyncio
import sys
from urllib.parse import urlparse

import asyncpg

BASELINE_FILE = "portal/migrations/runtime_schema_baseline.sql"
MIGRATION_FILE = "portal/migrations/runtime_schema_integrity_2026_07_27.sql"


def normalize_url(url: str) -> str:
    """Return a clean asyncpg DSN from an SQLAlchemy-style URL."""
    parsed = urlparse(url)
    scheme = parsed.scheme
    if scheme.startswith("postgresql+"):
        scheme = "postgresql"
    netloc = parsed.netloc
    path = parsed.path
    return f"{scheme}://{netloc}{path}"


async def apply_baseline(conn: asyncpg.Connection, repo_root: str) -> None:
    baseline_path = f"{repo_root}/{BASELINE_FILE}"
    with open(baseline_path, encoding="utf-8") as f:
        sql = f.read()
    await conn.execute(sql)


async def apply_migration(conn: asyncpg.Connection, repo_root: str) -> None:
    migration_path = f"{repo_root}/{MIGRATION_FILE}"
    with open(migration_path, encoding="utf-8") as f:
        sql = f.read()
    await conn.execute(sql)


async def verify(conn: asyncpg.Connection) -> dict:
    results: dict = {"checks": [], "passed": 0, "failed": 0}

    checks = [
        ("ck_agents_status", "SELECT 1 FROM pg_constraint WHERE conname = 'ck_agents_status'"),
        (
            "ck_execution_history_status",
            "SELECT 1 FROM pg_constraint WHERE conname = 'ck_execution_history_status'",
        ),
        ("ck_swarms_status", "SELECT 1 FROM pg_constraint WHERE conname = 'ck_swarms_status'"),
        (
            "ck_messages_priority",
            "SELECT 1 FROM pg_constraint WHERE conname = 'ck_messages_priority'",
        ),
        (
            "ck_knowledge_entries_confidence",
            "SELECT 1 FROM pg_constraint WHERE conname = 'ck_knowledge_entries_confidence'",
        ),
        (
            "idx_messages_sender_id",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_messages_sender_id'",
        ),
        (
            "idx_messages_recipient_id",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_messages_recipient_id'",
        ),
        (
            "idx_execution_history_agent_id",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_execution_history_agent_id'",
        ),
        (
            "idx_execution_history_swarm_id",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_execution_history_swarm_id'",
        ),
        (
            "idx_sessions_user_id",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sessions_user_id'",
        ),
        ("idx_users_is_active", "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_is_active'"),
        (
            "idx_knowledge_entries_source",
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_knowledge_entries_source'",
        ),
    ]

    for name, query in checks:
        row = await conn.fetchrow(query)
        ok = row is not None
        results["checks"].append({"name": name, "passed": ok})
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Verify NOT NULL on a representative column
    nn_row = await conn.fetchrow(
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'agents' AND column_name = 'status'
        """
    )
    nn_ok = nn_row is not None and nn_row["is_nullable"] == "NO"
    results["checks"].append({"name": "agents.status NOT NULL", "passed": nn_ok})
    if nn_ok:
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Verify CHECK rejects invalid value
    try:
        await conn.execute(
            "INSERT INTO agents (name, type, status) VALUES ('test-agent', 'worker', 'invalid_status')"
        )
        results["checks"].append({"name": "agents.status CHECK rejects invalid", "passed": False})
        results["failed"] += 1
    except asyncpg.CheckViolationError:
        results["checks"].append({"name": "agents.status CHECK rejects invalid", "passed": True})
        results["passed"] += 1

    return results


async def main(url: str) -> int:
    repo_root = "."
    dsn = normalize_url(url)
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await apply_baseline(conn, repo_root)
        await apply_migration(conn, repo_root)
        results = await verify(conn)

        print(f"Migration applied to: {dsn}")
        print(f"Checks passed: {results['passed']}")
        print(f"Checks failed: {results['failed']}")
        for check in results["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"  [{status}] {check['name']}")

        return 0 if results["failed"] == 0 else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    url = sys.argv[1]
    raise SystemExit(asyncio.run(main(url)))
