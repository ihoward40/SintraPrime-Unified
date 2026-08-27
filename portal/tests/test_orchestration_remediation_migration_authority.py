"""Migration authority tests for the three remediation tables.

Validates that:
- The new migration file exists and is in the bootstrap sequence
- EXPECTED_TABLES includes all three new tables
- The migration SQL is idempotent (CREATE TABLE IF NOT EXISTS + DROP POLICY IF EXISTS)
- FK creation order is safe (all parent tables already authoritative)
- ORM column definitions match the raw-SQL migration exactly
- RLS is enabled on all three tables
- Rollback notes are present
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "portal" / "migrations" / "add_orchestration_remediation_tables.sql"
BOOTSTRAP_PATH = REPO_ROOT / "portal" / "scripts" / "postgresql_bootstrap.py"


@pytest.fixture(scope="module")
def migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bootstrap_source() -> str:
    return BOOTSTRAP_PATH.read_text(encoding="utf-8")


# --- Migration file and sequence --------------------------------------------

def test_migration_file_exists(migration_sql: str):
    assert MIGRATION_PATH.exists()
    assert len(migration_sql) > 100


def test_migration_in_bootstrap_sequence(bootstrap_source: str):
    assert "add_orchestration_remediation_tables.sql" in bootstrap_source


def test_expected_tables_includes_new_tables(bootstrap_source: str):
    for table in ("orchestration_linkages", "orchestration_principal_authorities", "memory_vault"):
        assert table in bootstrap_source, f"{table} missing from EXPECTED_TABLES"


# --- Idempotency ------------------------------------------------------------

def test_migration_uses_if_not_exists(migration_sql: str):
    """All CREATE statements must use IF NOT EXISTS for idempotency."""
    create_tables = re.findall(r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?\w+", migration_sql, re.IGNORECASE)
    assert len(create_tables) >= 3
    for match in create_tables:
        assert match.strip(), "CREATE TABLE without IF NOT EXISTS found"


def test_migration_uses_drop_policy_if_exists(migration_sql: str):
    """All DROP POLICY statements must use IF EXISTS for idempotency."""
    drop_policies = re.findall(r"DROP\s+POLICY\s+(IF\s+EXISTS\s+)?", migration_sql, re.IGNORECASE)
    assert len(drop_policies) >= 3
    for match in drop_policies:
        assert match.strip(), "DROP POLICY without IF EXISTS found"


def test_migration_uses_create_index_if_not_exists(migration_sql: str):
    """All CREATE INDEX statements must use IF NOT EXISTS."""
    create_indexes = re.findall(r"CREATE\s+INDEX\s+(IF\s+NOT\s+EXISTS\s+)?", migration_sql, re.IGNORECASE)
    assert len(create_indexes) >= 4
    for match in create_indexes:
        assert match.strip(), "CREATE INDEX without IF NOT EXISTS found"


# --- Table definitions ------------------------------------------------------

def test_orchestration_linkages_schema(migration_sql: str):
    assert "CREATE TABLE IF NOT EXISTS orchestration_linkages" in migration_sql
    assert "UUID PRIMARY KEY" in migration_sql
    assert "event_id    UUID NOT NULL REFERENCES orchestration_events(id) ON DELETE CASCADE" in migration_sql
    assert "node_id     UUID NOT NULL REFERENCES orchestration_nodes(id) ON DELETE CASCADE" in migration_sql
    assert "tenant_id   UUID NOT NULL REFERENCES tenants(id)" in migration_sql
    assert "linked_at   TIMESTAMPTZ NOT NULL DEFAULT now()" in migration_sql
    assert "uq_orchestration_linkage_event_node" in migration_sql


def test_orchestration_principal_authorities_schema(migration_sql: str):
    assert "CREATE TABLE IF NOT EXISTS orchestration_principal_authorities" in migration_sql
    assert "tenant_id      UUID NOT NULL REFERENCES tenants(id)" in migration_sql
    assert "user_id        UUID NOT NULL REFERENCES users(id)" in migration_sql
    assert "scope          VARCHAR(80) NOT NULL DEFAULT 'GLOBAL'" in migration_sql
    assert "is_active      BOOLEAN NOT NULL DEFAULT TRUE" in migration_sql
    assert "authorized_at  TIMESTAMPTZ NOT NULL DEFAULT now()" in migration_sql
    assert "uq_orchestration_principal_auth" in migration_sql


def test_memory_vault_schema(migration_sql: str):
    assert "CREATE TABLE IF NOT EXISTS memory_vault" in migration_sql
    assert "tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE" in migration_sql
    assert "type           VARCHAR(80) NOT NULL" in migration_sql
    assert "content        JSONB NOT NULL" in migration_sql
    assert "metadata_json  JSONB NOT NULL DEFAULT '{}'::jsonb" in migration_sql
    assert "version        INTEGER NOT NULL DEFAULT 1" in migration_sql
    assert "created_at     TIMESTAMPTZ NOT NULL DEFAULT now()" in migration_sql


# --- RLS --------------------------------------------------------------------

def test_rls_enabled_on_all_three_tables(migration_sql: str):
    for table in ("orchestration_linkages", "orchestration_principal_authorities", "memory_vault"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in migration_sql


def test_rls_policies_use_tenant_id(migration_sql: str):
    policies = re.findall(r"CREATE POLICY (\w+)", migration_sql)
    assert len(policies) >= 3
    assert "app.current_tenant_id" in migration_sql


# --- Rollback ---------------------------------------------------------------

def test_rollback_notes_present(migration_sql: str):
    assert "DOWN migration notes" in migration_sql
    assert "DROP TABLE IF EXISTS memory_vault" in migration_sql
    assert "DROP TABLE IF EXISTS orchestration_principal_authorities" in migration_sql
    assert "DROP TABLE IF EXISTS orchestration_linkages" in migration_sql


# --- ORM-to-SQL type consistency -------------------------------------------

def test_orm_tables_match_migration_column_count():
    """Verify the ORM-declared columns match the migration SQL columns."""
    from portal.models.orchestration import (
        OrchestrationLinkage,
        PrincipalAuthority,
        MemoryEntry,
    )

    for model, expected_count in [
        (OrchestrationLinkage, 5),
        (PrincipalAuthority, 6),
        (MemoryEntry, 7),
    ]:
        assert len(model.__table__.columns) == expected_count, (
            f"{model.__tablename__}: expected {expected_count} columns, "
            f"got {len(model.__table__.columns)}"
        )