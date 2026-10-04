"""
test_gov001a_fail_closed.py — GOV-001A regression suite.

Covers the fail-closed remediation for the governance/risk path:
  1. Unknown actions must fail closed (CRITICAL, requires_approval=True).
  2. Malformed action identifiers must never gain more authority.
  3. A whitelist entry must apply only to its exact action and must never
     override an upstream fail-closed condition.
  4. The @requires_approval(min_risk=...) decorator floor must be enforced.
  5. A sequence containing one unknown/malformed/blocked member must not be
     authorized as a whole.
  6. An audit-logging failure must never be treated as action success.

Baseline note: governance/tests/test_r6_r1_fail_closed.py does not exist on
the pinned base revision (051e2594c67a805ceacc66ea2a6fc6db9c0bc793) and no
historical claim about it is treated as evidence here.
"""

from __future__ import annotations

import tempfile

import pytest

from governance.approval_gate import ApprovalGate
from governance.governance_engine import GovernanceEngine
from governance.risk_assessor import RiskAssessor
from governance.risk_types import ApprovalStatus, RiskLevel

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def assessor() -> RiskAssessor:
    return RiskAssessor(org_risk_threshold=RiskLevel.HIGH)


@pytest.fixture
def gate() -> ApprovalGate:
    return ApprovalGate(
        base_url="https://test.example.com",
        auto_approve_threshold=RiskLevel.LOW,
    )


@pytest.fixture
def engine() -> GovernanceEngine:
    tmp_db = tempfile.mktemp(suffix=".db")
    return GovernanceEngine(db_path=tmp_db, approval_timeout_seconds=1)


# ---------------------------------------------------------------------------
# 1. Unknown actions fail closed
# ---------------------------------------------------------------------------


class TestUnknownActionFailsClosed:
    def test_unknown_action_is_critical_and_requires_approval(
        self, assessor: RiskAssessor
    ) -> None:
        risk = assessor.assess("totally_unknown_action_xyz")
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.requires_approval is True
        assert risk.reversible is False
        assert risk.metadata["unrecognized_action"] is True

    def test_unknown_action_fails_closed_even_with_low_org_threshold(
        self,
    ) -> None:
        # Even when the org threshold is LOW (everything above LOW requires
        # approval), the pre-fix defect was comparing the *default* MEDIUM
        # risk against the threshold rather than fail-closing outright. This
        # asserts the fail-closed result holds for any threshold.
        low_threshold_assessor = RiskAssessor(org_risk_threshold=RiskLevel.LOW)
        risk = low_threshold_assessor.assess("another_unknown_action")
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.requires_approval is True

    def test_unknown_action_fails_closed_even_with_critical_org_threshold(
        self,
    ) -> None:
        # The original defect: requires_approval = MEDIUM >= org_threshold.
        # With a CRITICAL threshold this was False for unknown actions.
        critical_threshold_assessor = RiskAssessor(org_risk_threshold=RiskLevel.CRITICAL)
        risk = critical_threshold_assessor.assess("yet_another_unknown_action")
        assert risk.requires_approval is True


# ---------------------------------------------------------------------------
# 2. Malformed action identifiers
# ---------------------------------------------------------------------------


class TestMalformedActionIdentifiers:
    @pytest.mark.parametrize(
        "bad_action",
        [None, "", "   ", "\t\n", 123, 1.5, ["send_payment"], {"action": "send_payment"}, object()],
    )
    def test_malformed_identifier_fails_closed(self, assessor: RiskAssessor, bad_action) -> None:
        risk = assessor.assess(bad_action)
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.requires_approval is True
        assert risk.reversible is False
        assert risk.metadata["unrecognized_action"] is True
        assert risk.metadata["malformed_action"] is True

    def test_malformed_identifier_does_not_raise(self, assessor: RiskAssessor) -> None:
        # Previously None/int/list inputs raised an uncaught TypeError from
        # fnmatch rather than being handled as a controlled fail-closed
        # assessment.
        for bad_action in [None, 123, ["x"]]:
            assessor.assess(bad_action)  # must not raise


# ---------------------------------------------------------------------------
# 3. Whitelist must not bypass fail-closed conditions
# ---------------------------------------------------------------------------


class TestWhitelistDoesNotBypassFailClosed:
    def test_whitelisted_unknown_action_still_pending(
        self, assessor: RiskAssessor, gate: ApprovalGate
    ) -> None:
        gate.auto_approve("weird_unknown_thing")
        risk = assessor.assess("weird_unknown_thing")
        req = gate.request_approval("weird_unknown_thing", risk)
        assert req.status == ApprovalStatus.PENDING

    def test_whitelist_entry_does_not_cover_unmatched_variants(
        self, assessor: RiskAssessor, gate: ApprovalGate
    ) -> None:
        gate.auto_approve("generate_report")
        # A similarly-named but distinct/unregistered action must not
        # inherit the whitelist entry's approval.
        risk = assessor.assess("generate_report_v2_unregistered_variant")
        req = gate.request_approval("generate_report_v2_unregistered_variant", risk)
        assert req.status == ApprovalStatus.PENDING

    def test_ordinary_whitelist_still_works(
        self, assessor: RiskAssessor, gate: ApprovalGate
    ) -> None:
        # Regression guard: the fix must not break legitimate whitelisting
        # of a known, non-fail-closed action.
        gate.auto_approve("generate_report")
        risk = assessor.assess("generate_report")
        req = gate.request_approval("generate_report", risk)
        assert req.status == ApprovalStatus.AUTO_APPROVED


# ---------------------------------------------------------------------------
# 4. Decorator min_risk floor is enforced
# ---------------------------------------------------------------------------


class TestDecoratorMinRiskEnforced:
    def test_min_risk_floor_blocks_low_risk_action(self, engine: GovernanceEngine) -> None:
        # read_data is normally LOW risk / no approval required. Declaring
        # min_risk=CRITICAL must force approval and (with no human approver
        # and a 1s timeout) the call must be blocked.
        @engine.requires_approval(min_risk=RiskLevel.CRITICAL, agent_id="agent-floor")
        def read_data():
            return "should not run"

        with pytest.raises(PermissionError):
            read_data()

    def test_min_risk_floor_does_not_lower_existing_risk(
        self, engine: GovernanceEngine
    ) -> None:
        # send_payment is already CRITICAL; declaring a lower min_risk must
        # not reduce it.
        @engine.requires_approval(min_risk=RiskLevel.LOW, agent_id="agent-pay")
        def send_payment():
            return "paid"

        with pytest.raises(PermissionError):
            send_payment()

    def test_before_action_reports_floor_applied_metadata(
        self, engine: GovernanceEngine
    ) -> None:
        allowed = engine.before_action(
            "read_data", {}, "agent-1", min_risk=RiskLevel.CRITICAL
        )
        assert allowed is False


# ---------------------------------------------------------------------------
# 5. Sequence fail-closed propagation
# ---------------------------------------------------------------------------


class TestSequenceFailClosed:
    def test_one_unknown_action_blocks_whole_sequence(self, assessor: RiskAssessor) -> None:
        results = assessor.assess_sequence(["read_data", "totally_unknown_action", "draft_document"])
        assert all(r.requires_approval is True for r in results)
        assert all(r.metadata["sequence_requires_approval"] is True for r in results)

    def test_one_malformed_action_blocks_whole_sequence(self, assessor: RiskAssessor) -> None:
        results = assessor.assess_sequence(["read_data", None, "draft_document"])
        assert all(r.requires_approval is True for r in results)

    def test_all_low_risk_sequence_is_not_forced(self, assessor: RiskAssessor) -> None:
        results = assessor.assess_sequence(["read_data", "search_database", "list_records"])
        assert all(r.requires_approval is False for r in results)
        assert all(r.metadata["sequence_requires_approval"] is False for r in results)

    def test_sequence_preserves_existing_api_shape(self, assessor: RiskAssessor) -> None:
        results = assessor.assess_sequence(["read_data", "send_payment"])
        assert isinstance(results, list)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# 6. Audit failure must not be treated as action success
# ---------------------------------------------------------------------------


class TestAuditFailureNotActionSuccess:
    def test_audit_failure_after_successful_func_propagates(
        self, engine: GovernanceEngine
    ) -> None:
        class _BrokenAudit:
            def log(self, *args, **kwargs):
                raise RuntimeError("audit storage unavailable")

        engine.audit_trail = _BrokenAudit()

        @engine.requires_approval(min_risk=RiskLevel.LOW, agent_id="agent-audit")
        def read_data():
            return "real result"

        # Whether the audit failure happens pre- or post-execution, it must
        # propagate as an exception rather than silently returning
        # "real result" to the caller as if governance had succeeded.
        with pytest.raises(RuntimeError):
            read_data()

    def test_audit_failure_does_not_relabel_as_action_failure(
        self, engine: GovernanceEngine
    ) -> None:
        # Only the post-execution ("success") audit write is broken; the
        # pre-execution ("auto_allowed") write succeeds normally, so the
        # decorated function actually runs.
        calls = []

        class _PartiallyBrokenAudit:
            def log(self, *args, **kwargs):
                outcome = kwargs.get("outcome")
                calls.append(outcome)
                if outcome == "success":
                    raise RuntimeError("audit storage unavailable")

        engine.audit_trail = _PartiallyBrokenAudit()

        @engine.requires_approval(min_risk=RiskLevel.LOW, agent_id="agent-audit2")
        def read_data():
            return "real result"

        with pytest.raises(RuntimeError):
            read_data()

        # The pre-execution audit succeeded (func ran), then the
        # post-execution "success" audit failed — that failure must
        # propagate as-is and must not trigger a second, mislabeled
        # "failure" audit call for the same invocation.
        assert calls == ["auto_allowed", "success"]
