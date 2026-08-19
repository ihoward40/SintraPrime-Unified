"""PostgreSQL certification for durable governed service identities."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest

from portal.scripts.postgresql_bootstrap import (
    PRODUCTION_GATE_MIGRATION_SEQUENCE,
    apply_migrations,
    psycopg2_url,
)

pytestmark = pytest.mark.postgresql


def _database_url() -> str:
    url = os.environ.get("POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL bootstrap certification database URL not configured")
    return url


def _seed_principal(url: str) -> tuple[str, str]:
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s)",
            (tenant_id, "Identity Gate", f"identity-{tenant_id[:8]}"),
        )
        cur.execute("SELECT id FROM roles WHERE name = 'FIRM_ADMIN'")
        role_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO users (id, tenant_id, role_id, email, first_name, last_name, hashed_password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                tenant_id,
                str(role_id),
                f"identity-{user_id[:8]}@example.invalid",
                "Identity",
                "Principal",
                "synthetic-not-a-real-password",
            ),
        )
    return tenant_id, user_id


def test_durable_identity_gate_is_in_authoritative_bootstrap() -> None:
    assert [str(path).replace("\\", "/") for path in PRODUCTION_GATE_MIGRATION_SEQUENCE] == [
        "portal/migrations/add_governed_service_identities.sql"
    ]


def test_service_identity_survives_reconnect_and_revocation_is_durable() -> None:
    url = _database_url()
    apply_migrations(url, reset_public_schema=True)
    tenant_id, user_id = _seed_principal(url)
    identity_id = f"svc-{uuid.uuid4().hex[:12]}"
    idempotency_key = "identity-gate-postgresql-0001"
    expires_at = datetime.now(UTC) + timedelta(minutes=30)

    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO governed_service_identities (
                id, tenant_id, created_by, display_name, agent_id,
                scopes, scoped_folders, allowed_capabilities, status,
                idempotency_key, request_hash, expires_at
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
            """,
            (
                identity_id,
                tenant_id,
                user_id,
                "Durable Identity",
                "gate-agent",
                '["runtime:side-effect"]',
                '[]',
                '["computer_control"]',
                "ACTIVE",
                idempotency_key,
                "a" * 64,
                expires_at,
            ),
        )

    # New connection simulates process/repository restart: authority still exists.
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, scopes, allowed_capabilities, credential_ref
            FROM governed_service_identities
            WHERE id = %s AND tenant_id = %s
            """,
            (identity_id, tenant_id),
        )
        status, scopes, capabilities, credential_ref = cur.fetchone()
        assert status == "ACTIVE"
        assert scopes == ["runtime:side-effect"]
        assert capabilities == ["computer_control"]
        assert credential_ref is None
        cur.execute(
            """
            UPDATE governed_service_identities
            SET status = 'REVOKED', revoked_at = NOW(), revocation_reason = %s
            WHERE id = %s AND tenant_id = %s
            """,
            ("Gate certification complete", identity_id, tenant_id),
        )

    # Revocation also survives reconnect and cannot be confused with active authority.
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, revoked_at, revocation_reason FROM governed_service_identities WHERE id = %s",
            (identity_id,),
        )
        status, revoked_at, reason = cur.fetchone()
        assert status == "REVOKED"
        assert revoked_at is not None
        assert reason == "Gate certification complete"


def test_service_identity_idempotency_constraint_rejects_duplicate_authority() -> None:
    url = _database_url()
    apply_migrations(url, reset_public_schema=True)
    tenant_id, user_id = _seed_principal(url)
    expires_at = datetime.now(UTC) + timedelta(minutes=30)
    key = "identity-gate-postgresql-0002"

    insert_sql = """
        INSERT INTO governed_service_identities (
            id, tenant_id, created_by, display_name, scopes, scoped_folders,
            allowed_capabilities, status, idempotency_key, request_hash, expires_at
        ) VALUES (%s, %s, %s, %s, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'ACTIVE', %s, %s, %s)
    """
    with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
        cur.execute(
            insert_sql,
            (f"svc-{uuid.uuid4().hex[:12]}", tenant_id, user_id, "First", key, "b" * 64, expires_at),
        )

    with pytest.raises(psycopg2.errors.UniqueViolation):
        with psycopg2.connect(psycopg2_url(url)) as conn, conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    f"svc-{uuid.uuid4().hex[:12]}",
                    tenant_id,
                    user_id,
                    "Duplicate",
                    key,
                    "c" * 64,
                    expires_at,
                ),
            )
