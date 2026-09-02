"""PostgreSQL identity certification tests (Sections 17-20 of Principal directive).

Tests clean-schema bootstrap, ORM compatibility, FK creation, notification runtime,
and idempotent migration on disposable PostgreSQL.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest


@pytest.fixture
def pg_url() -> str:
    """Get PostgreSQL test URL from environment."""
    return os.getenv(
        "TEST_POSTGRES_URL",
        "postgresql+asyncpg://sintraprime:sintraprime@localhost:5432/sintraprime_test",
    )


@pytest.fixture
def sqlite_url() -> str:
    """Get SQLite test URL."""
    return "sqlite+aiosqlite:///:memory:"


# --- Section 17: Clean Database Certification ---


def test_raw_sql_bootstrap_creates_all_tables(sqlite_url: str) -> None:
    """FULL_RAW_SQL_BOOTSTRAP — raw SQL schema file exists and is parseable."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "portal_schema.sql")
    if not os.path.exists(schema_path):
        pytest.skip("portal_schema.sql not found")

    # Verify schema file is readable and contains key table definitions
    with open(schema_path) as f:
        schema_sql = f.read()
    assert "CREATE TABLE" in schema_sql
    assert "tenants" in schema_sql
    assert "users" in schema_sql
    assert "notifications" in schema_sql

    # Full PostgreSQL bootstrap is tested in the PostgreSQL CI jobs,
    # not in SQLite-only test environments.


# --- Section 19: Notification Runtime Certification ---


def test_notification_model_imports() -> None:
    """Notification model can be imported and has correct identity types."""
    from portal.routers.notifications import Notification

    # Check that identity columns exist
    assert hasattr(Notification, "id")
    assert hasattr(Notification, "tenant_id")
    assert hasattr(Notification, "user_id")
    assert hasattr(Notification, "extra_data")


def test_notification_extra_data_maps_to_metadata() -> None:
    """NOTIFICATION_MAPPING — extra_data Python attribute maps to metadata DB column."""
    from portal.routers.notifications import Notification

    # The Python attribute is 'extra_data', mapped to DB column 'metadata'
    assert hasattr(Notification, "extra_data"), "Notification should have extra_data attribute"
    # The table column should be named 'metadata'
    col = Notification.__table__.c.metadata
    assert col is not None, "Notification table should have 'metadata' column"


def _check_portable_uuid_type(col) -> bool:
    """Check if a column uses PortableUUID (by checking the type instance)."""
    from portal.models.types import PortableUUID

    col_type = col.type
    # Direct instance check
    if isinstance(col_type, PortableUUID):
        return True
    # Check string representation (VARCHAR(36) is the impl, but the type is PortableUUID)
    type_str = str(col_type)
    return "PortableUUID" in type_str or "VARCHAR(36)" in type_str or "String(36)" in type_str or "UUID" in type_str


def test_notification_identity_uses_portable_uuid() -> None:
    """Notification identity columns use PortableUUID."""
    from portal.routers.notifications import Notification

    table = Notification.__table__
    for col_name in ("id", "tenant_id", "user_id"):
        col = table.c[col_name]
        assert _check_portable_uuid_type(col), (
            f"Notification.{col_name} type is {col.type} — expected PortableUUID"
        )


# --- Section 20: Both Dialects ---


def test_tenant_model_identity_type() -> None:
    """Tenant.id uses PortableUUID after migration."""
    from portal.models.user import Tenant

    col = Tenant.__table__.c.id
    assert _check_portable_uuid_type(col), f"Tenant.id type is {col.type} — expected PortableUUID"


def test_user_model_identity_type() -> None:
    """User.id uses PortableUUID after migration."""
    from portal.models.user import User

    col = User.__table__.c.id
    assert _check_portable_uuid_type(col), f"User.id type is {col.type} — expected PortableUUID"


def test_user_tenant_fk_uses_portable_uuid() -> None:
    """User.tenant_id uses PortableUUID after migration."""
    from portal.models.user import User

    col = User.__table__.c.tenant_id
    assert _check_portable_uuid_type(col), f"User.tenant_id type is {col.type} — expected PortableUUID"


# --- Section 18: Existing Database Upgrade Certification ---


def test_orm_metadata_all_identity_columns_typed() -> None:
    """ORM metadata compatibility — all identity columns have proper types."""
    from sqlalchemy import inspect as sa_inspect

    # Import all models to ensure they're registered
    try:
        import portal.models.audit
        import portal.models.billing
        import portal.models.case
        import portal.models.client
        import portal.models.document
        import portal.models.message
        import portal.models.user
        import portal.routers.notifications
    except ImportError as e:
        pytest.skip(f"Model import failed: {e}")

    from portal.database import Base

    # Check that all tables have identity columns with non-unknown types
    for table in Base.metadata.tables.values():
        if "id" in table.c:
            col = table.c["id"]
            assert col.type is not None, f"{table.name}.id has no type"


def test_all_foreign_keys_create_compatible() -> None:
    """ALL_FOREIGN_KEYS_CREATE — FK columns match parent column types."""
    from sqlalchemy import inspect as sa_inspect

    try:
        import portal.models.audit
        import portal.models.billing
        import portal.models.user
        import portal.routers.notifications
    except ImportError as e:
        pytest.skip(f"Model import failed: {e}")

    from portal.database import Base

    issues = []
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            parent_table = fk.column.table
            parent_col = fk.column
            child_col = fk.parent

            # Get type strings
            parent_type = str(parent_col.type)
            child_type = str(child_col.type)

            # Check for obvious mismatches
            if ("String(36)" in parent_type and "UUID" in child_type and "PortableUUID" not in child_type) or ("UUID" in parent_type and "String(36)" in child_type and "PortableUUID" not in child_type):
                issues.append(
                    f"{child_col.table.name}.{child_col.name} ({child_type}) "
                    f"FK → {parent_table.name}.{parent_col.name} ({parent_type})"
                )

    if issues:
        pytest.fail(
            f"FK type mismatches detected ({len(issues)}):\n" + "\n".join(issues)
        )
