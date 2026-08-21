"""Gate 4C PostgreSQL certification for the provider-owned HTTP boundary."""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from portal.models.external_action_sandbox import (
    ExternalActionIntent,
    ExternalProviderAttempt,
    ExternalProviderCredentialLease,
    ExternalProviderRateBucket,
)
from portal.scripts.postgresql_bootstrap import PROVIDER_GATE_MIGRATION_SEQUENCE, apply_migrations
from portal.services.postman_echo_provider_adapter import (
    ADAPTER_ID,
    APPROVED_URL,
    ProviderBoundaryError,
    ProviderReceipt,
    postman_echo_provider_adapter,
)
from portal.services.restricted_external_action import (
    ExternalActionAuthorityError,
    approve_external_intent,
    compensate_external_intent,
    create_external_intent,
    execute_external_intent,
    issue_provider_credential_lease,
    preflight_external_intent,
    reconcile_external_intent,
    revoke_provider_credential_lease,
    set_external_kill_switch,
    verify_external_evidence_chain,
)

pytestmark = [pytest.mark.postgresql, pytest.mark.integration]

TENANT_A = "00000000-0000-0000-0000-000000004485"
TENANT_B = "00000000-0000-0000-0000-000000004486"
PRINCIPAL_A = "00000000-0000-0000-0000-000000004585"
PRINCIPAL_B = "00000000-0000-0000-0000-000000004586"
IDENTITY_A = "svc-gate4c-primary"
IDENTITY_B = "svc-gate4c-tenant-b"
CAPABILITY = f"external:{ADAPTER_ID}:echo_write"
CREDENTIAL_REF = "env:GATE4C_POSTMAN_ECHO_TOKEN"
SYNTHETIC_TOKEN = "gate4c-synthetic-provider-token-not-a-secret"


def _database_url() -> str:
    raw = os.environ.get("GATE4C_PROVIDER_AUTHORITY_DATABASE_URL")
    if not raw:
        pytest.skip("Gate 4C PostgreSQL URL not configured")
    return raw


async def _sessionmaker() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    database_url = _database_url()
    apply_migrations(database_url, reset_public_schema=True)
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession), engine


async def _seed(maker: async_sessionmaker[AsyncSession]) -> None:
    os.environ[CREDENTIAL_REF.removeprefix("env:")] = SYNTHETIC_TOKEN
    async with maker() as db:
        role_id = await db.scalar(text("SELECT id FROM roles WHERE name = 'SUPER_ADMIN'"))
        assert role_id is not None
        for tenant_id, name, slug in (
            (TENANT_A, "Gate 4C A", "gate4c-a"),
            (TENANT_B, "Gate 4C B", "gate4c-b"),
        ):
            await db.execute(
                text("INSERT INTO tenants (id, name, slug) VALUES (CAST(:id AS uuid), :name, :slug)"),
                {"id": tenant_id, "name": name, "slug": slug},
            )
        for principal_id, tenant_id, email in (
            (PRINCIPAL_A, TENANT_A, "gate4c-a@example.invalid"),
            (PRINCIPAL_B, TENANT_B, "gate4c-b@example.invalid"),
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
        for identity_id, tenant_id, principal_id in (
            (IDENTITY_A, TENANT_A, PRINCIPAL_A),
            (IDENTITY_B, TENANT_B, PRINCIPAL_B),
        ):
            await db.execute(
                text(
                    """
                    INSERT INTO governed_service_identities (
                        id, tenant_id, created_by, display_name, agent_id, credential_ref,
                        scopes, scoped_folders, allowed_capabilities, status,
                        idempotency_key, request_hash, expires_at
                    ) VALUES (
                        :id, CAST(:tenant_id AS uuid), CAST(:created_by AS uuid), :display_name,
                        'gate4c-certifier', NULL, '[]'::jsonb,
                        CAST(:scoped_folders AS jsonb), CAST(:capabilities AS jsonb),
                        'ACTIVE', :idempotency_key, :request_hash, :expires_at
                    )
                    """
                ),
                {
                    "id": identity_id,
                    "tenant_id": tenant_id,
                    "created_by": principal_id,
                    "display_name": identity_id,
                    "scoped_folders": f'["{APPROVED_URL}"]',
                    "capabilities": f'["{CAPABILITY}"]',
                    "idempotency_key": f"{identity_id}-idem-0001",
                    "request_hash": hashlib.sha256(identity_id.encode()).hexdigest(),
                    "expires_at": expires_at,
                },
            )
        await db.commit()


async def _lease(
    db: AsyncSession,
    *,
    tenant_id: str = TENANT_A,
    principal_id: str = PRINCIPAL_A,
    identity_id: str = IDENTITY_A,
    rate_limit_per_minute: int = 5,
) -> dict:
    return await issue_provider_credential_lease(
        db,
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=identity_id,
        credential_ref=CREDENTIAL_REF,
        expires_at=datetime.now(UTC) + timedelta(minutes=45),
        rate_limit_per_minute=rate_limit_per_minute,
    )


async def _approved_provider_intent(
    db: AsyncSession,
    *,
    lease_id: str,
    idempotency_key: str,
    tenant_id: str = TENANT_A,
    principal_id: str = PRINCIPAL_A,
    identity_id: str = IDENTITY_A,
    payload: dict | None = None,
    schedule_id: str | None = None,
) -> dict:
    intent = await create_external_intent(
        db,
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=identity_id,
        adapter_id=ADAPTER_ID,
        credential_lease_id=lease_id,
        destination=APPROVED_URL,
        payload=payload or {"gate": "4c", "message": idempotency_key},
        payload_summary="Provider-owned Postman Echo certification",
        idempotency_key=idempotency_key,
        schedule_id=schedule_id,
    )
    await preflight_external_intent(db, tenant_id=tenant_id, intent_id=intent["intent_id"])
    return await approve_external_intent(
        db,
        tenant_id=tenant_id,
        intent_id=intent["intent_id"],
        principal_id=principal_id,
        approval_nonce=f"approval-{idempotency_key}",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )


def _receipt(payload: dict, suffix: str = "ok") -> ProviderReceipt:
    payload_hash = hashlib.sha256(
        __import__("json").dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    response_hash = hashlib.sha256(f"response-{suffix}".encode()).hexdigest()
    return ProviderReceipt(
        status=200,
        payload_hash=payload_hash,
        response_hash=response_hash,
        resolved_ips=("8.8.8.8",),
        provider_url=APPROVED_URL,
    )


def test_gate4c_bootstrap_extension_is_separate_from_gate4b() -> None:
    paths = [str(path).replace("\\", "/") for path in PROVIDER_GATE_MIGRATION_SEQUENCE]
    assert paths == ["portal/migrations/extend_external_action_provider_test.sql"]
    assert ADAPTER_ID == "provider.postman-echo-v1"


@pytest.mark.asyncio
async def test_gate4c_credential_lease_revocation_expiry_and_cross_tenant_denial() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        async with maker() as db:
            lease = await _lease(db)
            raw = await db.execute(
                text(
                    "SELECT credential_ref, credential_fingerprint "
                    "FROM external_provider_credential_leases WHERE id=:id"
                ),
                {"id": lease["lease_id"]},
            )
            credential_ref, fingerprint = raw.one()
            assert credential_ref == CREDENTIAL_REF
            assert SYNTHETIC_TOKEN not in credential_ref
            assert SYNTHETIC_TOKEN not in fingerprint
            assert fingerprint == hashlib.sha256(SYNTHETIC_TOKEN.encode()).hexdigest()

            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-revoked-0001",
            )
            await revoke_provider_credential_lease(
                db,
                tenant_id=TENANT_A,
                lease_id=lease["lease_id"],
                principal_id=PRINCIPAL_A,
                reason="Gate 4C revocation certification",
            )
            with pytest.raises(ExternalActionAuthorityError, match="revoked"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="revoked-lease-worker",
                )
            await db.commit()

        async with maker() as db:
            lease = await _lease(db)
            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-expired-0001",
            )
            await db.execute(
                text("UPDATE external_provider_credential_leases SET expires_at=NOW()-INTERVAL '1 minute' WHERE id=:id"),
                {"id": lease["lease_id"]},
            )
            with pytest.raises(ExternalActionAuthorityError, match="expired"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="expired-lease-worker",
                )
            await db.commit()

        async with maker() as db:
            lease = await _lease(db)
            cross = await create_external_intent(
                db,
                tenant_id=TENANT_B,
                principal_id=PRINCIPAL_B,
                service_identity_id=IDENTITY_B,
                adapter_id=ADAPTER_ID,
                credential_lease_id=lease["lease_id"],
                destination=APPROVED_URL,
                payload={"gate": "4c", "cross_tenant": True},
                payload_summary="Must not cross tenant boundary",
                idempotency_key="gate4c-cross-tenant-0001",
            )
            with pytest.raises(ExternalActionAuthorityError, match="lease"):
                await preflight_external_intent(
                    db,
                    tenant_id=TENANT_B,
                    intent_id=cross["intent_id"],
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4c_exact_approval_mutation_scheduler_and_kill_switch(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        async with maker() as db:
            lease = await _lease(db)
            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-mutation-0001",
            )
            with pytest.raises(ExternalActionAuthorityError, match="payload differs"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="payload-mutation-worker",
                    execution_payload={"gate": "4c", "mutated": True},
                )
            with pytest.raises(ExternalActionAuthorityError, match="destination differs"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="destination-mutation-worker",
                    execution_destination="https://postman-echo.com/get",
                )

            scheduled = await create_external_intent(
                db,
                tenant_id=TENANT_A,
                principal_id=PRINCIPAL_A,
                service_identity_id=IDENTITY_A,
                adapter_id=ADAPTER_ID,
                credential_lease_id=lease["lease_id"],
                destination=APPROVED_URL,
                payload={"gate": "4c", "scheduled": True},
                payload_summary="Schedule provenance has no provider authority",
                idempotency_key="gate4c-scheduler-no-bypass-0001",
                schedule_id="sch-gate4c-synthetic",
            )
            await preflight_external_intent(db, tenant_id=TENANT_A, intent_id=scheduled["intent_id"])
            with pytest.raises(ExternalActionAuthorityError, match="not executable"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=scheduled["intent_id"],
                    worker_id="scheduler-worker",
                )

            killed = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-kill-0001",
            )
            await set_external_kill_switch(
                db,
                scope_key=f"ADAPTER:{ADAPTER_ID}",
                active=True,
                updated_by=PRINCIPAL_A,
                reason="Gate 4C adapter kill certification",
                adapter_id=ADAPTER_ID,
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
                scope_key=f"ADAPTER:{ADAPTER_ID}",
                active=False,
                updated_by=PRINCIPAL_A,
                reason="Resume provider test",
                adapter_id=ADAPTER_ID,
            )
            await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4c_durable_rate_limit_and_provider_429(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def fake_execute_once(*, payload, **kwargs):
        nonlocal calls
        calls += 1
        return _receipt(payload, suffix=str(calls))

    try:
        await _seed(maker)
        monkeypatch.setattr(postman_echo_provider_adapter, "execute_once", fake_execute_once)
        async with maker() as db:
            lease = await _lease(db, rate_limit_per_minute=1)
            first = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-rate-first-0001",
            )
            await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=first["intent_id"],
                worker_id="rate-first-worker",
            )
            second = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-rate-second-0001",
            )
            with pytest.raises(ExternalActionAuthorityError, match="rate limit exceeded"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=second["intent_id"],
                    worker_id="rate-second-worker",
                )
            assert calls == 1
            bucket_count = await db.scalar(select(func.count()).select_from(ExternalProviderRateBucket))
            assert bucket_count == 1
            await db.commit()

        async def provider_429(**kwargs):
            raise ProviderBoundaryError("Provider rate limit returned 429")

        monkeypatch.setattr(postman_echo_provider_adapter, "execute_once", provider_429)
        async with maker() as db:
            lease = await _lease(db, rate_limit_per_minute=5)
            intent = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-provider-429-0001",
            )
            with pytest.raises(ExternalActionAuthorityError, match="429"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=intent["intent_id"],
                    worker_id="provider-429-worker",
                )
            attempt = await db.scalar(
                select(ExternalProviderAttempt).where(
                    ExternalProviderAttempt.intent_id == intent["intent_id"]
                )
            )
            assert attempt is not None and attempt.outcome == "RATE_LIMITED"
            stored = await db.get(ExternalActionIntent, intent["intent_id"])
            assert stored is not None and stored.status == "FAILED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4c_timeout_restart_reconciliation_and_no_blind_retry(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def timeout_once(**kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("synthetic provider timeout")

    try:
        await _seed(maker)
        monkeypatch.setattr(postman_echo_provider_adapter, "execute_once", timeout_once)
        async with maker() as db:
            lease = await _lease(db)
            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-timeout-0001",
            )
            result = await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
                worker_id="timeout-worker",
            )
            assert result["status"] == "UNKNOWN_REQUIRES_RECONCILIATION"
            assert calls == 1
            await db.commit()

        async with maker() as db:
            with pytest.raises(ExternalActionAuthorityError, match="requires reconciliation"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="blind-retry-worker",
                )
            reconciled = await reconcile_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
            )
            assert reconciled["status"] == "FAILED"
            assert reconciled["reconciled"] is True
            assert calls == 1
            assert reconciled["events"][-1]["event_payload"]["network_retry_performed"] is False
            await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4c_concurrent_duplicate_suppression_evidence_and_logical_compensation(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def slow_success(*, payload, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return _receipt(payload, suffix="concurrent")

    try:
        await _seed(maker)
        monkeypatch.setattr(postman_echo_provider_adapter, "execute_once", slow_success)
        async with maker() as db:
            lease = await _lease(db, rate_limit_per_minute=5)
            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-concurrent-0001",
            )
            intent_id = approved["intent_id"]
            await db.commit()

        async def execute(worker_id: str) -> dict:
            async with maker() as db:
                result = await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=intent_id,
                    worker_id=worker_id,
                )
                await db.commit()
                return result

        first, second = await asyncio.gather(execute("worker-a"), execute("worker-b"))
        assert calls == 1
        assert {first["duplicate"], second["duplicate"]} == {False, True}
        assert first["provider"]["response_hash"] == second["provider"]["response_hash"]

        async with maker() as db:
            attempts = await db.scalar(
                select(func.count()).select_from(ExternalProviderAttempt).where(
                    ExternalProviderAttempt.intent_id == intent_id
                )
            )
            assert attempts == 1
            attempt = await db.scalar(
                select(ExternalProviderAttempt).where(ExternalProviderAttempt.intent_id == intent_id)
            )
            assert attempt is not None
            assert attempt.request_hash and attempt.response_hash
            assert attempt.provider_url == APPROVED_URL
            chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=intent_id,
            )
            assert chain["valid"] is True

            compensated = await compensate_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=intent_id,
                principal_id=PRINCIPAL_A,
                reason="Gate 4C logical compensation certification",
            )
            assert compensated["status"] == "COMPENSATED"
            assert compensated["logical_compensation"] is True
            event = compensated["events"][-1]["event_payload"]
            assert event["provider_rollback_required"] is False
            assert event["network_call_performed"] is False
            await db.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4c_real_postman_echo_through_durable_authority() -> None:
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        async with maker() as db:
            lease = await _lease(db, rate_limit_per_minute=5)
            approved = await _approved_provider_intent(
                db,
                lease_id=lease["lease_id"],
                idempotency_key="gate4c-live-authority-0001",
                payload={"gate": "4c", "purpose": "durable-authority-live-boundary"},
            )
            result = await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
                worker_id="gate4c-live-worker",
                timeout_seconds=15.0,
            )
            assert result["status"] == "SUCCEEDED"
            assert result["provider"]["provider_status"] == 200
            assert result["provider"]["provider_url"] == APPROVED_URL
            assert result["provider"]["response_hash"]
            chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
            )
            assert chain["valid"] is True
            await db.commit()
    finally:
        await engine.dispose()
