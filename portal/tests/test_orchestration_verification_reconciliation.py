from portal.services.orchestration.confidence import aggregate_confidence, confidence_label
from portal.services.orchestration.failure_policy import (
    node_status_after_failure,
    run_status_for_limit,
)
from portal.services.orchestration.result_reconciler import reconcile_outputs
from portal.services.orchestration.schemas import NodeStatus, RunStatus
from portal.services.orchestration.verifier import verify_output


def test_verifier_marks_missing_evidence_as_disputed():
    verification = verify_output({"result": "This will always work", "confidence": 0.9}, require_evidence=True)

    assert verification.verification_result == "DISPUTED"
    assert verification.evidence_quality == "unsupported"
    assert verification.confidence_score <= 0.55


def test_reconciliation_preserves_disagreement_and_approval_gate():
    worker = {
        "result": "Use provider A",
        "claims": ["Provider A is safest"],
        "confidence": 0.8,
        "evidence": [{"evidence_quality": "secondary"}],
    }
    checker = {
        "result": "Use provider B",
        "claims": ["Provider B is safest"],
        "confidence": 0.75,
        "evidence": [{"evidence_quality": "test"}],
    }
    verifications = [verify_output(worker), verify_output(checker)]

    reconciliation = reconcile_outputs([worker, checker], verifications, approval_required=True)

    assert reconciliation.disputed_claims
    assert reconciliation.verified_result == {"claims": []}
    assert any("Principal approval required" in item for item in reconciliation.principal_decision_required)
    assert reconciliation.final_confidence > 0


def test_reconciliation_accepts_shared_verified_claim():
    first = {"result": "Tests pass", "claims": ["Tests pass"], "evidence": [{"evidence_quality": "test"}], "confidence": 0.9}
    second = {"result": "Tests pass", "claims": ["Tests pass"], "evidence": [{"evidence_quality": "test"}], "confidence": 0.8}
    verifications = [verify_output(first), verify_output(second)]

    reconciliation = reconcile_outputs([first, second], verifications, approval_required=False)

    assert reconciliation.verified_result == {"claims": ["Tests pass"]}
    assert reconciliation.disputed_claims == []
    assert reconciliation.principal_decision_required == []


def test_confidence_label_uses_evidence_weighting():
    verifications = [
        verify_output({"result": "ok", "confidence": 0.9, "evidence": [{"evidence_quality": "test"}]}),
        verify_output({"result": "ok", "confidence": 0.5, "evidence": [{"evidence_quality": "secondary"}]}),
    ]

    score = aggregate_confidence(verifications)

    assert score == 0.557
    assert confidence_label(score) == "low"


def test_failure_policy_controls_retry_and_partial_status():
    assert node_status_after_failure(0, 1) == NodeStatus.READY
    assert node_status_after_failure(1, 1) == NodeStatus.FAILED
    assert run_status_for_limit(True, completed_nodes=0) == RunStatus.BLOCKED
    assert run_status_for_limit(True, completed_nodes=2) == RunStatus.PARTIAL
