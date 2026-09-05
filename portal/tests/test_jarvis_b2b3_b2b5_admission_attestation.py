"""Focused B2-B3/5 admission and attestation tests."""
from __future__ import annotations

from datetime import UTC, datetime

from portal.services.jarvis_runtime_attestation import (
    RuntimeAttestationEvidence,
    artifact_hash,
    attest_runtime,
)


def evidence(contract_hash="contract", revision=4, executor_id="executor", adapter_id="adapter"):
    return RuntimeAttestationEvidence(
        capability_id="github.issue.add_label",
        capability_version="1.0.0",
        capability_contract_hash=contract_hash,
        registry_revision=revision,
        executor_id=executor_id,
        executor_version="1.0.0",
        executor_artifact_hash=artifact_hash("executor-source"),
        adapter_id=adapter_id,
        adapter_version="1.0.0",
        adapter_artifact_hash=artifact_hash("adapter-source"),
        runtime_config_hash=artifact_hash("config"),
        resolved_policy_versions=("policy.v1",),
        evaluated_at=datetime.now(UTC).isoformat(),
    )


def approvals():
    return {
        "approved_contract_hash": "contract",
        "approved_executor_id": "executor",
        "approved_executor_version": "1.0.0",
        "approved_executor_artifact_hash": artifact_hash("executor-source"),
        "approved_adapter_id": "adapter",
        "approved_adapter_version": "1.0.0",
        "approved_adapter_artifact_hash": artifact_hash("adapter-source"),
        "approved_registry_revision": 4,
    }


def test_valid_runtime_attestation():
    decision = attest_runtime(runtime_contract_hash="contract", evidence=evidence(), **approvals())
    assert decision.allowed is True
    assert decision.provider_calls == 0


def test_contract_mismatch_denied_with_zero_provider_calls():
    decision = attest_runtime(runtime_contract_hash="runtime-other", evidence=evidence(), **approvals())
    assert decision.allowed is False
    assert decision.reason_code == "CONTRACT_HASH_MISMATCH"
    assert decision.provider_calls == 0


def test_executor_and_adapter_identity_mismatch_denied():
    decision = attest_runtime(runtime_contract_hash="contract", evidence=evidence(executor_id="wrong", adapter_id="wrong"), **approvals())
    assert decision.allowed is False
    assert decision.provider_calls == 0


def test_artifact_and_revision_mismatch_denied():
    current = evidence(revision=9)
    decision = attest_runtime(runtime_contract_hash="contract", evidence=current, **approvals())
    assert decision.allowed is False
    assert decision.reason_code == "EXECUTOR_ARTIFACT_MISMATCH" or decision.reason_code == "REGISTRY_REVISION_MISMATCH"
    assert decision.provider_calls == 0
