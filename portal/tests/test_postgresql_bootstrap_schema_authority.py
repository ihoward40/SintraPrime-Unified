"""PostgreSQL raw-SQL bootstrap and affected ORM authority certification."""
from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

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
    url = os.environ.get("POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL"
    )
    if not url:
        pytest.skip("PostgreSQL bootstrap certification database URL not configured")
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
                (str(case_id), str(tenant_id), str(client_id), str(user_id), f"PRB-{case_id.hex[:8]}", "PR-B Bootstrap Case"),
            )
    return tenant_id, client_id, user_id, case_id


def test_authoritative_migration_sequence_is_ordered() -> None:
    assert [str(path).replace("\\", "/") for path in MIGRATION_SEQUENCE] == [
        "portal/migrations/portal_schema.sql",
        "portal/migrations/add_evidence_snapshots.sql",
        "portal/migrations/add_audit_records.sql",
        "portal/migrations/add_mission_control_command_ledger.sql",
        "portal/migrations/add_mission_control_run_control_projection.sql",
    ]


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
            constraint_defs = "\n".join(f"{name}:{kind}:{definition}" for name, kind, definition in cur.fetchall())
            assert "PRIMARY KEY (snapshot_id)" in constraint_defs
            assert "PRIMARY KEY (audit_id)" in constraint_defs
            assert "FOREIGN KEY (case_id) REFERENCES cases(id)" in constraint_defs
            assert "FOREIGN KEY (created_by) REFERENCES users(id)" in constraint_defs
            assert "FOREIGN KEY (snapshot_id) REFERENCES evidence_snapshots(snapshot_id)" in constraint_defs
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
            assert cur.fetchall() == [("trg_audit_record_immutable", "prevent_audit_record_mutation")]

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
            assert found.case_id == case_id
            assert isinstance(found.snapshot_id, uuid.UUID)
            assert session.scalars(
                select(EvidenceSnapshot).where(EvidenceSnapshot.case_id == str(case_id))
            ).one().snapshot_id == snapshot_id

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
                session.execute(text("UPDATE audit_records SET verification_status = 'failed' WHERE audit_id = :audit_id"), {"audit_id": audit_id})
            session.rollback()

        with Session(engine) as session:
            with pytest.raises(Exception, match="audit_records rows cannot be deleted"):
                session.execute(text("DELETE FROM audit_records WHERE audit_id = :audit_id"), {"audit_id": audit_id})
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
            assert session.scalar(select(AuditRecord).where(AuditRecord.evidence_hash == "f" * 64)) is None
    finally:
        engine.dispose()
