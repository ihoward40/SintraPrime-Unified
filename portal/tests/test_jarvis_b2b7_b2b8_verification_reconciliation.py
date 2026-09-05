from datetime import UTC, datetime

from portal.services.jarvis_verification_reconciliation import (
    InMemoryReconciler,
    OperationState,
    VerificationEvidence,
    VerificationStatus,
    idempotency_key,
    verify_effect,
)


def evidence():
    return VerificationEvidence("action", "tenant", "cap", "1", "contract", "op", "target", "params", "pre", "provider", "post", "readback", "verifier", "1", datetime.now(UTC), datetime.now(UTC), VerificationStatus.VERIFICATION_INCONCLUSIVE, "")


def test_provider_success_requires_independent_post_state():
    decision = verify_effect(evidence=evidence(), provider_reported_success=True, post_state_matches=False, provider_mutation_calls=1, provider_read_calls=1)
    assert decision.status == VerificationStatus.VERIFIED_FAILURE
    assert decision.reason_code == "POST_STATE_CONTRADICTED"


def test_provider_failure_with_effect_is_verified_success():
    decision = verify_effect(evidence=evidence(), provider_reported_success=False, post_state_matches=True, provider_mutation_calls=1, provider_read_calls=1)
    assert decision.status == VerificationStatus.VERIFIED_SUCCESS


def test_inconclusive_is_unknown_without_second_mutation():
    reconciler = InMemoryReconciler()
    record = reconciler.create_or_get(action_id="a", tenant_id="t", capability_contract_hash="c", lease_id="l", credential_grant_id="g", operation="op", target="target", params_hash="p")
    decision = reconciler.attempt_once(record, mutate=lambda: True, read_state=lambda: None)
    assert decision.status == VerificationStatus.SIDE_EFFECT_UNKNOWN
    assert decision.provider_mutation_calls == 1
    again = reconciler.attempt_once(record, mutate=lambda: True, read_state=lambda: True)
    assert again.reason_code == "DUPLICATE_SUPPRESSED"
    assert again.provider_mutation_calls == 1


def test_duplicate_identity_reuses_operation():
    reconciler = InMemoryReconciler()
    kwargs = {
        "action_id": "a", "tenant_id": "t", "capability_contract_hash": "c",
        "lease_id": "l", "credential_grant_id": "g", "operation": "op",
        "target": "target", "params_hash": "p",
    }
    first = reconciler.create_or_get(**kwargs)
    second = reconciler.create_or_get(**kwargs)
    assert first.operation_id == second.operation_id
    assert idempotency_key(tenant_id="t", action_id="a", capability_contract_hash="c", operation="op", target="target", params_hash="p") == first.idempotency_key
