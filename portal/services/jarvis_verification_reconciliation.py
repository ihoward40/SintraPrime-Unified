"""B2-B7/8 verification and idempotent reconciliation primitives."""
from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Callable


class VerificationStatus(enum.StrEnum):
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILURE = "VERIFIED_FAILURE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"
    SIDE_EFFECT_UNKNOWN = "SIDE_EFFECT_UNKNOWN"


class OperationState(enum.StrEnum):
    PENDING = "PENDING"
    ATTEMPTING = "ATTEMPTING"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    VERIFIED = "VERIFIED"
    FAILED_VERIFIED = "FAILED_VERIFIED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass(frozen=True)
class VerificationEvidence:
    action_id: str
    tenant_id: str
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    operation: str
    target: str
    params_hash: str
    pre_state_hash: str
    provider_result_hash: str
    post_state_hash: str
    verification_strategy: str
    verifier_id: str
    verifier_version: str
    started_at: datetime
    completed_at: datetime
    status: VerificationStatus
    reason_code: str


@dataclass(frozen=True)
class VerificationDecision:
    status: VerificationStatus
    reason_code: str
    evidence: VerificationEvidence
    provider_mutation_calls: int
    provider_read_calls: int


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    action_id: str
    tenant_id: str
    capability_contract_hash: str
    lease_id: str
    credential_grant_id: str
    operation: str
    target: str
    params_hash: str
    idempotency_key: str
    state: OperationState
    created_at: datetime
    attempted_at: datetime | None = None
    verified_at: datetime | None = None
    reconciled_at: datetime | None = None
    provider_operation_ref: str | None = None
    latest_verification_status: VerificationStatus | None = None
    revision: int = 0


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def idempotency_key(*, tenant_id: str, action_id: str, capability_contract_hash: str, operation: str, target: str, params_hash: str) -> str:
    return canonical_hash((tenant_id, action_id, capability_contract_hash, operation, target, params_hash))


def verify_effect(
    *,
    evidence: VerificationEvidence,
    provider_reported_success: bool,
    post_state_matches: bool | None,
    provider_mutation_calls: int,
    provider_read_calls: int,
) -> VerificationDecision:
    if post_state_matches is True:
        status = VerificationStatus.VERIFIED_SUCCESS
        reason = "POST_STATE_CONFIRMED"
    elif post_state_matches is False:
        status = VerificationStatus.VERIFIED_FAILURE
        reason = "POST_STATE_CONTRADICTED"
    else:
        status = VerificationStatus.SIDE_EFFECT_UNKNOWN
        reason = "REFETCH_INCONCLUSIVE"
    return VerificationDecision(status, reason, replace(evidence, status=status, reason_code=reason), provider_mutation_calls, provider_read_calls)


class InMemoryReconciler:
    """Deterministic fake boundary; mutation is never retried after uncertainty."""

    def __init__(self) -> None:
        self.records: dict[str, OperationRecord] = {}
        self.provider_mutation_calls = 0
        self.provider_read_calls = 0
        self.provider_state: dict[str, bool] = {}

    def create_or_get(self, *, action_id: str, tenant_id: str, capability_contract_hash: str, lease_id: str, credential_grant_id: str, operation: str, target: str, params_hash: str, now: datetime | None = None) -> OperationRecord:
        key = idempotency_key(tenant_id=tenant_id, action_id=action_id, capability_contract_hash=capability_contract_hash, operation=operation, target=target, params_hash=params_hash)
        existing = self.records.get(key)
        if existing is not None:
            return existing
        record = OperationRecord(str(uuid.uuid4()), action_id, tenant_id, capability_contract_hash, lease_id, credential_grant_id, operation, target, params_hash, key, OperationState.PENDING, now or datetime.now(UTC))
        self.records[key] = record
        return record

    def attempt_once(self, record: OperationRecord, *, mutate: Callable[[], bool], read_state: Callable[[], bool | None]) -> VerificationDecision:
        current = self.records.get(record.idempotency_key, record)
        if current.state in {OperationState.UNKNOWN, OperationState.MANUAL_REVIEW_REQUIRED, OperationState.VERIFIED, OperationState.FAILED_VERIFIED}:
            return self._decision(current, VerificationStatus.SIDE_EFFECT_UNKNOWN, "DUPLICATE_SUPPRESSED", read_state)
        if current.latest_verification_status == VerificationStatus.SIDE_EFFECT_UNKNOWN:
            return self._decision(current, VerificationStatus.SIDE_EFFECT_UNKNOWN, "DUPLICATE_SUPPRESSED", read_state)
        record = replace(current, state=OperationState.ATTEMPTING, attempted_at=datetime.now(UTC), revision=current.revision + 1)
        self.records[record.idempotency_key] = record
        self.provider_mutation_calls += 1
        mutate()
        self.provider_read_calls += 1
        post = read_state()
        evidence = VerificationEvidence(record.action_id, record.tenant_id, "capability", "1", record.capability_contract_hash, record.operation, record.target, record.params_hash, "pre", "provider", "post", "fake-readback", "fake-verifier", "1", record.created_at, datetime.now(UTC), VerificationStatus.VERIFICATION_INCONCLUSIVE, "")
        decision = verify_effect(evidence=evidence, provider_reported_success=post is True, post_state_matches=post, provider_mutation_calls=self.provider_mutation_calls, provider_read_calls=self.provider_read_calls)
        state = OperationState.VERIFIED if decision.status == VerificationStatus.VERIFIED_SUCCESS else OperationState.FAILED_VERIFIED if decision.status == VerificationStatus.VERIFIED_FAILURE else OperationState.MANUAL_REVIEW_REQUIRED
        self.records[record.idempotency_key] = replace(record, state=state, latest_verification_status=decision.status, verified_at=datetime.now(UTC) if state != OperationState.MANUAL_REVIEW_REQUIRED else None, revision=record.revision + 1)
        return decision

    def _decision(self, record, status, reason, read_state):
        self.provider_read_calls += 1
        evidence = VerificationEvidence(record.action_id, record.tenant_id, "capability", "1", record.capability_contract_hash, record.operation, record.target, record.params_hash, "pre", "provider", "post", "fake-readback", "fake-verifier", "1", record.created_at, datetime.now(UTC), status, reason)
        return VerificationDecision(status, reason, evidence, self.provider_mutation_calls, self.provider_read_calls)
