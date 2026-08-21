"""Gate 4B PostgreSQL certification for the disposable E1 external-action sandbox."""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from portal.models.external_action_sandbox import SandboxEchoEffect
from portal.scripts.postgresql_bootstrap import (
    PRODUCTION_GATE_MIGRATION_SEQUENCE,
    apply_migrations,
)
from portal.services.restricted_external_action import (
    ExternalActionAuthorityError,
    approve_external_intent,
    compensate_external_intent,
    create_external_intent,
    execute_external_intent,
    preflight_external_intent,
    reconcile_external_intent,
    set_external_kill_switch,
    verify_external_evidence_chain,
)
from portal.services.sandbox_echo_adapter import ADAPTER_ID, SandboxAdapterError, sandbox_echo_adapter

pytestmark = pytest.mark.postgresql

TENANT_A = "00000000-0000-0000-0000-000000004285"
TENANT_B = "00000000-0000-0000-0000-000000004286"
PRINCIPAL_A = "00000000-0000-0000-0000-000000004385"
PRINCIPAL_B = "00000000-0000-0000-0000-000000004386"
IDENTITY_A = "svc-gate4b-primary"
IDENTITY_REVOKED = "svc-gate4b-revoked"
DESTINATION_A = "sandbox://gate4b/target-a"
CAPABILITY = "external:sandbox.echo-write-v1:echo_write"


def _database_url() -> str:
    raw = os.environ.get("RESTRICTED_EXTERNAL_ACTION_DATABASE_URL")
    if not raw:
        pytest.skip("Gate 4B PostgreSQL URL not configured")
    return raw


async def _sessionmaker() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    database_url = _database_url()
    apply_migrations(database_url, reset_public_schema=True)
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession), engine


async def _seed(maker: async_sessionmaker[AsyncSession]) -> None:
    async with maker() as db:
        role_id = await db.scalar(text("SELECT id FROM roles WHERE name = 'SUPER_ADMIN'"))
        assert role_id is not None
        for tenant_id, name, slug in (
            (TENANT_A, "Gate 4B A", "gate4b-a"),
            (TENANT_B, "Gate 4B B", "gate4b-b"),
        ):
            await db.execute(
                text("INSERT INTO tenants (id, name, slug) VALUES (CAST(:id AS uuid), :name, :slug)"),
                {"id": tenant_id, "name": name, "slug": slug},
            )
        for principal_id, tenant_id, email in (
            (PRINCIPAL_A, TENANT_A, "gate4b-a@example.invalid"),
            (PRINCIPAL_B, TENANT_B, "gate4b-b@example.invalid"),
        ):
            await db.execute(
                text(
                    """
                    INSERT INTO users (
                        id, tenant_id, role_id, email, first_name, last_name, hashed_password
                    ) VALUES (
                        CAST(:id AS uuid), CAST(:tenant_id AS uuid), CAST(:role_id AS uuid),
                        :email, 'Gate', 'Principal', 'synthetic-not-a-real-password'
                    )
                    """
                ),
                {
                    "id": principal_id,
                    "tenant_id": tenant_id,
                    "role_id": str(role_id),
                    "email": email,
                },
            )
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        for identity_id in (IDENTITY_A, IDENTITY_REVOKED):
            await db.execute(
                text(
                    """
                    INSERT INTO governed_service_identities (
                        id, tenant_id, created_by, display_name, agent_id, credential_ref,
                        scopes, scoped_folders, allowed_capabilities, status,
                        idempotency_key, request_hash, expires_at
                    ) VALUES (
                        :id, CAST(:tenant_id AS uuid), CAST(:created_by AS uuid), :display_name,
                        'gate4b-certifier', NULL, '[]'::jsonb,
                        CAST(:scoped_folders AS jsonb), CAST(:capabilities AS jsonb),
                        'ACTIVE', :idempotency_key, :request_hash, :expires_at
                    )
                    """
                ),
                {
                    "id": identity_id,
                    "tenant_id": TENANT_A,
                    "created_by": PRINCIPAL_A,
                    "display_name": identity_id,
                    "scoped_folders": f'["{DESTINATION_A}"]',
                    "capabilities": f'["{CAPABILITY}"]',
                    "idempotency_key": f"{identity_id}-idem-0001",
                    "request_hash": hashlib.sha256(identity_id.encode()).hexdigest(),
                    "expires_at": expires_at,
                },
            )
        await db.commit()


async def _approved_intent(
    db: AsyncSession,
    *,
    idempotency_key: str,
    identity_id: str = IDENTITY_A,
    payload: dict | None = None,
    destination: str = DESTINATION_A,
    schedule_id: str | None = None,
) -> dict:
    intent = await create_external_intent(
        db,
        tenant_id=TENANT_A,
        principal_id=PRINCIPAL_A,
        service_identity_id=identity_id,
        destination=destination,
        payload=payload or {"message": "gate4b-certified"},
        payload_summary="Synthetic sandbox echo write",
        idempotency_key=idempotency_key,
        schedule_id=schedule_id,
    )
    intent = await preflight_external_intent(
        db,
        tenant_id=TENANT_A,
        intent_id=intent["intent_id"],
    )
    return await approve_external_intent(
        db,
        tenant_id=TENANT_A,
        intent_id=intent["intent_id"],
        principal_id=PRINCIPAL_A,
        approval_nonce=f"approval-{idempotency_key}",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )


def test_gate4b_is_last_authoritative_bootstrap_gate_and_adapter_is_sandbox_only() -> None:
    paths = [str(path).replace("\\", "/") for path in PRODUCTION_GATE_MIGRATION_SEQUENCE]
    assert paths[-1] == "portal/migrations/add_external_action_sandbox_domain.sql"
    assert paths.count("portal/migrations/add_external_action_sandbox_domain.sql") == 1
    assert ADAPTER_ID == "sandbox.echo-write-v1"
    receipt = sandbox_echo_adapter.preflight(
        destination=DESTINATION_A,
        payload={"message": "dry-run"},
    )
    assert receipt["network_access"] is False
    assert receipt["credential_access"] is False
    assert receipt["production_reachable"] is False
    with pytest.raises(SandboxAdapterError):
        sandbox_echo_adapter.preflight(
            destination="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            payload={"message": "must never send"},
        )


@pytest.mark.asyncio
async def test_gate4b_rejects_mutation_revocation_scheduler_bypass_kill_switch_and_cross_tenant() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)

        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4b-mutation-0001")
            with pytest.raises(ExternalActionAuthorityError, match="payload differs"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="mutation-worker",
                    execution_payload={"message": "mutated-after-approval"},
                )
            with pytest.raises(ExternalActionAuthorityError, match="destination differs"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="destination-worker",
                    execution_destination="sandbox://gate4b/target-b",
                )
            await db.commit()

        async with maker() as db:
            scheduled = await create_external_intent(
                db,
                tenant_id=TENANT_A,
                principal_id=PRINCIPAL_A,
                service_identity_id=IDENTITY_A,
                destination=DESTINATION_A,
                payload={"message": "scheduled-but-not-approved"},
                payload_summary="Schedule provenance carries no execution authority",
                idempotency_key="gate4b-scheduler-non-bypass-0001",
                schedule_id="sch-synthetic-gate4b",
            )
            await preflight_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=scheduled["intent_id"],
            )
            with pytest.raises(ExternalActionAuthorityError, match="not executable"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=scheduled["intent_id"],
                    worker_id="scheduler-worker",
                )
            await db.commit()

        async with maker() as db:
            revoked = await _approved_intent(
                db,
                idempotency_key="gate4b-revoked-identity-0001",
                identity_id=IDENTITY_REVOKED,
            )
            await db.execute(
                text(
                    "UPDATE governed_service_identities "
                    "SET status='REVOKED', revoked_at=NOW(), revocation_reason='Gate 4B test' "
                    "WHERE id=:id"
                ),
                {"id": IDENTITY_REVOKED},
            )
            with pytest.raises(ExternalActionAuthorityError, match="revoked"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=revoked["intent_id"],
                    worker_id="revocation-worker",
                )
            await db.commit()

        async with maker() as db:
            killed = await _approved_intent(db, idempotency_key="gate4b-kill-switch-0001")
            await set_external_kill_switch(
                db,
                scope_key="GLOBAL",
                active=True,
                updated_by=PRINCIPAL_A,
                reason="Gate 4B global stop certification",
            )
            with pytest.raises(ExternalActionAuthorityError, match="kill switch"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=killed["intent_id"],
                    worker_id="kill-switch-worker",
                )
            await set_external_kill_switch(
                db,
                scope_key="GLOBAL",
                active=False,
                updated_by=PRINCIPAL_A,
                reason="Resume after certification",
            )
            await db.commit()

        async with maker() as db:
            cross_tenant = await _approved_intent(db, idempotency_key="gate4b-cross-tenant-0001")
            await db.commit()
        async with maker() as db:
            with pytest.raises(ExternalActionAuthorityError, match="not found"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_B,
                    intent_id=cross_tenant["intent_id"],
                    worker_id="tenant-b-worker",
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4b_restart_reconciliation_concurrent_duplicate_suppression_and_compensation() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)

        async with maker() as db:
            ambiguous = await _approved_intent(db, idempotency_key="gate4b-ambiguous-0001")
            result = await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=ambiguous["intent_id"],
                worker_id="ambiguous-worker",
                simulate_ambiguous_after_write=True,
            )
            assert result["status"] == "UNKNOWN_REQUIRES_RECONCILIATION"
            assert result["provider"] is None
            await db.commit()

        # New session simulates restart. Reconciliation must discover the existing
        # provider-side effect rather than retrying the write.
        async with maker() as db:
            reconciled = await reconcile_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=ambiguous["intent_id"],
            )
            assert reconciled["status"] == "SUCCEEDED"
            assert reconciled["reconciled"] is True
            chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=ambiguous["intent_id"],
            )
            assert chain["valid"] is True
            assert chain["event_count"] >= 6
            effect_count = await db.scalar(
                select(func.count()).select_from(SandboxEchoEffect).where(
                    SandboxEchoEffect.tenant_id == TENANT_A,
                    SandboxEchoEffect.idempotency_key == "gate4b-ambiguous-0001",
                )
            )
            assert effect_count == 1
            await db.commit()

        async with maker() as db:
            concurrent = await _approved_intent(db, idempotency_key="gate4b-concurrent-0001")
            concurrent_id = concurrent["intent_id"]
            await db.commit()

        async def _execute(worker_id: str) -> dict:
            async with maker() as db:
                result = await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=concurrent_id,
                    worker_id=worker_id,
                )
                await db.commit()
                return result

        first, second = await asyncio.gather(
            _execute("concurrent-worker-a"),
            _execute("concurrent-worker-b"),
        )
        assert first["provider"]["confirmation_id"] == second["provider"]["confirmation_id"]
        assert {first["duplicate"], second["duplicate"]} == {False, True}

        async with maker() as db:
            effect_count = await db.scalar(
                select(func.count()).select_from(SandboxEchoEffect).where(
                    SandboxEchoEffect.tenant_id == TENANT_A,
                    SandboxEchoEffect.idempotency_key == "gate4b-concurrent-0001",
                )
            )
            assert effect_count == 1
            chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=concurrent_id,
            )
            assert chain["valid"] is True

            compensated = await compensate_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=concurrent_id,
                principal_id=PRINCIPAL_A,
                reason="Gate 4B reversible-write compensation certification",
            )
            assert compensated["status"] == "COMPENSATED"
            assert compensated["provider"]["compensated"] is True
            compensated_chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=concurrent_id,
            )
            assert compensated_chain["valid"] is True
            assert compensated["events"][-1]["event_type"] == "COMPENSATION_COMPLETED"
            await db.commit()
    finally:
        await engine.dispose()
