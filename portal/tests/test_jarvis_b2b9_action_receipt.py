from dataclasses import replace

import pytest

from portal.services.jarvis_action_receipt_b2 import (
    ActionReceipt,
    ReceiptCreationDeniedError,
    verify_receipt,
    verify_receipt_chain,
)

BASE = {
    "tenant_id": "tenant", "mission_id": "mission", "action_id": "action",
    "operation_id": "operation", "attempt_id": "attempt", "principal_id": "principal",
    "approval_id": "approval", "capability_id": "cap", "capability_version": "1",
    "capability_contract_hash": "contract", "approved_contract_hash": "contract",
    "runtime_contract_hash": "contract", "operation_contract_hash": "contract",
    "registry_revision": 3, "lease_id": "lease",
    "lease_revision": 1, "credential_grant_id": "grant", "executor_id": "executor",
    "executor_version": "1", "executor_artifact_hash": "executor-hash", "adapter_id": "adapter",
    "adapter_version": "1", "adapter_artifact_hash": "adapter-hash", "operation": "op",
    "target": "target", "params_hash": "params", "pre_state_hash": "pre",
    "provider_result_hash": "provider", "post_state_hash": "post",
    "verification_status": "VERIFIED_SUCCESS", "verification_reason": "POST_STATE_CONFIRMED",
    "execution_started_at": "2026-01-01T00:00:00+00:00", "execution_completed_at": "2026-01-01T00:00:01+00:00",
    "verified_at": "2026-01-01T00:00:02+00:00",
}


def test_receipt_hash_is_valid_and_material_mutation_detected():
    receipt = ActionReceipt.create(**BASE)
    assert verify_receipt(receipt)
    assert not verify_receipt(replace(receipt, target="other"))
    assert not verify_receipt(replace(receipt, verification_status="SIDE_EFFECT_UNKNOWN"))
    assert not verify_receipt(replace(receipt, tenant_id="other"))


def test_chain_detects_predecessor_tampering_and_gap():
    first = ActionReceipt.create(**BASE)
    second = ActionReceipt.create(**BASE, receipt_id="second", previous_receipt_hash=first.receipt_hash)
    assert verify_receipt_chain([first, second], tenant_id="tenant")
    assert not verify_receipt_chain([second], tenant_id="tenant")
    assert not verify_receipt_chain([replace(second, previous_receipt_hash="wrong")], tenant_id="tenant")
    assert not verify_receipt_chain([first, replace(second, tenant_id="other")], tenant_id="tenant")


def test_duplicate_receipt_identity_rejected():
    first = ActionReceipt.create(**BASE)
    assert not verify_receipt_chain([first, first], tenant_id="tenant")


def test_contract_hash_disagreement_denies_creation():
    values = {**BASE, "runtime_contract_hash": "other"}
    with pytest.raises(ReceiptCreationDeniedError):
        ActionReceipt.create(**values)


def test_receipt_is_not_authority():
    receipt = ActionReceipt.create(**BASE)
    with pytest.raises(ReceiptCreationDeniedError):
        receipt.as_authority()
