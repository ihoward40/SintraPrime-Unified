"""P5-P13 JARVIS B2 real-PostgreSQL runtime durability certification.

Opt-in: postgresql marker + JARVIS_B2_POSTGRES_URL. No real providers, no real
credentials (fake-only material), no external side effects.

Every restart test deliberately constructs a NEW engine, session factory, and
service instance set so the recovery source is provably the database, not an
identity map or process-local object (Principal restart-certification rule).
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.services.jarvis_action_receipt_b2 import (
    ActionReceipt,
    verify_receipt,
    verify_receipt_chain,
)
from portal.services.jarvis_authority_lease import AuthorityLease, LeaseDeniedError, LeaseState
from portal.services.jarvis_b2_runtime import create_b2_runtime, protected_state_backends
from portal.services.jarvis_capability_admission import admit_for_approval
from portal.services.jarvis_capability_contract import CapabilityContract
from portal.services.jarvis_capability_registry import CapabilityRegistryService
from portal.services.jarvis_credential_broker import CredentialDeniedError, CredentialRequest
from portal.services.jarvis_durable_credentials import DurableCredentialBroker
from portal.services.jarvis_durable_lease import DurableAuthorityLeaseStore
from portal.services.jarvis_durable_memory import DurableOperationalMemory
from portal.services.jarvis_durable_operations import DurableReconciler
from portal.services.jarvis_durable_receipts import DurableReceiptRepository
from portal.services.jarvis_operational_memory import MemoryClass, MemoryStatus
from portal.services.jarvis_verification_reconciliation import OperationState, VerificationStatus

pytestmark = pytest.mark.postgresql

CONTRACT_HASH = "b2-cert-contract-" + uuid.uuid4().hex[:16]
TENANT_A = "tenant-cert-a"
TENANT_B = "tenant-cert-b"

CREDENTIAL_STATE_COLUMNS = {
    "grant_id", "tenant_id", "lease_id", "action_id", "capability_contract_hash",
    "nonce_hash", "grant_status", "expires_at", "created_at", "consumed_at",
}
SECRET_LIKE_TOKENS = ("secret", "token", "api_key", "apikey", "bearer", "password", "private_key")


@pytest.fixture
def pg_url():
    value = os.getenv("JARVIS_B2_POSTGRES_URL")
    if not value:
        pytest.skip("JARVIS_B2_POSTGRES_URL is required; PostgreSQL runtime certification is not claimed")
    return value


@pytest.fixture
async def runtime(pg_url):
    """Fresh engine + session factory per test (process-restart equivalent)."""
    engine = create_async_engine(pg_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


def unique_lease(tenant_id=TENANT_A):
    return AuthorityLease.issue(
        tenant_id=tenant_id, principal_id="principal-cert", capability_id="cert.capability",
        capability_version="1.0.0", capability_contract_hash=CONTRACT_HASH, registry_revision=11,
        action_id="action-" + uuid.uuid4().hex[:8], approval_id="approval-" + uuid.uuid4().hex[:8],
        operation="cert.operation", target="cert-target:primary", params_hash="params-" + uuid.uuid4().hex[:8],
        ttl=timedelta(minutes=10), now=datetime.now(UTC),
    )


def lease_context(lease):
    return {
        "tenant_id": lease.tenant_id, "principal_id": lease.principal_id,
        "capability_id": lease.capability_id, "capability_version": lease.capability_version,
        "capability_contract_hash": lease.capability_contract_hash,
        "registry_revision": lease.registry_revision, "action_id": lease.action_id,
        "approval_id": lease.approval_id, "operation": lease.operation,
        "target": lease.target, "params_hash": lease.params_hash,
        "now": datetime.now(UTC),
    }


def credential_request(lease, nonce):
    now = datetime.now(UTC)
    return CredentialRequest(
        broker_request_id="request-" + uuid.uuid4().hex[:8], tenant_id=lease.tenant_id,
        principal_id=lease.principal_id, capability_id=lease.capability_id,
        capability_version=lease.capability_version,
        capability_contract_hash=lease.capability_contract_hash, action_id=lease.action_id,
        approval_id=lease.approval_id, lease_id=lease.lease_id, lease_revision=lease.revision,
        provider_id="fake-provider", resource_scope="cert-resource", operation=lease.operation,
        target=lease.target, issued_at=now, expires_at=now + timedelta(minutes=5), nonce=nonce,
    )


async def persist_claimed_lease(factory, lease):
    async with factory() as session:
        store = DurableAuthorityLeaseStore(session)
        await store.persist(lease)
        claimed = await store.claim(lease, **lease_context(lease))
        await session.commit()
    return claimed


async def persist_and_claim_lease(factory, lease):
    async with factory() as session:
        store = DurableAuthorityLeaseStore(session)
        await store.persist(lease)
        claimed = await store.claim(lease, **lease_context(lease))
        await session.commit()
    return claimed


async def persist_and_consume_lease(factory, claimed):
    async with factory() as session:
        consumed = await DurableAuthorityLeaseStore(session).consume(claimed, **lease_context(claimed))
        await session.commit()
    return consumed


def receipt_fields(operation_id, lease, grant_id, *, verification_status="VERIFIED_SUCCESS"):
    moment = datetime.now(UTC).isoformat()
    return {
        "tenant_id": lease.tenant_id, "mission_id": "mission-cert", "action_id": lease.action_id,
        "operation_id": operation_id, "attempt_id": "attempt-" + uuid.uuid4().hex[:8],
        "principal_id": lease.principal_id, "approval_id": lease.approval_id,
        "capability_id": lease.capability_id, "capability_version": lease.capability_version,
        "capability_contract_hash": lease.capability_contract_hash,
        "approved_contract_hash": lease.capability_contract_hash,
        "runtime_contract_hash": lease.capability_contract_hash,
        "operation_contract_hash": lease.capability_contract_hash,
        "registry_revision": lease.registry_revision, "lease_id": lease.lease_id,
        "lease_revision": lease.revision, "credential_grant_id": grant_id,
        "executor_id": "cert-executor", "executor_version": "1.0.0",
        "executor_artifact_hash": "executor-hash", "adapter_id": "cert-adapter",
        "adapter_version": "1.0.0", "adapter_artifact_hash": "adapter-hash",
        "operation": lease.operation, "target": lease.target, "params_hash": lease.params_hash,
        "pre_state_hash": "pre-state", "provider_result_hash": "provider-result",
        "post_state_hash": "post-state", "verification_status": verification_status,
        "verification_reason": "POST_STATE_CONFIRMED", "execution_started_at": moment,
        "execution_completed_at": moment, "verified_at": moment,
    }


# ═══════════════════════════════════════════════════════════════════════════
# P5 — Durable lease race (two genuinely separate sessions)
# ═══════════════════════════════════════════════════════════════════════════


async def test_p5_lease_double_claim_and_double_consume_denied(runtime):
    factory = runtime
    original = unique_lease()
    async with factory() as setup:
        await DurableAuthorityLeaseStore(setup).persist(original)
        await setup.commit()

    async def attempt_claim():
        async with factory() as session:
            try:
                await DurableAuthorityLeaseStore(session).claim(original, **lease_context(original))
                await session.commit()
                return "CLAIMED"
            except LeaseDeniedError as exc:
                await session.rollback()
                return str(exc)

    claim_outcomes = await asyncio.gather(attempt_claim(), attempt_claim())
    successful_claims = claim_outcomes.count("CLAIMED")
    claim_conflicts = len(claim_outcomes) - successful_claims
    assert successful_claims == 1, claim_outcomes
    assert claim_conflicts == 1, claim_outcomes

    winner = None
    async with factory() as session:
        winner = await DurableAuthorityLeaseStore(session).load(original.lease_id, tenant_id=original.tenant_id)
    assert winner is not None
    assert winner.lease_state is LeaseState.CLAIMED
    assert winner.revision == original.revision + 1

    async def attempt_consume():
        async with factory() as session:
            try:
                await DurableAuthorityLeaseStore(session).consume(winner, **lease_context(winner))
                await session.commit()
                return "CONSUMED"
            except LeaseDeniedError as exc:
                await session.rollback()
                return str(exc)

    consume_outcomes = await asyncio.gather(attempt_consume(), attempt_consume())
    successful_consumes = consume_outcomes.count("CONSUMED")
    consume_conflicts = len(consume_outcomes) - successful_consumes
    assert successful_consumes == 1, consume_outcomes
    assert consume_conflicts == 1, consume_outcomes

    async with factory() as session:
        final = await DurableAuthorityLeaseStore(session).load(original.lease_id, tenant_id=original.tenant_id)
    assert final.lease_state is LeaseState.CONSUMED
    assert final.revision == original.revision + 2


# ═══════════════════════════════════════════════════════════════════════════
# P6 — Lease restart recovery
# ═══════════════════════════════════════════════════════════════════════════


async def test_p6_lease_restart_recovery_from_postgres(runtime):
    factory = runtime
    original = unique_lease()
    async with factory() as session_a:
        store_a = DurableAuthorityLeaseStore(session_a)
        await store_a.persist(original)
        await store_a.claim(original, **lease_context(original))
        await session_a.commit()
    # session A and store A are discarded here

    async with factory() as session_b:
        recovered = await DurableAuthorityLeaseStore(session_b).load(original.lease_id, tenant_id=original.tenant_id)
        await session_b.commit()
    assert recovered is not None
    assert recovered.lease_state is LeaseState.CLAIMED
    assert recovered.revision == original.revision + 1

    with pytest.raises(LeaseDeniedError):
        async with factory() as session_c:
            await DurableAuthorityLeaseStore(session_c).claim(recovered, **lease_context(recovered))


# ═══════════════════════════════════════════════════════════════════════════
# P7 — Credential replay persistence across restart
# ═══════════════════════════════════════════════════════════════════════════


async def _consume_with_fresh_broker(factory, grant, request):
    async with factory() as session:
        await DurableCredentialBroker(session).consume_durable(grant=grant, request=request)
        await session.commit()


async def _reissue_with_fresh_broker(factory, request, claimed):
    async with factory() as session:
        await DurableCredentialBroker(session).issue_scoped_grant_durable(request=request, lease=claimed)
        await session.commit()


async def test_p7_credential_replay_denied_after_restart(runtime):
    factory = runtime
    issued = unique_lease()
    claimed = await persist_and_claim_lease(factory, issued)
    nonce = "nonce-" + uuid.uuid4().hex
    request = credential_request(claimed, nonce)

    async with factory() as session_a:
        broker_a = DurableCredentialBroker(session_a)
        grant = await broker_a.issue_scoped_grant_durable(request=request, lease=claimed)
        await broker_a.consume_durable(grant=grant, request=request)
        await session_a.commit()
        grant_id = grant.grant_id
    # broker A and session A discarded

    with pytest.raises(CredentialDeniedError) as denied:
        await _consume_with_fresh_broker(factory, grant, request)
    assert denied.value.reason_code == "NONCE_REPLAY"

    with pytest.raises(CredentialDeniedError) as reissued:
        await _reissue_with_fresh_broker(factory, request, claimed)
    assert reissued.value.reason_code == "NONCE_REPLAY"

    # durable row inspection: identifiers/hashes/status only, no secret material
    async with factory() as session_d:
        row = (await session_d.execute(
            text("SELECT * FROM jarvis_credential_state WHERE grant_id = :gid"),
            {"gid": grant_id},
        )).mappings().one()
    assert set(row.keys()) == CREDENTIAL_STATE_COLUMNS
    assert not any(token in " ".join(row.keys()).lower() for token in SECRET_LIKE_TOKENS)
    assert row["nonce_hash"] == hashlib.sha256(nonce.encode()).hexdigest()
    assert row["grant_status"] == "CONSUMED"
    assert not any("FAKE_" in str(value) for value in row.values())


# ═══════════════════════════════════════════════════════════════════════════
# P8 — Operation restart / unknown-state recovery (central High-severity test)
# ═══════════════════════════════════════════════════════════════════════════


def _external_mutation_tracker():
    return {"mutation_count": 0, "present": False}


async def test_p8a_unknown_restart_recovery_has_zero_second_mutation(runtime):
    factory = runtime
    state = _external_mutation_tracker()

    def mutate():
        state["mutation_count"] += 1
        state["present"] = True
        return True

    lease = unique_lease()
    async with factory() as session_a:
        record = await DurableReconciler(session_a).create_or_get(
            action_id=lease.action_id, attempt_id="attempt-p8a", tenant_id=lease.tenant_id,
            capability_contract_hash=lease.capability_contract_hash, lease_id=lease.lease_id,
            credential_grant_id="grant-p8a", operation=lease.operation, target=lease.target,
            params_hash=lease.params_hash,
        )
        await session_a.commit()
        operation_id = record.operation_id

    async with factory() as session_b:
        outcome, status = await DurableReconciler(session_b).attempt_once(
            record, tenant_id=lease.tenant_id, mutate=mutate, read_state=lambda: None,
        )
        await session_b.commit()
    assert outcome == "UNKNOWN_RECORDED"
    assert status is VerificationStatus.SIDE_EFFECT_UNKNOWN
    assert state["mutation_count"] == 1

    async with factory() as session_c:
        fresh = DurableReconciler(session_c)
        recovered = await fresh.recover(operation_id, tenant_id=lease.tenant_id)
        assert recovered is not None
        assert recovered.state is OperationState.UNKNOWN
        outcome2, _status2 = await fresh.attempt_once(
            recovered, tenant_id=lease.tenant_id, mutate=mutate, read_state=lambda: True,
        )
        await session_c.commit()
    assert outcome2 == "DUPLICATE_SUPPRESSED"
    assert state["mutation_count"] == 1, "second external mutation after restart"

    async with factory() as session_d:
        reconciled = await DurableReconciler(session_d).reconcile_unknown_from_recovery(
            operation_id, tenant_id=lease.tenant_id,
            post_state_matches=state["present"], verification_status=VerificationStatus.VERIFIED_SUCCESS,
        )
        await session_d.commit()
    assert reconciled.state is OperationState.RECONCILED
    assert reconciled.latest_verification_status is VerificationStatus.VERIFIED_SUCCESS
    assert state["mutation_count"] == 1
    assert state["mutation_count"] == 1  # FINAL_MUTATION_COUNT == 1


async def test_p8b_crash_before_mutation_reconciles_without_mutation(runtime):
    factory = runtime
    state = _external_mutation_tracker()

    def mutate():
        state["mutation_count"] += 1
        state["present"] = True
        return True

    lease = unique_lease()
    async with factory() as session_a:
        record = await DurableReconciler(session_a).create_or_get(
            action_id=lease.action_id, attempt_id="attempt-p8b", tenant_id=lease.tenant_id,
            capability_contract_hash=lease.capability_contract_hash, lease_id=lease.lease_id,
            credential_grant_id="grant-p8b", operation=lease.operation, target=lease.target,
            params_hash=lease.params_hash,
        )
        await DurableReconciler(session_a).mark_attempting(record.operation_id, tenant_id=lease.tenant_id)
        await session_a.commit()
        operation_id = record.operation_id
    # crash before mutate() ever runs

    async with factory() as session_b:
        fresh = DurableReconciler(session_b)
        recovered = await fresh.recover(operation_id, tenant_id=lease.tenant_id)
        assert recovered.state is OperationState.ATTEMPTING
        outcome, _status = await fresh.attempt_once(
            recovered, tenant_id=lease.tenant_id, mutate=mutate, read_state=lambda: True,
        )
        await session_b.commit()
    assert outcome == "DUPLICATE_SUPPRESSED"
    assert state["mutation_count"] == 0, "recovery must not re-mutate an ATTEMPTING operation"

    async with factory() as session_c:
        reconciled = await DurableReconciler(session_c).reconcile_unknown_from_recovery(
            operation_id, tenant_id=lease.tenant_id,
            post_state_matches=state["present"], verification_status=VerificationStatus.VERIFIED_FAILURE,
        )
        await session_c.commit()
    assert reconciled.state is OperationState.RECONCILED
    assert reconciled.latest_verification_status is VerificationStatus.VERIFIED_FAILURE
    assert state["mutation_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# P9 — Receipt durability
# ═══════════════════════════════════════════════════════════════════════════


async def _persist_with_fresh_repo(factory, receipt):
    async with factory() as session:
        await DurableReceiptRepository(session).persist(receipt)
        await session.commit()


async def test_p9_receipt_reload_hash_chain_and_immutability(runtime):
    factory = runtime
    lease = unique_lease()
    fields = receipt_fields("op-" + uuid.uuid4().hex[:8], lease, "grant-p9")
    receipt_one = ActionReceipt.create(**fields)

    async with factory() as session_a:
        await DurableReceiptRepository(session_a).persist(receipt_one)
        await session_a.commit()
    # repository and session discarded

    async with factory() as session_b:
        reloaded = await DurableReceiptRepository(session_b).load(receipt_one.receipt_id, tenant_id=lease.tenant_id)
    assert reloaded is not None
    assert reloaded.receipt_id == receipt_one.receipt_id
    assert reloaded.receipt_hash == receipt_one.receipt_hash
    assert verify_receipt(reloaded)
    assert reloaded.previous_receipt_hash is None

    with pytest.raises(ValueError, match="RECEIPT_IMMUTABLE"):
        await _persist_with_fresh_repo(factory, receipt_one)

    tampered = replace(reloaded, post_state_hash="tampered")
    assert not verify_receipt(tampered)
    with pytest.raises(ValueError, match="RECEIPT_HASH_INVALID"):
        await _persist_with_fresh_repo(factory, tampered)

    receipt_two = ActionReceipt.create(previous_receipt_hash=receipt_one.receipt_hash, **fields)
    async with factory() as session_e:
        await DurableReceiptRepository(session_e).persist(receipt_two)
        await session_e.commit()
    assert verify_receipt_chain([receipt_one, receipt_two], tenant_id=lease.tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# P10 — Operational memory durability
# ═══════════════════════════════════════════════════════════════════════════


async def test_p10_memory_attention_dedup_ack_resolve_survive_restart(runtime):
    factory = runtime
    values = {
        "tenant_id": TENANT_A, "mission_id": "mission-cert", "action_id": "action-cert",
        "operation_id": "op-" + uuid.uuid4().hex[:8], "receipt_id": None, "receipt_hash": None,
        "capability_id": "cert.capability", "capability_version": "1.0.0",
        "capability_contract_hash": CONTRACT_HASH, "event_class": MemoryClass.ATTENTION_REQUIRED,
        "reason_code": "CERT_REASON", "summary": "attention item",
        "dedup_key": "dedup-" + uuid.uuid4().hex,
    }
    async with factory() as session_a:
        event = await DurableOperationalMemory(session_a).record_operational_event(**values)
        await session_a.commit()

    async with factory() as session_b:
        memory_b = DurableOperationalMemory(session_b)
        events = await memory_b.get_for_tenant(tenant_id=TENANT_A)
        assert any(item.memory_event_id == event.memory_event_id for item in events)
        duplicate = await memory_b.record_operational_event(**values)
        await session_b.commit()
    assert duplicate.memory_event_id == event.memory_event_id

    async with factory() as session_c:
        acknowledged = await DurableOperationalMemory(session_c).acknowledge_attention(
            tenant_id=TENANT_A, memory_event_id=event.memory_event_id,
        )
        await session_c.commit()
    assert acknowledged.status is MemoryStatus.ACKNOWLEDGED
    assert acknowledged.acknowledged_at

    async with factory() as session_d:
        events_d = await DurableOperationalMemory(session_d).get_for_tenant(tenant_id=TENANT_A)
        persisted = next(item for item in events_d if item.memory_event_id == event.memory_event_id)
        assert persisted.status is MemoryStatus.ACKNOWLEDGED
        await DurableOperationalMemory(session_d).resolve_attention(
            tenant_id=TENANT_A, memory_event_id=event.memory_event_id,
        )
        await session_d.commit()

    async with factory() as session_e:
        events_e = await DurableOperationalMemory(session_e).get_for_tenant(tenant_id=TENANT_A)
        final = next(item for item in events_e if item.memory_event_id == event.memory_event_id)
    assert final.status is MemoryStatus.RESOLVED
    assert final.resolved_at
    assert final.acknowledged_at


# ═══════════════════════════════════════════════════════════════════════════
# P11 — Fail-closed database loss (permanent regression)
# ═══════════════════════════════════════════════════════════════════════════


def test_p11_runtime_without_database_fails_closed():
    with pytest.raises(RuntimeError, match="B2_DURABILITY_DATABASE_REQUIRED"):
        create_b2_runtime(None)
    backends = protected_state_backends()
    assert set(backends.values()) == {"DURABLE"}
    assert not any("in_memory" in name or "process_local" in name for name in backends)


# ═══════════════════════════════════════════════════════════════════════════
# P12 — End-to-end durable chain
# ═══════════════════════════════════════════════════════════════════════════


def _e2e_contract():
    return CapabilityContract(
        capability_id="cert.e2e.capability", capability_version="1.0.0",
        allowed_operations=("cert.operation",), allowed_targets=("cert-target:primary",),
        risk="low", consequence="reversible", authority="tenant_principal",
        credential="fake_credential", executor_id="cert-executor", adapter_id="cert-adapter",
        verification="independent_refetch", idempotency="label_already_present",
        reconciliation="refetch_on_timeout", rollback="remove_label",
        lease="single_request", revocation="approval_consumed",
        receipt="hash_chain_append", memory="bounded_writeback", brief="e2e durable chain",
    )


async def _seed_tenant_principal(session, tenant_id, actor_id):
    """P12 needs real FK-satisfying rows (PG enforces; SQLite lanes cannot)."""
    import sqlalchemy as sa

    await session.execute(sa.text(
        "INSERT INTO tenants (id, name, slug) VALUES (:id, :name, :slug) ON CONFLICT DO NOTHING"
    ), {"id": str(tenant_id), "name": "B2 Cert Tenant", "slug": "b2-cert-" + str(tenant_id)[:8]})
    role_id = await session.scalar(sa.text(
        "SELECT id FROM roles WHERE name = 'FIRM_ADMIN' LIMIT 1"
    ))
    await session.execute(sa.text(
        "INSERT INTO users (id, tenant_id, role_id, email, first_name, last_name, hashed_password) "
        "VALUES (:id, :tenant_id, :role_id, :email, :first_name, :last_name, :hashed_password) "
        "ON CONFLICT DO NOTHING"
    ), {
        "id": str(actor_id), "tenant_id": str(tenant_id), "role_id": str(role_id),
        "email": f"b2-cert-{str(tenant_id)[:8]}.example.invalid", "first_name": "B2", "last_name": "Cert",
        "hashed_password": "cert-not-a-real-password",
    })
    await session.commit()


async def test_p12_end_to_end_durable_chain_recovered_from_postgres(runtime):
    factory = runtime
    contract = _e2e_contract()
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    registry = CapabilityRegistryService()

    # The B2-B2 registry tables are ORM-managed in this repository (no SQL
    # migration owns them); create them via the repo's own init_db mechanism.
    # checkfirst=True is additive: the migrated B2/portal tables are skipped.
    from portal.database import Base

    async with create_async_engine(  # separate engine scoped to this proof
        os.environ["JARVIS_B2_POSTGRES_URL"]
    ).begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        await _seed_tenant_principal(session, tenant_id, actor_id)
        await registry.register_capability(
            session=session, tenant_id=tenant_id, contract=contract,
            owner_principal=actor_id, actor_id=actor_id,
        )
        await session.commit()
        await registry.transition_to_reviewed(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version, contract_hash=contract.contract_hash,
            actor_id=actor_id,
        )
        await session.commit()
        await registry.transition_to_approved(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version, contract_hash=contract.contract_hash,
            actor_id=actor_id,
            approval_policy_ref="approval_policy_v1",
            credential_policy_ref="credential_policy_v1",
            verification_policy_ref="verification_policy_v1",
        )
        await session.commit()
        await registry.transition_to_sandboxed(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version, contract_hash=contract.contract_hash,
            actor_id=actor_id,
        )
        await session.commit()
        await registry.transition_to_trusted(
            session=session, tenant_id=tenant_id, capability_id=contract.capability_id,
            capability_version=contract.capability_version, contract_hash=contract.contract_hash,
            actor_id=actor_id, certifier_id=actor_id,
        )
        await session.commit()
        admission = await admit_for_approval(session=session, tenant_id=tenant_id, contract=contract)
        await session.commit()
    # INT-ADMISSION-COMPOSITION-001 (observed, not repaired — frozen code):
    # admit_for_approval requires lifecycle_state == REVIEWED while
    # effective_executable is only True at TRUSTED, so no public registry path
    # yields ADMISSION_ELIGIBLE. The gate is structurally fail-closed; the
    # certification records the denial as evidence and does NOT bypass it.
    assert admission.approved is False
    assert admission.reason_code in {"LIFECYCLE_NOT_REVIEWED", "REGISTRY_NOT_EXECUTION_ELIGIBLE"}
    assert admission.contract_hash == contract.contract_hash
    assert admission.provider_calls == 0

    async with factory() as session:
        registration = await registry.get_current_registration(
            session, tenant_id, contract.capability_id, contract.capability_version,
        )
        await session.commit()
    assert registration is not None
    assert registration.lifecycle_state == "TRUSTED"
    assert registration.effective_executable is True
    registry_revision = registration.registry_revision

    lease = AuthorityLease.issue(
        tenant_id=str(tenant_id), principal_id=str(actor_id), capability_id=contract.capability_id,
        capability_version=contract.capability_version, capability_contract_hash=contract.contract_hash,
        registry_revision=registry_revision, action_id="action-e2e", approval_id="approval-e2e",
        operation="cert.operation", target="cert-target:primary", params_hash="params-e2e",
        ttl=timedelta(minutes=10), now=datetime.now(UTC),
    )
    claimed = await persist_and_claim_lease(factory, lease)

    request = credential_request(claimed, "nonce-e2e-" + uuid.uuid4().hex)
    async with factory() as session:
        broker = DurableCredentialBroker(session)
        grant = await broker.issue_scoped_grant_durable(request=request, lease=claimed)
        await broker.consume_durable(grant=grant, request=request)
        await session.commit()
        grant_id = grant.grant_id

    state = _external_mutation_tracker()

    def mutate():
        state["mutation_count"] += 1
        state["present"] = True
        return True

    async with factory() as session:
        reconciler = DurableReconciler(session)
        record = await reconciler.create_or_get(
            action_id=lease.action_id, attempt_id="attempt-e2e", tenant_id=lease.tenant_id,
            capability_contract_hash=contract.contract_hash, lease_id=lease.lease_id,
            credential_grant_id=grant_id, operation=lease.operation, target=lease.target,
            params_hash=lease.params_hash,
        )
        outcome, status = await reconciler.attempt_once(
            record, tenant_id=lease.tenant_id, mutate=mutate, read_state=lambda: True,
        )
        await session.commit()
        operation_id = record.operation_id
    assert outcome == "COMPLETED"
    assert status is VerificationStatus.VERIFIED_SUCCESS

    await persist_and_consume_lease(factory, claimed)

    receipt = ActionReceipt.create(
        **receipt_fields(operation_id, lease, grant_id, verification_status="VERIFIED_SUCCESS")
    )
    async with factory() as session:
        await DurableReceiptRepository(session).persist(receipt)
        await session.commit()

    async with factory() as session:
        event = await DurableOperationalMemory(session).record_operational_event(
            tenant_id=lease.tenant_id, mission_id="mission-e2e", action_id=lease.action_id,
            operation_id=operation_id, receipt_id=receipt.receipt_id, receipt_hash=receipt.receipt_hash,
            capability_id=contract.capability_id, capability_version=contract.capability_version,
            capability_contract_hash=contract.contract_hash,
            event_class=MemoryClass.GOVERNED_ACTION_COMPLETED, reason_code="E2E_COMPLETED",
            summary="governed action completed", dedup_key="dedup-e2e-" + uuid.uuid4().hex,
        )
        await session.commit()

    # ── destroy everything; reconstruct exclusively from PostgreSQL ──
    async with factory() as session:
        lease_b = await DurableAuthorityLeaseStore(session).load(lease.lease_id, tenant_id=lease.tenant_id)
        operation_b = await DurableReconciler(session).recover(operation_id, tenant_id=lease.tenant_id)
        receipt_b = await DurableReceiptRepository(session).load(receipt.receipt_id, tenant_id=lease.tenant_id)
        events_b = await DurableOperationalMemory(session).get_for_tenant(tenant_id=lease.tenant_id)
        await session.commit()

    assert lease_b.lease_state is LeaseState.CONSUMED
    assert operation_b.state is OperationState.VERIFIED
    assert operation_b.latest_verification_status is VerificationStatus.VERIFIED_SUCCESS
    assert verify_receipt(receipt_b)
    assert receipt_b.receipt_hash == receipt.receipt_hash
    memory_b = next(item for item in events_b if item.memory_event_id == event.memory_event_id)

    assert contract.contract_hash == lease_b.capability_contract_hash
    assert contract.contract_hash == operation_b.capability_contract_hash
    assert contract.contract_hash == receipt_b.capability_contract_hash
    assert contract.contract_hash == receipt_b.approved_contract_hash
    assert contract.contract_hash == receipt_b.runtime_contract_hash
    assert contract.contract_hash == receipt_b.operation_contract_hash
    assert contract.contract_hash == memory_b.capability_contract_hash
    assert state["mutation_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# P13 — Cross-tenant durable state
# ═══════════════════════════════════════════════════════════════════════════


async def test_p13_cross_tenant_durable_state_fully_denied(runtime):
    factory = runtime
    issued_a = unique_lease(TENANT_A)
    lease_a = await persist_and_claim_lease(factory, issued_a)

    nonce = "nonce-p13-" + uuid.uuid4().hex
    request_a = credential_request(lease_a, nonce)
    async with factory() as session:
        broker_a = DurableCredentialBroker(session)
        grant_a = await broker_a.issue_scoped_grant_durable(request=request_a, lease=lease_a)
        await session.commit()
        grant_id_a = grant_a.grant_id

    async with factory() as session:
        operation_a = await DurableReconciler(session).create_or_get(
            action_id=lease_a.action_id, attempt_id="attempt-p13", tenant_id=TENANT_A,
            capability_contract_hash=lease_a.capability_contract_hash, lease_id=lease_a.lease_id,
            credential_grant_id=grant_id_a, operation=lease_a.operation, target=lease_a.target,
            params_hash=lease_a.params_hash,
        )
        await session.commit()
        operation_id_a = operation_a.operation_id

    fields = receipt_fields(operation_id_a, lease_a, grant_id_a)
    receipt_a = ActionReceipt.create(**fields)
    async with factory() as session:
        await DurableReceiptRepository(session).persist(receipt_a)
        await session.commit()

    memory_values = {
        "tenant_id": TENANT_A, "mission_id": "mission-p13", "action_id": "action-p13",
        "operation_id": operation_id_a, "receipt_id": receipt_a.receipt_id,
        "receipt_hash": receipt_a.receipt_hash, "capability_id": "cert.capability",
        "capability_version": "1.0.0", "capability_contract_hash": CONTRACT_HASH,
        "event_class": MemoryClass.ATTENTION_REQUIRED, "reason_code": "P13_REASON",
        "summary": "tenant-a attention", "dedup_key": "dedup-p13-shared",
    }
    async with factory() as session:
        event_a = await DurableOperationalMemory(session).record_operational_event(**memory_values)
        await session.commit()
    bypasses = 0

    # 1. lease load as tenant B
    async with factory() as session:
        if await DurableAuthorityLeaseStore(session).load(lease_a.lease_id, tenant_id=TENANT_B) is not None:
            bypasses += 1

    # 2. lease claim as tenant B
    try:
        async with factory() as session:
            await DurableAuthorityLeaseStore(session).claim(lease_a, **{
                **lease_context(lease_a), "tenant_id": TENANT_B,
            })
            await session.commit()
        bypasses += 1
    except LeaseDeniedError:
        pass

    # 3. credential consume as tenant B
    try:
        async with factory() as session:
            row = (await session.execute(
                text("SELECT grant_id FROM jarvis_credential_state WHERE grant_id = :gid"),
                {"gid": grant_id_a},
            )).scalar_one()
            assert row
            tampered_request = credential_request(lease_a, nonce)
            tampered = replace(tampered_request, tenant_id=TENANT_B)
            await DurableCredentialBroker(session).consume_durable(
                grant=type("GrantProxy", (), {"grant_id": grant_id_a})(), request=tampered,
            )
            await session.commit()
        bypasses += 1
    except CredentialDeniedError:
        pass

    # 4. operation recovery as tenant B
    async with factory() as session:
        if await DurableReconciler(session).recover(operation_id_a, tenant_id=TENANT_B) is not None:
            bypasses += 1

    # 5. operation mutation as tenant B (no external mutation possible)
    state = _external_mutation_tracker()

    def mutate():
        state["mutation_count"] += 1
        return True

    try:
        async with factory() as session:
            await DurableReconciler(session).attempt_once(
                operation_a, tenant_id=TENANT_B, mutate=mutate, read_state=lambda: True,
            )
            await session.commit()
        bypasses += 1
    except LookupError:
        pass

    # 6. receipt load as tenant B
    async with factory() as session:
        if await DurableReceiptRepository(session).load(receipt_a.receipt_id, tenant_id=TENANT_B) is not None:
            bypasses += 1

    # 7. memory acknowledgement as tenant B
    try:
        async with factory() as session:
            await DurableOperationalMemory(session).acknowledge_attention(
                tenant_id=TENANT_B, memory_event_id=event_a.memory_event_id,
            )
            await session.commit()
        bypasses += 1
    except PermissionError:
        pass

    # 8. tenant B memory view excludes tenant A events; same dedup key is separate
    async with factory() as session:
        events_b = await DurableOperationalMemory(session).get_for_tenant(tenant_id=TENANT_B)
        assert all(item.memory_event_id != event_a.memory_event_id for item in events_b)
        tenant_b_event = await DurableOperationalMemory(session).record_operational_event(**{**memory_values, "tenant_id": TENANT_B})
        await session.commit()
    assert tenant_b_event.memory_event_id != event_a.memory_event_id

    assert bypasses == 0
    assert state["mutation_count"] == 0
