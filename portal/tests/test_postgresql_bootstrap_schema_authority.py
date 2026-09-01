"""PostgreSQL raw-SQL bootstrap and affected ORM authority certification."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from portal import models as _models
from portal.database import Base
from portal.models.audit_record import AuditRecord
from portal.models.evidence_snapshot import EvidenceSnapshot
from portal.scripts.postgresql_bootstrap import (
    EXPECTED_TABLES,
    MIGRATION_SEQUENCE,
    apply_migrations,
    psycopg2_url,
)

pytestmark = pytest.mark.postgresql


def _database_url() -> str:
    url = os.environ.get("POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL bootstrap certification database URL not configured")
    return url


def _async_sqlalchemy_url(url: str) -> str:
    """Return an async SQLAlchemy URL for the ORM create_all CI path."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


@pytest.fixture
def migrated_database_url() -> str:
    url = _database_url()
    apply_migrations(url, reset_public_schema=True)
    return url


def _seed_case_user(url: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()
    with psycopg2.connect(psycopg2_url(url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (str(tenant_id), "PR-B Test Firm", f"prb-{tenant_id.hex[:12]}"),
            )
            cur.execute("SELECT id FROM roles WHERE name = 'FIRM_ADMIN'")
            role_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO users (id, tenant_id, role_id, email, first_name, last_name, hashed_password)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(user_id),
                    str(tenant_id),
                    str(role_id),
                    f"prb-{user_id.hex[:12]}@example.invalid",
                    "PRB",
                    "Tester",
                    "synthetic-not-a-real-password",
                ),
            )
            cur.execute(
                """
                INSERT INTO clients (id, tenant_id, primary_attorney_id, client_type, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(client_id), str(tenant_id), str(user_id), "individual", "Test", "Client"),
            )
            cur.execute(
                """
                INSERT INTO cases (id, tenant_id, client_id, lead_attorney_id, case_number, title)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(case_id),
                    str(tenant_id),
                    str(client_id),
                    str(user_id),
                    f"PRB-{case_id.hex[:8]}",
                    "PR-B Bootstrap Case",
                ),
            )
    return tenant_id, client_id, user_id, case_id


def test_authoritative_migration_sequence_is_ordered() -> None:
    # Canonical 10-migration sequence reflecting convergence of Option 5 with current main.
    # Order: portal_schema.sql first (foundational), then additive migrations.
    # Hard-verified dependency edges (from SQL inspection):
    #   mission_runs < run_approvals  (run_approvals references runs.run_id)
    #   command_ledger < run_control_projection  (run-control references mission_control_commands)
    #   adaptive_domain < identity_fk_alignment  (verify from SQL)
    #   tenant_principal and mission_runs are INDEPENDENT siblings after portal_schema.sql
    #   (mission_runs FK: tenants, users; NO tenant_principals reference)
    # Adopt deterministic canonical order (not strictly dependency-based for siblings).
    assert [str(path).replace("\\", "/") for path in MIGRATION_SEQUENCE] == [
        "portal/migrations/portal_schema.sql",
        "portal/migrations/add_evidence_snapshots.sql",
        "portal/migrations/add_audit_records.sql",
        "portal/migrations/add_tenant_principal.sql",
        "portal/migrations/add_mission_control_command_ledger.sql",
        "portal/migrations/add_adaptive_orchestration_domain.sql",
        "portal/migrations/align_orchestration_identity_fk_types.sql",
        "portal/migrations/add_mission_control_mission_runs.sql",
        "portal/migrations/add_mission_control_run_approvals.sql",
        "portal/migrations/add_mission_control_run_control_projection.sql",
    ]
    # Uniqueness and count invariants
    seq = [str(path).replace("\\", "/") for path in MIGRATION_SEQUENCE]
    assert len(seq) == 10, f"Expected 10 migrations, got {len(seq)}"
    assert len(set(seq)) == 10, f"Expected 10 unique migrations, got duplicates: {set(seq)}"
    # All required main migrations present
    main_migrations = {
        "portal/migrations/portal_schema.sql",
        "portal/migrations/add_evidence_snapshots.sql",
        "portal/migrations/add_audit_records.sql",
        "portal/migrations/add_mission_control_command_ledger.sql",
        "portal/migrations/add_adaptive_orchestration_domain.sql",
        "portal/migrations/align_orchestration_identity_fk_types.sql",
    }
    main_present = sum(1 for m in main_migrations if m in seq)
    assert main_present == 6, f"Expected 6 main migrations present, got {main_present}"
    # All Option 5 migrations present
    option5_migrations = {
        "portal/migrations/add_tenant_principal.sql",
        "portal/migrations/add_mission_control_command_ledger.sql",
        "portal/migrations/add_mission_control_mission_runs.sql",
        "portal/migrations/add_mission_control_run_approvals.sql",
        "portal/migrations/add_mission_control_run_control_projection.sql",
    }
    option5_present = sum(1 for m in option5_migrations if m in seq)
    assert option5_present == 5, f"Expected 5 Option 5 migrations present, got {option5_present}"
    # No duplicates
    assert len(seq) == len(set(seq)), f"Duplicate migrations found: {seq}"


def test_postgresql_orm_foreign_key_column_types_are_internally_consistent() -> None:
    """Guard the CI create_all path against UUID/VARCHAR FK drift."""
    dialect = postgresql.dialect()
    mismatches = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            for fk in column.foreign_keys:
                referred = fk.column
                local_type = column.type.compile(dialect=dialect)
                referred_type = referred.type.compile(dialect=dialect)
                if local_type != referred_type:
                    mismatches.append(
                        f"{table.name}.{column.name} {local_type} -> "
                        f"{referred.table.name}.{referred.name} {referred_type}"
                    )
    assert mismatches == []


def test_orchestration_identity_compatibility_migration_covers_known_drift() -> None:
    sql = Path("portal/migrations/align_orchestration_identity_fk_types.sql")
    migration = sql.read_text(encoding="utf-8")
    expected_references = {
        "('orchestration_runs', 'tenant_id', 'tenants', 'id', 'NO ACTION')",
        "('orchestration_runs', 'created_by', 'users', 'id', 'NO ACTION')",
        "('orchestration_approval_requests', 'principal_id', 'users', 'id', 'NO ACTION')",
        "('orchestration_linkages', 'tenant_id', 'tenants', 'id', 'NO ACTION')",
        "('orchestration_principal_authorities', 'tenant_id', 'tenants', 'id', 'NO ACTION')",
        "('orchestration_principal_authorities', 'user_id', 'users', 'id', 'NO ACTION')",
        "('memory_vault', 'tenant_id', 'tenants', 'id', 'CASCADE')",
    }
    assert all(reference in migration for reference in expected_references)
    assert "tenant_id::text = NULLIF(current_setting('app.current_tenant_id'" in migration


def test_postgresql_race_prepare_schema_create_all_path_executes() -> None:
    """Execute the same ORM Base.metadata.create_all path used by postgresql-race CI."""
    url = _database_url()
    with psycopg2.connect(psycopg2_url(url)) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
            cur.execute("CREATE SCHEMA public")

    async def create_schema() -> None:
        engine = create_async_engine(_async_sqlalchemy_url(url), echo=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        finally:
            await engine.dispose()

    asyncio.run(create_schema())


def test_orm_on_raw_sql_uuid_schema_compatibility(migrated_database_url: str) -> None:
    """Prove ORM String(36) models can insert/read through raw-SQL UUID schema.

    The canonical raw-SQL bootstrap creates UUID columns in PostgreSQL.
    The ORM models use String(36) for cross-database compatibility.
    SQLAlchemy must transparently coerce between String(36) and UUID columns.

    Issue #291: Notification.tenant_id and Notification.user_id were
    UUID(as_uuid=True) while Tenant.id and User.id are String(36).
    After the fix, all are String(36) in ORM metadata. This test proves
    the ORM can operate against the raw-SQL UUID schema.
    """
    import uuid as uuid_mod

    from sqlalchemy.ext.asyncio import AsyncSession

    url = migrated_database_url
    async_url = _async_sqlalchemy_url(url)

    tenant_uuid = uuid_mod.uuid4()
    user_uuid = uuid_mod.uuid4()
    notification_uuid = uuid_mod.uuid4()

    # First insert parent rows via raw SQL (as the bootstrap schema expects UUID)
    role_uuid = uuid_mod.uuid4()
    with psycopg2.connect(psycopg2_url(url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (str(tenant_uuid), "ORM Compat Test", f"orm-compat-{tenant_uuid.hex[:12]}"),
            )
            cur.execute(
                """INSERT INTO roles (id, name, description, permissions, is_system)
                   VALUES (%s, %s, %s, %s::text[], %s)""",
                (str(role_uuid), "compat_admin", "Test admin role", "{*}", False),
            )
            cur.execute(
                """INSERT INTO users (id, tenant_id, role_id, email, first_name, last_name, hashed_password)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (str(user_uuid), str(tenant_uuid), str(role_uuid), "compat@test.local", "Test", "User", "hash"),
            )
            conn.commit()

    # Now insert and read via ORM (String(36) types against UUID columns)
    async def orm_roundtrip() -> None:
        engine = create_async_engine(async_url, echo=False)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                from sqlalchemy import select

                from portal.routers.notifications import Notification

                # Insert a Notification via ORM (String(36) FKs into UUID columns)
                notification = Notification(
                    id=notification_uuid,
                    tenant_id=str(tenant_uuid),
                    user_id=str(user_uuid),
                    event_type="test_event",
                    title="ORM Compatibility Test",
                )
                session.add(notification)
                await session.commit()

                # Read back via ORM
                result = await session.execute(
                    select(Notification).where(Notification.id == str(notification_uuid))
                )
                fetched = result.scalar_one()
                assert fetched.event_type == "test_event"
                assert fetched.title == "ORM Compatibility Test"
                # Verify FK values are readable (UUID column coerced to string by ORM)
                assert str(fetched.tenant_id) == str(tenant_uuid)
                assert str(fetched.user_id) == str(user_uuid)

                # Query by tenant_id using ORM filter (String(36) against UUID column)
                result = await session.execute(
                    select(Notification).where(Notification.tenant_id == str(tenant_uuid))
                )
                tenant_notifications = result.scalars().all()
                assert len(tenant_notifications) >= 1
        finally:
            await engine.dispose()

    asyncio.run(orm_roundtrip())


def test_clean_raw_sql_bootstrap_repeats_three_times() -> None:
    url = _database_url()
    for _attempt in range(3):
        apply_migrations(url, reset_public_schema=True)
        with psycopg2.connect(psycopg2_url(url)) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """
                )
                existing = {row[0] for row in cur.fetchall()}
        assert set(EXPECTED_TABLES).issubset(existing)


@pytest.mark.parametrize(
    ("company_name", "first_name", "last_name", "expected_display_name"),
    [
        pytest.param("Acme LLC", "Ada", "Lovelace", "Acme LLC", id="company-name-present"),
        pytest.param("", "Ada", "Lovelace", "Ada Lovelace", id="empty-company-personal-names"),
        pytest.param(None, "Ada", "Lovelace", "Ada Lovelace", id="null-company-personal-names"),
        pytest.param(None, "Ada", None, "Ada ", id="last-null"),
        pytest.param(None, None, "Lovelace", " Lovelace", id="first-null"),
        pytest.param(None, None, None, " ", id="both-names-null"),
        pytest.param(None, "", "Lovelace", " Lovelace", id="empty-first-name"),
        pytest.param(None, "Ada", "", "Ada ", id="empty-last-name"),
        pytest.param("Acme LLC", "Grace", "Hopper", "Acme LLC", id="company-precedence"),
    ],
)
def test_client_display_name_generated_expression_matches_concat_null_semantics(
    migrated_database_url: str,
    company_name: str | None,
    first_name: str | None,
    last_name: str | None,
    expected_display_name: str,
) -> None:
    tenant_id = uuid.uuid4()
    client_id = uuid.uuid4()
    with psycopg2.connect(psycopg2_url(migrated_database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
                (str(tenant_id), "Display Test", f"display-{tenant_id.hex[:12]}"),
            )
            cur.execute(
                """
                SELECT pg_get_expr(adbin, adrelid)
                FROM pg_attrdef
                WHERE adrelid = 'clients'::regclass
                  AND adnum = (
                    SELECT attnum FROM pg_attribute
                    WHERE attrelid = 'clients'::regclass AND attname = 'display_name'
                  )
                """
            )
            expression = cur.fetchone()[0]
            assert "concat" not in expression.lower()
            assert "COALESCE(first_name" in expression
            assert "COALESCE(last_name" in expression

            cur.execute(
                """
                INSERT INTO clients (id, tenant_id, client_type, first_name, last_name, company_name)
                VALUES (%s, %s, 'individual', %s, %s, %s)
                RETURNING display_name
                """,
                (str(client_id), str(tenant_id), first_name, last_name, company_name),
            )
            assert cur.fetchone()[0] == expected_display_name


def test_live_catalog_constraints_and_uuid_authority(migrated_database_url: str) -> None:
    with psycopg2.connect(psycopg2_url(migrated_database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('evidence_snapshots', 'audit_records')
                  AND column_name IN ('snapshot_id', 'case_id', 'created_by', 'audit_id', 'packet_id')
                ORDER BY table_name, column_name
                """
            )
            columns = {(row[0], row[1]): (row[2], row[3]) for row in cur.fetchall()}
            assert columns[("evidence_snapshots", "snapshot_id")] == ("uuid", "NO")
            assert columns[("evidence_snapshots", "case_id")] == ("uuid", "NO")
            assert columns[("evidence_snapshots", "created_by")] == ("uuid", "NO")
            assert columns[("audit_records", "audit_id")] == ("uuid", "NO")
            assert columns[("audit_records", "snapshot_id")] == ("uuid", "NO")
            assert columns[("audit_records", "packet_id")] == ("uuid", "NO")
            assert columns[("audit_records", "created_by")] == ("uuid", "NO")

            cur.execute(
                """
                SELECT conname, contype, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid IN ('evidence_snapshots'::regclass, 'audit_records'::regclass)
                ORDER BY conname
                """
            )
            constraint_defs = "\n".join(
                f"{name}:{kind}:{definition}" for name, kind, definition in cur.fetchall()
            )
            assert "PRIMARY KEY (snapshot_id)" in constraint_defs
            assert "PRIMARY KEY (audit_id)" in constraint_defs
            assert "FOREIGN KEY (case_id) REFERENCES cases(id)" in constraint_defs
            assert "FOREIGN KEY (created_by) REFERENCES users(id)" in constraint_defs
            assert (
                "FOREIGN KEY (snapshot_id) REFERENCES evidence_snapshots(snapshot_id)"
                in constraint_defs
            )
            assert "ON DELETE RESTRICT" in constraint_defs
            assert "CHECK (((status)::text = ANY" in constraint_defs
            assert "CHECK (((verification_status)::text = ANY" in constraint_defs

            cur.execute(
                """
                SELECT tgname, proname
                FROM pg_trigger t
                JOIN pg_proc p ON p.oid = t.tgfoid
                WHERE tgrelid = 'audit_records'::regclass AND NOT tgisinternal
                """
            )
            assert cur.fetchall() == [
                ("trg_audit_record_immutable", "prevent_audit_record_mutation")
            ]

            cur.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename IN ('evidence_snapshots', 'audit_records')
                """
            )
            indexes = {row[0] for row in cur.fetchall()}
            assert "idx_evidence_snapshots_one_active_per_case" in indexes
            assert "idx_audit_records_packet_snapshot" in indexes


def test_real_orm_crud_uuid_binding_and_audit_immutability(migrated_database_url: str) -> None:
    _tenant_id, _client_id, user_id, case_id = _seed_case_user(migrated_database_url)
    engine = create_engine(psycopg2_url(migrated_database_url), future=True)
    snapshot_id = uuid.uuid4()
    packet_id = uuid.uuid4()
    audit_id = uuid.uuid4()

    try:
        with Session(engine) as session:
            snapshot = EvidenceSnapshot(
                snapshot_id=snapshot_id,
                case_id=str(case_id),
                evidence_hash="a" * 64,
                manifest_hash="b" * 64,
                created_by=user_id,
                evidence_count=2,
            )
            session.add(snapshot)
            session.commit()

        with Session(engine) as session:
            found = session.get(EvidenceSnapshot, snapshot_id)
            assert found is not None
            assert found.snapshot_id == snapshot_id
            assert str(found.case_id) == str(case_id)
            assert isinstance(found.snapshot_id, uuid.UUID)
            assert (
                session.scalars(
                    select(EvidenceSnapshot).where(EvidenceSnapshot.case_id == str(case_id))
                )
                .one()
                .snapshot_id
                == snapshot_id
            )

            audit = AuditRecord(
                audit_id=audit_id,
                snapshot_id=str(snapshot_id),
                evidence_hash="a" * 64,
                packet_id=packet_id,
                packet_hash="c" * 64,
                packet_version=1,
                serialization_version=1,
                created_by=str(user_id),
            )
            session.add(audit)
            session.commit()

        with Session(engine) as session:
            found_audit = session.get(AuditRecord, audit_id)
            assert found_audit is not None
            assert found_audit.audit_id == audit_id
            assert found_audit.snapshot_id == snapshot_id
            assert found_audit.packet_id == packet_id

        with Session(engine) as session:
            session.add(
                EvidenceSnapshot(
                    snapshot_id=uuid.uuid4(),
                    case_id=uuid.uuid4(),
                    evidence_hash="d" * 64,
                    manifest_hash="e" * 64,
                    created_by=user_id,
                )
            )
            with pytest.raises(Exception, match=r"ForeignKeyViolation|foreign key"):
                session.commit()
            session.rollback()

        with Session(engine) as session:
            with pytest.raises(Exception, match="audit_records rows cannot be modified"):
                session.execute(
                    text(
                        "UPDATE audit_records SET verification_status = 'failed' WHERE audit_id = :audit_id"
                    ),
                    {"audit_id": audit_id},
                )
            session.rollback()

        with Session(engine) as session:
            with pytest.raises(Exception, match="audit_records rows cannot be deleted"):
                session.execute(
                    text("DELETE FROM audit_records WHERE audit_id = :audit_id"),
                    {"audit_id": audit_id},
                )
            session.rollback()

        with Session(engine) as session:
            session.add(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    snapshot_id=snapshot_id,
                    evidence_hash="f" * 64,
                    packet_id=uuid.uuid4(),
                    packet_hash="f" * 64,
                    packet_version=1,
                    created_by=user_id,
                )
            )
            session.flush()
            session.rollback()
            assert (
                session.scalar(select(AuditRecord).where(AuditRecord.evidence_hash == "f" * 64))
                is None
            )
    finally:
        engine.dispose()
