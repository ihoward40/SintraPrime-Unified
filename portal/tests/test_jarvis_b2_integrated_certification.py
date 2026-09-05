"""Lane A B2 integrated certification smoke matrix.

This suite composes the frozen local primitives without real providers,
credentials, database writes, or external effects.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from portal.services.jarvis_action_receipt_b2 import (
    ActionReceipt,
    ReceiptCreationDeniedError,
    verify_receipt_chain,
)
from portal.services.jarvis_authority_lease import AuthorityLease, LeaseDeniedError
from portal.services.jarvis_capability_admission import AdmissionResult
from portal.services.jarvis_credential_broker import (
    CredentialBroker,
    CredentialDeniedError,
    CredentialRequest,
)
from portal.services.jarvis_legacy_containment import (
    LEGACY_CONTAINMENT_MAP,
    LegacyDisposition,
    deny_legacy_mutation,
)
from portal.services.jarvis_operational_memory import MemoryClass, OperationalMemory
from portal.services.jarvis_runtime_attestation import (
    RuntimeAttestationEvidence,
    artifact_hash,
    attest_runtime,
)
from portal.services.jarvis_verification_reconciliation import (
    InMemoryReconciler,
    VerificationStatus,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTRACT = "contract-hash"


def make_lease():
    lease = AuthorityLease.issue(
        tenant_id="tenant-a", principal_id="principal-a", capability_id="cap",
        capability_version="1", capability_contract_hash=CONTRACT, registry_revision=3,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", ttl=timedelta(minutes=5), now=NOW,
    )
    return lease.claim(
        tenant_id="tenant-a", principal_id="principal-a", capability_id="cap",
        capability_version="1", capability_contract_hash=CONTRACT, registry_revision=3,
        action_id="action", approval_id="approval", operation="op", target="target",
        params_hash="params", now=NOW + timedelta(minutes=1),
    )


def make_request(lease):
    return CredentialRequest(
        broker_request_id="request", tenant_id=lease.tenant_id, principal_id=lease.principal_id,
        capability_id=lease.capability_id, capability_version=lease.capability_version,
        capability_contract_hash=lease.capability_contract_hash, action_id=lease.action_id,
        approval_id=lease.approval_id, lease_id=lease.lease_id, lease_revision=lease.revision,
        provider_id="fake", resource_scope="resource", operation=lease.operation,
        target=lease.target, issued_at=NOW + timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=4), nonce="nonce",
    )


def test_contract_identity_and_authority_chain():
    lease = make_lease()
    request = make_request(lease)
    broker = CredentialBroker()
    grant = broker.issue_scoped_grant(request=request, lease=lease, now=NOW + timedelta(minutes=2))
    assert grant.capability_contract_hash == lease.capability_contract_hash == CONTRACT
    evidence = RuntimeAttestationEvidence(
        "cap", "1", CONTRACT, 3, "executor", "1", artifact_hash("executor"),
        "adapter", "1", artifact_hash("adapter"), artifact_hash("config"), ("policy.v1",), NOW.isoformat(),
    )
    decision = attest_runtime(
        approved_contract_hash=CONTRACT, runtime_contract_hash=CONTRACT, evidence=evidence,
        approved_executor_id="executor", approved_executor_version="1",
        approved_executor_artifact_hash=artifact_hash("executor"), approved_adapter_id="adapter",
        approved_adapter_version="1", approved_adapter_artifact_hash=artifact_hash("adapter"),
        approved_registry_revision=3,
    )
    assert decision.allowed
    assert grant.lease_id == lease.lease_id


def test_contract_identity_mutation_denied():
    lease = make_lease()
    with pytest.raises(CredentialDeniedError):
        CredentialBroker().issue_scoped_grant(request=make_request(lease), lease=lease, now=NOW + timedelta(minutes=2), attestation_valid=False)


def test_cross_tenant_denials_across_lease_credential_and_memory():
    lease = make_lease()
    with pytest.raises(LeaseDeniedError):
        lease.validate(tenant_id="tenant-b", principal_id="principal-a", capability_id="cap", capability_version="1", capability_contract_hash=CONTRACT, registry_revision=3, action_id="action", approval_id="approval", operation="op", target="target", params_hash="params", now=NOW + timedelta(minutes=1))
    memory = OperationalMemory()
    event = memory.record_operational_event(tenant_id="tenant-a", mission_id="m", action_id="a", operation_id="o", receipt_id=None, receipt_hash=None, capability_id="cap", capability_version="1", capability_contract_hash=CONTRACT, event_class=MemoryClass.ATTENTION_REQUIRED, reason_code="DENIED", summary="denied", dedup_key="a")
    with pytest.raises(PermissionError):
        memory.acknowledge_attention(tenant_id="tenant-b", memory_event_id=event.memory_event_id)


def test_revoked_dependency_states_deny_lease_and_credential():
    lease = make_lease()
    request = make_request(lease)
    for state in ("REVOKED", "QUARANTINED_BY_DEPENDENCY", "REVALIDATION_REQUIRED"):
        with pytest.raises(CredentialDeniedError):
            CredentialBroker().issue_scoped_grant(request=request, lease=lease, now=NOW + timedelta(minutes=2), effective_state=state)


def test_executor_and_adapter_substitution_denied():
    evidence = RuntimeAttestationEvidence("cap", "1", CONTRACT, 3, "wrong", "1", artifact_hash("executor"), "adapter", "1", artifact_hash("adapter"), "config", (), NOW.isoformat())
    result = attest_runtime(approved_contract_hash=CONTRACT, runtime_contract_hash=CONTRACT, evidence=evidence, approved_executor_id="executor", approved_executor_version="1", approved_executor_artifact_hash=artifact_hash("executor"), approved_adapter_id="adapter", approved_adapter_version="1", approved_adapter_artifact_hash=artifact_hash("adapter"), approved_registry_revision=3)
    assert result.allowed is False
    assert result.provider_calls == 0


def test_unknown_state_has_no_second_mutation():
    reconciler = InMemoryReconciler()
    record = reconciler.create_or_get(action_id="a", tenant_id="t", capability_contract_hash=CONTRACT, lease_id="l", credential_grant_id="g", operation="op", target="target", params_hash="p")
    first = reconciler.attempt_once(record, mutate=lambda: True, read_state=lambda: None)
    second = reconciler.attempt_once(record, mutate=lambda: True, read_state=lambda: True)
    assert first.status == VerificationStatus.SIDE_EFFECT_UNKNOWN
    assert second.reason_code == "DUPLICATE_SUPPRESSED"
    assert reconciler.provider_mutation_calls == 1


def test_receipt_chain_and_contract_mismatch_denial():
    fields = {
        "tenant_id": "tenant-a", "mission_id": "m", "action_id": "a",
        "operation_id": "o", "attempt_id": "t", "principal_id": "p",
        "approval_id": "approval", "capability_id": "cap", "capability_version": "1",
        "capability_contract_hash": CONTRACT, "approved_contract_hash": CONTRACT,
        "runtime_contract_hash": CONTRACT, "operation_contract_hash": CONTRACT,
        "registry_revision": 3, "lease_id": "lease", "lease_revision": 1,
        "credential_grant_id": "grant", "executor_id": "executor", "executor_version": "1",
        "executor_artifact_hash": "eh", "adapter_id": "adapter", "adapter_version": "1",
        "adapter_artifact_hash": "ah", "operation": "op", "target": "target",
        "params_hash": "params", "pre_state_hash": "pre", "provider_result_hash": "provider",
        "post_state_hash": "post", "verification_status": "VERIFIED_SUCCESS",
        "verification_reason": "POST_STATE_CONFIRMED", "execution_started_at": NOW.isoformat(),
        "execution_completed_at": NOW.isoformat(), "verified_at": NOW.isoformat(),
    }
    receipt = ActionReceipt.create(**fields)
    assert verify_receipt_chain([receipt], tenant_id="tenant-a")
    with pytest.raises(ReceiptCreationDeniedError):
        ActionReceipt.create(**{**fields, "runtime_contract_hash": "wrong"})


def test_legacy_inventory_has_no_unclassified_present_mutation_surface():
    for surface in LEGACY_CONTAINMENT_MAP:
        if surface.mutation_capable and surface.disposition == LegacyDisposition.NOT_PRESENT:
            continue
        if surface.mutation_capable and surface.disposition == LegacyDisposition.QUARANTINE:
            with pytest.raises(PermissionError):
                deny_legacy_mutation(surface=surface)
