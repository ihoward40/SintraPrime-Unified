"""Gate 4D-B PostgreSQL certification for public GitHub repository metadata reads."""

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

from portal.models.external_action_sandbox import (
    ExternalActionIntent,
    ExternalProviderAttempt,
    ExternalProviderCredentialLease,
    ExternalProviderRateBucket,
)
from portal.scripts.postgresql_bootstrap import READONLY_GATE_MIGRATION_SEQUENCE, apply_migrations
from portal.services.github_metadata_read_adapter import (
    ADAPTER_ID,
    APPROVED_PAYLOAD,
    APPROVED_URL,
    ENVIRONMENT,
    GitHubMetadataReceipt,
    OPERATION_ID,
    RISK_CLASS,
    github_metadata_read_adapter,
)
from portal.services.postman_echo_provider_adapter import ProviderBoundaryError
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

pytestmark = [pytest.mark.postgresql, pytest.mark.integration]

TENANT_A = "00000000-0000-0000-0000-000000004d01"
TENANT_B = "00000000-0000-0000-0000-000000004d02"
PRINCIPAL_A = "00000000-0000-0000-0000-000000004e01"
PRINCIPAL_B = "00000000-0000-0000-0000-000000004e02"
IDENTITY_A = "svc-gate4d-github-a"
IDENTITY_B = "svc-gate4d-github-b"
CAPABILITY = f"external:{ADAPTER_ID}:{OPERATION_ID}"


def _database_url() -> str:
    raw = os.environ.get("GATE4D_GITHUB_DATABASE_URL")
    if not raw:
        pytest.skip("Gate 4D-B PostgreSQL URL not configured")
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
            (TENANT_A, "Gate 4D A", "gate4d-a"),
            (TENANT_B, "Gate 4D B", "gate4d-b"),
        ):
            await db.execute(
                text("INSERT INTO tenants (id, name, slug) VALUES (CAST(:id AS uuid), :name, :slug)"),
                {"id": tenant_id, "name": name, "slug": slug},
            )
        for principal_id, tenant_id, email in (
            (PRINCIPAL_A, TENANT_A, "gate4d-a@example.invalid"),
            (PRINCIPAL_B, TENANT_B, "gate4d-b@example.invalid"),
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
                        'gate4d-certifier', NULL, '[]'::jsonb,
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


async def _approved_intent(
    db: AsyncSession,
    *,
    idempotency_key: str,
    tenant_id: str = TENANT_A,
    principal_id: str = PRINCIPAL_A,
    identity_id: str = IDENTITY_A,
    schedule_id: str | None = None,
) -> dict:
    intent = await create_external_intent(
        db,
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=identity_id,
        adapter_id=ADAPTER_ID,
        destination=APPROVED_URL,
        payload=APPROVED_PAYLOAD,
        payload_summary="Gate 4D-B public repository metadata read",
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


def _receipt(suffix: str = "ok") -> GitHubMetadataReceipt:
    payload_hash = hashlib.sha256(
        b'{"method":"GET","resource":"repository_metadata"}'
    ).hexdigest()
    return GitHubMetadataReceipt(
        status=200,
        payload_hash=payload_hash,
        response_hash=hashlib.sha256(f"github-{suffix}".encode()).hexdigest(),
        resolved_ips=("8.8.8.8",),
        provider_url=APPROVED_URL,
    )


def test_gate4d_migration_tier_is_separate() -> None:
    paths = [str(path).replace("\\", "/") for path in READONLY_GATE_MIGRATION_SEQUENCE]
    assert paths == ["portal/migrations/extend_external_action_github_readonly.sql"]
    assert ENVIRONMENT == "provider_readonly"
    assert RISK_CLASS == "E0"


@pytest.mark.asyncio
async def test_gate4d_e0_no_credentials_exact_approval_scheduler_and_kill_switch(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def fake_execute_once(**kwargs):
        nonlocal calls
        calls += 1
        assert "credential_header" not in kwargs
        return _receipt(str(calls))

    try:
        await _seed(maker)
        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", fake_execute_once)
        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4d-exact-0001")
            assert approved["risk_class"] == "E0"
            assert approved["environment"] == "provider_readonly"
            assert approved["credential_lease_id"] is None
            assert await db.scalar(select(func.count()).select_from(ExternalProviderCredentialLease)) == 0

            with pytest.raises(ProviderBoundaryError, match="repository metadata GET"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="payload-mutation",
                    execution_payload={"method": "POST", "resource": "repository_metadata"},
                )
            with pytest.raises(ExternalActionAuthorityError, match="destination"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="destination-mutation",
                    execution_destination="https://api.github.com/repos/ihoward40/other",
                )

            scheduled = await create_external_intent(
                db,
                tenant_id=TENANT_A,
                principal_id=PRINCIPAL_A,
                service_identity_id=IDENTITY_A,
                adapter_id=ADAPTER_ID,
                destination=APPROVED_URL,
                payload=APPROVED_PAYLOAD,
                payload_summary="Schedule provenance has no read authority",
                idempotency_key="gate4d-scheduled-0001",
                schedule_id="sch-gate4d-synthetic",
            )
            await preflight_external_intent(db, tenant_id=TENANT_A, intent_id=scheduled["intent_id"])
            with pytest.raises(ExternalActionAuthorityError, match="not executable"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=scheduled["intent_id"],
                    worker_id="scheduler-no-bypass",
                )

            killed = await _approved_intent(db, idempotency_key="gate4d-kill-0001")
            for scope_key, tenant_id, adapter_id in (
                ("GLOBAL", None, None),
                (f"TENANT:{TENANT_A}", TENANT_A, None),
                (f"ADAPTER:{ADAPTER_ID}", None, ADAPTER_ID),
            ):
                await set_external_kill_switch(
                    db,
                    scope_key=scope_key,
                    active=True,
                    updated_by=PRINCIPAL_A,
                    reason="Gate 4D-B kill switch certification",
                    tenant_id=tenant_id,
                    adapter_id=adapter_id,
                )
                with pytest.raises(ExternalActionAuthorityError, match="kill switch"):
                    await execute_external_intent(
                        db,
                        tenant_id=TENANT_A,
                        intent_id=killed["intent_id"],
                        worker_id="kill-worker",
                    )
                await set_external_kill_switch(
                    db,
                    scope_key=scope_key,
                    active=False,
                    updated_by=PRINCIPAL_A,
                    reason="Resume Gate 4D-B certification",
                    tenant_id=tenant_id,
                    adapter_id=adapter_id,
                )
            assert calls == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4d_durable_rate_limit_and_provider_rate_limit(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def fake_execute_once(**kwargs):
        nonlocal calls
        calls += 1
        return _receipt(str(calls))

    try:
        await _seed(maker)
        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", fake_execute_once)
        async with maker() as db:
            first = await _approved_intent(db, idempotency_key="gate4d-rate-first-0001")
            result = await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=first["intent_id"],
                worker_id="rate-first",
            )
            assert result["status"] == "SUCCEEDED"
            second = await _approved_intent(db, idempotency_key="gate4d-rate-second-0001")
            with pytest.raises(ExternalActionAuthorityError, match="rate limit exceeded"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=second["intent_id"],
                    worker_id="rate-second",
                )
            assert calls == 1
            bucket = await db.scalar(select(ExternalProviderRateBucket))
            assert bucket is not None
            assert bucket.limit_count == 1
            assert bucket.request_count == 1
            await db.commit()

        async with maker() as db:
            await db.execute(text("DELETE FROM external_provider_rate_buckets"))
            await db.commit()

        async def provider_limited(**kwargs):
            raise ProviderBoundaryError("Provider rate limit returned 403")

        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", provider_limited)
        async with maker() as db:
            intent = await _approved_intent(db, idempotency_key="gate4d-provider-rate-0001")
            with pytest.raises(ExternalActionAuthorityError, match="rate limit"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=intent["intent_id"],
                    worker_id="provider-rate-worker",
                )
            attempt = await db.scalar(
                select(ExternalProviderAttempt).where(ExternalProviderAttempt.intent_id == intent["intent_id"])
            )
            assert attempt is not None
            assert attempt.outcome == "RATE_LIMITED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4d_timeout_restart_reconciliation_and_no_blind_retry(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def timeout_once(**kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("synthetic GitHub timeout")

    try:
        await _seed(maker)
        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", timeout_once)
        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4d-timeout-0001")
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
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4d_concurrent_replay_evidence_cross_tenant_and_no_compensation(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def slow_success(**kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return _receipt("concurrent")

    try:
        await _seed(maker)
        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", slow_success)
        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4d-concurrent-0001")
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
            assert attempt.credential_lease_id is None
            assert attempt.request_hash
            assert attempt.response_hash
            assert attempt.provider_url == APPROVED_URL
            chain = await verify_external_evidence_chain(db, tenant_id=TENANT_A, intent_id=intent_id)
            assert chain["valid"] is True
            with pytest.raises(ExternalActionAuthorityError, match="no external effect to compensate"):
                await compensate_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=intent_id,
                    principal_id=PRINCIPAL_A,
                    reason="Read-only action has nothing to undo",
                )

        async with maker() as db:
            cross = await _approved_intent(
                db,
                idempotency_key="gate4d-cross-tenant-0001",
                tenant_id=TENANT_B,
                principal_id=PRINCIPAL_B,
                identity_id=IDENTITY_A,
            )
            with pytest.raises(ExternalActionAuthorityError, match="identity"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_B,
                    intent_id=cross["intent_id"],
                    worker_id="cross-tenant-worker",
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4d_service_identity_revocation_blocks_before_network(monkeypatch) -> None:
    maker, engine = await _sessionmaker()
    calls = 0

    async def should_not_run(**kwargs):
        nonlocal calls
        calls += 1
        return _receipt()

    try:
        await _seed(maker)
        monkeypatch.setattr(github_metadata_read_adapter, "execute_once", should_not_run)
        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4d-revoked-id-0001")
            await db.execute(
                text("UPDATE governed_service_identities SET status='REVOKED' WHERE id=:id"),
                {"id": IDENTITY_A},
            )
            with pytest.raises(ExternalActionAuthorityError, match="revoked"):
                await execute_external_intent(
                    db,
                    tenant_id=TENANT_A,
                    intent_id=approved["intent_id"],
                    worker_id="revoked-id-worker",
                )
            assert calls == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_gate4d_real_public_github_through_durable_authority() -> None:
    if os.environ.get("GATE4D_LIVE_HTTP") != "1":
        pytest.skip("Live Gate 4D-B call runs only in its dedicated workflow")
    maker, engine = await _sessionmaker()
    try:
        await _seed(maker)
        async with maker() as db:
            approved = await _approved_intent(db, idempotency_key="gate4d-live-authority-0001")
            result = await execute_external_intent(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
                worker_id="gate4d-live-worker",
                timeout_seconds=15.0,
            )
            assert result["status"] == "SUCCEEDED"
            assert result["risk_class"] == "E0"
            assert result["credential_lease_id"] is None
            assert result["provider"]["provider_status"] == 200
            assert result["provider"]["provider_url"] == APPROVED_URL
            assert result["provider"]["response_hash"]
            chain = await verify_external_evidence_chain(
                db,
                tenant_id=TENANT_A,
                intent_id=approved["intent_id"],
            )
            assert chain["valid"] is True
    finally:
        await engine.dispose()
