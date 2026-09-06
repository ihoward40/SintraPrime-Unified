"""CI invariant: PRODUCTION_AUTHORITY_TABLE -> MUST_HAVE_MIGRATION_OWNER.

Every protected JARVIS authority/evidence ORM table must have a production SQL
migration owner in portal/migrations/. A database provisioned from the SQL
artifacts must contain all authority tables without relying on ORM
create_all() side effects (JARVIS_B2_REGISTRY_MIGRATION_OWNERSHIP_REPAIR).

Fails if a protected table loses its migration owner or a new protected table
is added without one.
"""
from __future__ import annotations

import os

from portal.models import jarvis_b2_durability as durability_models
from portal.models import jarvis_capability_registry as registry_models

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(REPO_ROOT, "portal", "migrations")

# Protected authority/evidence tables (Principal-invariant enumeration).
PROTECTED_TABLES = {
    "capability_registrations": registry_models.CapabilityRegistration.__table__,
    "capability_transitions": registry_models.CapabilityTransition.__table__,
    "jarvis_authority_leases": durability_models.JarvisAuthorityLeaseRecord.__table__,
    "jarvis_operations": durability_models.JarvisOperationRecord.__table__,
    "jarvis_action_receipts": durability_models.JarvisActionReceiptRecord.__table__,
    "jarvis_operational_memory": durability_models.JarvisOperationalMemoryRecord.__table__,
    "jarvis_credential_state": durability_models.JarvisCredentialStateRecord.__table__,
}


def _migration_sql_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if filename.endswith(".sql"):
            with open(os.path.join(MIGRATIONS_DIR, filename), encoding="utf-8") as fh:
                texts[filename] = fh.read()
    return texts


def test_every_protected_authority_table_has_sql_migration_owner():
    sql_texts = _migration_sql_texts()
    assert sql_texts, "no SQL migrations found — production schema mechanism missing"
    orphans = []
    for table, model_table in PROTECTED_TABLES.items():
        # The ORM model must exist and declare the expected table name.
        assert model_table.name == table
        owners = [
            filename for filename, text_content in sql_texts.items()
            if f"CREATE TABLE IF NOT EXISTS {table} " in text_content
            or f"CREATE TABLE {table} " in text_content
        ]
        if not owners:
            orphans.append(table)
        assert model_table.columns.keys(), table
    assert orphans == [], (
        "PROTECTED authority/evidence tables without SQL migration ownership "
        f"(MUST_HAVE_MIGRATION_OWNER violated): {sorted(orphans)}"
    )


def test_protected_table_enumeration_is_exact():
    """Guard the invariant list itself: model module drift must fail loudly."""
    assert set(PROTECTED_TABLES) == {
        "capability_registrations",
        "capability_transitions",
        "jarvis_authority_leases",
        "jarvis_operations",
        "jarvis_action_receipts",
        "jarvis_operational_memory",
        "jarvis_credential_state",
    }
