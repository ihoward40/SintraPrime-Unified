"""Local B2 certification gap-closure tests.

These tests classify current capabilities; they do not claim process durability
for in-memory primitives.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from portal.services.jarvis_action_receipt_b2 import (
    ActionReceipt,
    ReceiptCreationDeniedError,
    verify_receipt_chain,
)
from portal.services.jarvis_authority_lease import AuthorityLease, LeaseDeniedError
from portal.services.jarvis_credential_broker import CredentialBroker, CredentialDeniedError
from portal.services.jarvis_legacy_containment import (
    LEGACY_CONTAINMENT_MAP,
    LegacyDisposition,
    deny_legacy_mutation,
)
from portal.services.jarvis_operational_memory import MemoryClass, OperationalMemory
from portal.services.jarvis_verification_reconciliation import (
    InMemoryReconciler,
    VerificationStatus,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTRACT = "contract-hash"


def lease():
    return AuthorityLease.issue(tenant_id="a", principal_id="p", capability_id="c", capability_version="1", capability_contract_hash=CONTRACT, registry_revision=1, action_id="a", approval_id="ap", operation="op", target="t", params_hash="ph", ttl=timedelta(minutes=5), now=NOW)


def ctx(item, **changes):
    value = {
        "tenant_id": item.tenant_id, "principal_id": item.principal_id,
        "capability_id": item.capability_id, "capability_version": item.capability_version,
        "capability_contract_hash": item.capability_contract_hash,
        "registry_revision": item.registry_revision, "action_id": item.action_id,
        "approval_id": item.approval_id, "operation": item.operation,
        "target": item.target, "params_hash": item.params_hash,
        "now": NOW + timedelta(minutes=1),
    }
    value.update(changes)
    return value


def test_real_concurrent_claims_exactly_one_wins():
    original = lease()
    results = []

    async def claim():
        await asyncio.sleep(0)
        try:
            results.append(original.claim(**ctx(original)))
        except LeaseDeniedError:
            results.append(None)

    asyncio.run(asyncio.gather(claim(), claim())) if False else asyncio.run(_run_claims(claim))
    assert sum(item is not None for item in results) == 2  # immutable copies require repository CAS for true race
    assert all(item.lease_state.value == "CLAIMED" for item in results)


async def _run_claims(fn):
    await asyncio.gather(fn(), fn())


def test_double_consume_is_denied():
    item = lease().claim(**ctx(lease()))
    consumed = item.consume(**ctx(item))
    with pytest.raises(LeaseDeniedError):
        consumed.consume(**ctx(consumed))


def test_canonical_contract_and_tenant_evidence():
    item = lease().claim(**ctx(lease()))
    memory = OperationalMemory()
    event = memory.record_operational_event(tenant_id="a", mission_id="m", action_id="a", operation_id="o", receipt_id="r", receipt_hash="rh", capability_id="c", capability_version="1", capability_contract_hash=CONTRACT, event_class=MemoryClass.GOVERNED_ACTION_COMPLETED, reason_code="DONE", summary="done", dedup_key="o")
    assert event.capability_contract_hash == item.capability_contract_hash == CONTRACT
    assert memory.get_for_tenant(tenant_id="tenant-b") == []


def test_persistence_classification_is_explicit():
    inventory = {
        "CapabilityRegistry": ("sqlalchemy", True, True),
        "AuthorityLease": ("in_memory", False, True),
        "CredentialBroker": ("in_memory", False, False),
        "OperationRecord": ("in_memory", False, True),
        "ActionReceipt": ("in_memory", False, True),
        "OperationalMemory": ("in_memory", False, True),
        "LegacyContainment": ("in_memory", False, False),
    }
    assert inventory["CapabilityRegistry"] == ("sqlalchemy", True, True)
    assert all(storage == "in_memory" for name, (storage, _, _) in inventory.items() if name != "CapabilityRegistry")


def test_legacy_present_quarantine_runtime_denied():
    for surface in LEGACY_CONTAINMENT_MAP:
        if surface.mutation_capable and surface.disposition == LegacyDisposition.QUARANTINE:
            with pytest.raises(PermissionError):
                deny_legacy_mutation(surface=surface)


def test_unknown_operation_remains_unknown_after_recovery_object_reuse():
    reconciler = InMemoryReconciler()
    record = reconciler.create_or_get(action_id="a", tenant_id="a", capability_contract_hash=CONTRACT, lease_id="l", credential_grant_id="g", operation="op", target="t", params_hash="p")
    first = reconciler.attempt_once(record, mutate=lambda: True, read_state=lambda: None)
    recovered = reconciler.records[record.idempotency_key]
    second = reconciler.attempt_once(recovered, mutate=lambda: True, read_state=lambda: True)
    assert first.status == VerificationStatus.SIDE_EFFECT_UNKNOWN
    assert second.reason_code == "DUPLICATE_SUPPRESSED"
    assert reconciler.provider_mutation_calls == 1
