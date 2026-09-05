"""B2-B5 deterministic local runtime attestation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping


@dataclass(frozen=True)
class RuntimeAttestationEvidence:
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    registry_revision: int
    executor_id: str
    executor_version: str
    executor_artifact_hash: str
    adapter_id: str
    adapter_version: str
    adapter_artifact_hash: str
    runtime_config_hash: str
    resolved_policy_versions: tuple[str, ...]
    evaluated_at: str


@dataclass(frozen=True)
class AttestationDecision:
    allowed: bool
    reason_code: str
    evidence: RuntimeAttestationEvidence
    provider_calls: int = 0


def artifact_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def attest_runtime(
    *,
    approved_contract_hash: str,
    runtime_contract_hash: str,
    evidence: RuntimeAttestationEvidence,
    approved_executor_id: str,
    approved_executor_version: str,
    approved_executor_artifact_hash: str,
    approved_adapter_id: str,
    approved_adapter_version: str,
    approved_adapter_artifact_hash: str,
    approved_registry_revision: int,
) -> AttestationDecision:
    checks = (
        (approved_contract_hash == runtime_contract_hash, "CONTRACT_HASH_MISMATCH"),
        (evidence.capability_contract_hash == approved_contract_hash, "EVIDENCE_CONTRACT_MISMATCH"),
        (evidence.executor_id == approved_executor_id, "EXECUTOR_ID_MISMATCH"),
        (evidence.executor_version == approved_executor_version, "EXECUTOR_VERSION_MISMATCH"),
        (evidence.executor_artifact_hash == approved_executor_artifact_hash, "EXECUTOR_ARTIFACT_MISMATCH"),
        (evidence.adapter_id == approved_adapter_id, "ADAPTER_ID_MISMATCH"),
        (evidence.adapter_version == approved_adapter_version, "ADAPTER_VERSION_MISMATCH"),
        (evidence.adapter_artifact_hash == approved_adapter_artifact_hash, "ADAPTER_ARTIFACT_MISMATCH"),
        (evidence.registry_revision == approved_registry_revision, "REGISTRY_REVISION_MISMATCH"),
    )
    for valid, reason_code in checks:
        if not valid:
            return AttestationDecision(False, reason_code, evidence)
    return AttestationDecision(True, "ATTESTATION_VALID", evidence)
