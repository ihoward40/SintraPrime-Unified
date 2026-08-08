"""Governance expansion tests — §140-§145 mandatory proof conditions."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from collaboration.governance.budget_governor import BudgetGovernor
from collaboration.governance.capability_lease import LeaseService
from collaboration.governance.causal import CausalRecord, CausalStore
from collaboration.governance.dead_letter import DeadLetterQueue
from collaboration.governance.dlp import DLPScanner
from collaboration.governance.effect_receipts import EffectService
from collaboration.governance.goal_drift import (
    GoalDriftDetector,
    MissionContract,
    ScopeCreepDetector,
)
from collaboration.governance.invariants import (
    ActionContext,
    Invariant,
    InvariantEngine,
)
from collaboration.governance.lineage import (
    EvidenceScorer,
    LineageClass,
    LineageTag,
    TaintTracker,
)
from collaboration.governance.linter import (
    ArchitectureLinter,
    GovernanceLinter,
)
from collaboration.governance.quarantine import (
    AgentQuarantineService,
    QuarantineReason,
)
from collaboration.governance.uncertainty import (
    Assumption,
    AssumptionLedger,
    UncertaintyItem,
    UncertaintyRegistry,
)
from collaboration.policies import (
    EventPolicyEngine,
)
from collaboration.services.store import CollaborationStore

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def tmp_base():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def store(tmp_base):
    return CollaborationStore(tmp_base / "store")


@pytest.fixture
def invariant_engine():
    return InvariantEngine()


@pytest.fixture
def quarantine_service(store):
    return AgentQuarantineService(store)


@pytest.fixture
def lease_service(store):
    return LeaseService(store, default_ttl_minutes=60)


@pytest.fixture
def dlq(store):
    return DeadLetterQueue(store)


@pytest.fixture
def effect_service(store):
    return EffectService(store)


@pytest.fixture
def budget_governor():
    return BudgetGovernor(max_tokens=1000, max_calls=5, max_cost=10.0)


@pytest.fixture
def causal_store(store):
    return CausalStore(store)


@pytest.fixture
def uncertainty_registry(store):
    return UncertaintyRegistry(store)


@pytest.fixture
def assumption_ledger(store):
    return AssumptionLedger(store)


@pytest.fixture
def linter():
    return GovernanceLinter()


@pytest.fixture
def arch_linter():
    return ArchitectureLinter()


# ─── §140: Constitutional tests ─────────────────────────────────────


class TestConstitutionalInvariants:
    def test_agent_cannot_self_approve(self, invariant_engine):
        ctx = ActionContext(
            action="approve",
            actor_id="agent-1",
            actor_type="agent",
            approver_id="agent-1",
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_AGENT_SELF_APPROVAL for v in violations)

    def test_agent_cannot_grant_capability(self, invariant_engine):
        ctx = ActionContext(
            action="grant_capability",
            actor_id="agent-1",
            actor_type="agent",
            target_id="agent-1",
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_AGENT_SELF_PERMISSION_GRANT for v in violations)

    def test_consequential_action_requires_authority(self, invariant_engine):
        ctx = ActionContext(
            action="deploy",
            actor_id="agent-1",
            actor_type="agent",
            authority_class="A3",
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(
            v.invariant == Invariant.NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY for v in violations
        )

    def test_cross_tenant_blocked(self, invariant_engine):
        ctx = ActionContext(
            action="read",
            actor_id="agent-1",
            tenant_id="t2",
            metadata={"source_tenant": "t1"},
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_CROSS_TENANT_IMPLICIT_ACCESS for v in violations)

    def test_cross_matter_blocked(self, invariant_engine):
        ctx = ActionContext(
            action="read",
            actor_id="agent-1",
            tenant_id="t1",
            matter_id="matter-b",
            metadata={"source_matter": "matter-a"},
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_CROSS_MATTER_IMPLICIT_ACCESS for v in violations)

    def test_unbounded_loop_rejected(self, invariant_engine):
        ctx = ActionContext(
            action="continue",
            actor_id="agent-1",
            hop_count=10,
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP for v in violations)

    def test_bounded_loop_ok(self, invariant_engine):
        ctx = ActionContext(
            action="continue",
            actor_id="agent-1",
            hop_count=3,
            max_hop_count=5,
        )
        violations = invariant_engine.evaluate(ctx)
        assert all(v.invariant != Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP for v in violations)

    def test_implementer_cannot_certify(self, invariant_engine):
        ctx = ActionContext(
            action="certify",
            actor_id="agent-1",
            actor_type="agent",
            metadata={"implementer_id": "agent-1"},
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_CERTIFICATION_BY_IMPLEMENTER for v in violations)

    def test_no_budget_rejected(self, invariant_engine):
        ctx = ActionContext(action="llm_call", actor_id="a1", budget_defined=False)
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_UNBOUNDED_PROVIDER_SPEND for v in violations)

    def test_unregistered_tool_rejected(self, invariant_engine):
        ctx = ActionContext(
            action="tool_execute",
            actor_id="a1",
            capability="unknown_tool",
            capability_registered=False,
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_UNREGISTERED_TOOL_EXECUTION for v in violations)

    def test_unhashed_workflow_rejected(self, invariant_engine):
        ctx = ActionContext(action="workflow_execute", actor_id="a1", workflow_hash="")
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_UNHASHED_WORKFLOW_EXECUTION for v in violations)

    def test_unversioned_policy_rejected(self, invariant_engine):
        ctx = ActionContext(action="policy_execute", actor_id="a1", policy_version="")
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_UNVERSIONED_POLICY_EXECUTION for v in violations)

    def test_public_agent_high_authority_rejected(self, invariant_engine):
        ctx = ActionContext(
            action="act", actor_id="pub1", is_public_agent=True, authority_class="A3"
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_PRIVILEGED_PUBLIC_AGENT for v in violations)

    def test_silent_external_write_rejected(self, invariant_engine):
        ctx = ActionContext(action="write", actor_id="a1", external_write=True, metadata={})
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_SILENT_EXTERNAL_WRITE for v in violations)

    def test_audited_external_write_ok(self, invariant_engine):
        ctx = ActionContext(
            action="write", actor_id="a1", external_write=True, metadata={"audited": True}
        )
        violations = invariant_engine.evaluate(ctx)
        assert all(v.invariant != Invariant.NO_SILENT_EXTERNAL_WRITE for v in violations)

    def test_static_workflow_check(self, invariant_engine):
        violations = invariant_engine.static_check_workflow({})
        assert any(v.invariant == Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP for v in violations)
        assert any(v.invariant == Invariant.NO_UNBOUNDED_PROVIDER_SPEND for v in violations)

    def test_static_workflow_compliant(self, invariant_engine):
        violations = invariant_engine.static_check_workflow(
            {
                "max_iterations": 10,
                "budget": {"max_tokens": 5000},
                "hash": "abc123",
                "version": "1",
            }
        )
        assert not violations


# ─── §140: Dead letter tests ────────────────────────────────────────


class TestDeadLetter:
    def test_failure_persisted(self, dlq):
        entry = dlq.record_failure(
            event_id="e1",
            consumer_id="c1",
            tenant_id="t1",
            channel_id="ch1",
            failure_class="provider_error",
            error="timeout",
        )
        assert entry.failure_count == 1
        loaded = dlq.get("e1")
        assert loaded.failure_count == 1

    def test_retry_bounded(self, dlq):
        dlq.record_failure(
            event_id="e2", consumer_id="c1", tenant_id="t1", channel_id="ch1", failure_class="error"
        )
        dlq.record_failure(
            event_id="e2", consumer_id="c1", tenant_id="t1", channel_id="ch1", failure_class="error"
        )
        dlq.record_failure(
            event_id="e2", consumer_id="c1", tenant_id="t1", channel_id="ch1", failure_class="error"
        )
        entry = dlq.get("e2")
        assert entry.exhausted
        assert entry.quarantined
        assert not entry.retry_eligible

    def test_poison_event_quarantined(self, dlq):
        entry = dlq.mark_quarantined("e3", reason="poison")
        assert entry.quarantined
        assert dlq.is_poison("e3")


# ─── §140: Agent quarantine tests ──────────────────────────────────


class TestAgentQuarantine:
    def test_quarantine_blocks_activation(self, quarantine_service):
        quarantine_service.quarantine("agent-1", QuarantineReason.LOOP_BEHAVIOR, trigger="test")
        assert quarantine_service.is_quarantined("agent-1") is True
        rec = quarantine_service.get("agent-1")
        assert rec.active

    def test_release_restores(self, quarantine_service):
        quarantine_service.quarantine("agent-2", QuarantineReason.COST_ANOMALY)
        quarantine_service.release("agent-2")
        assert quarantine_service.is_quarantined("agent-2") is False

    def test_quarantine_survives_restart(self, store):
        svc1 = AgentQuarantineService(store)
        svc1.quarantine("agent-3", QuarantineReason.DATA_BOUNDARY_VIOLATION)
        svc2 = AgentQuarantineService(store)
        assert svc2.is_quarantined("agent-3") is True

    def test_list_active(self, quarantine_service):
        quarantine_service.quarantine("a1", QuarantineReason.SECURITY_VIOLATION)
        quarantine_service.quarantine("a2", QuarantineReason.LOOP_BEHAVIOR)
        assert len(quarantine_service.list_active()) == 2


# ─── §140: Capability lease tests ───────────────────────────────────


class TestCapabilityLease:
    def test_valid_lease(self, lease_service):
        lease_service.issue(
            lease_id="l1", agent_id="a1", capability="read", scope="repo/x", purpose="pr_review"
        )
        ok, reason = lease_service.validate(
            "l1", capability="read", scope="repo/x", purpose="pr_review"
        )
        assert ok is True
        assert reason == "valid"

    def test_expired_lease_rejected(self, lease_service):
        lease_service.issue(
            lease_id="l2",
            agent_id="a1",
            capability="read",
            scope="repo/x",
            purpose="pr_review",
            ttl_minutes=-1,
        )
        ok, reason = lease_service.validate(
            "l2", capability="read", scope="repo/x", purpose="pr_review"
        )
        assert ok is False
        assert "expired" in reason

    def test_wrong_purpose_rejected(self, lease_service):
        lease_service.issue(
            lease_id="l3", agent_id="a1", capability="read", scope="repo/x", purpose="pr_review"
        )
        ok, reason = lease_service.validate(
            "l3", capability="read", scope="repo/x", purpose="deploy"
        )
        assert ok is False
        assert "purpose_mismatch" in reason

    def test_wrong_scope_rejected(self, lease_service):
        lease_service.issue(
            lease_id="l4", agent_id="a1", capability="read", scope="repo/x", purpose="pr_review"
        )
        ok, reason = lease_service.validate(
            "l4", capability="read", scope="repo/y", purpose="pr_review"
        )
        assert ok is False
        assert "scope_mismatch" in reason

    def test_revoked_lease_rejected(self, lease_service):
        lease_service.issue(
            lease_id="l5", agent_id="a1", capability="read", scope="repo/x", purpose="pr_review"
        )
        lease_service.revoke("l5")
        ok, reason = lease_service.validate(
            "l5", capability="read", scope="repo/x", purpose="pr_review"
        )
        assert ok is False
        assert "revoked" in reason

    def test_list_for_agent(self, lease_service):
        lease_service.issue(lease_id="l6", agent_id="a1", capability="read", scope="r", purpose="p")
        lease_service.issue(lease_id="l7", agent_id="a2", capability="read", scope="r", purpose="p")
        leases = lease_service.list_for_agent("a1")
        assert len(leases) == 1


# ─── §140: Data taint tests ────────────────────────────────────────


class TestLineageTaint:
    def test_external_unverified_persists(self):
        tracker = TaintTracker()
        tracker.tag(LineageTag(artifact_id="src1", lineage_class=LineageClass.EXTERNAL_UNVERIFIED))
        derived = tracker.propagate("derived1", "src1")
        assert derived.lineage_class == LineageClass.EXTERNAL_UNVERIFIED

    def test_combine_weakest(self):
        tracker = TaintTracker()
        tracker.tag(LineageTag(artifact_id="src1", lineage_class=LineageClass.EXTERNAL_UNVERIFIED))
        tracker.tag(LineageTag(artifact_id="src2", lineage_class=LineageClass.VERIFIED))
        combined = tracker.combine("src1", "src2")
        assert combined == LineageClass.EXTERNAL_UNVERIFIED

    def test_evidence_scorer(self):
        scorer = EvidenceScorer()
        scorer.register_sources("art1", ["primary_source", "secondary_source"])
        result = scorer.score("art1")
        assert result["source_diversity"] == 2
        assert result["has_primary_source"]


# ─── §140: Uncertainty/assumption tests ────────────────────────────


class TestUncertaintyAssumption:
    def test_register_and_resolve(self, uncertainty_registry):
        item = UncertaintyItem(id="u1", uncertainty_type="unknown", description="is it secure?")
        uncertainty_registry.register(item)
        open_items = uncertainty_registry.list_open()
        assert len(open_items) == 1
        uncertainty_registry.resolve("u1", "confirmed secure")
        assert len(uncertainty_registry.list_open()) == 0

    def test_assumption_lifecycle(self, assumption_ledger):
        a = Assumption(id="a1", assumption="provider is reliable", source="test", owner="eng")
        assumption_ledger.register(a)
        assert len(assumption_ledger.list_active()) == 1
        assumption_ledger.invalidate("a1")
        assert len(assumption_ledger.list_active()) == 0


# ─── §140: Effect receipt + idempotency tests ──────────────────────


class TestEffectReceipt:
    def test_apply_first_time(self, effect_service):
        r1 = effect_service.apply(
            effect_id="ef1",
            operation="merge",
            target="repo",
            idempotency_key="ik1",
            before_state="open",
            after_state="merged",
            authorization="approved",
            result="done",
        )
        assert r1.effect_id == "ef1"
        assert r1.receipt_hash

    def test_idempotent_retry(self, effect_service):
        r1 = effect_service.apply(
            effect_id="ef2",
            operation="deploy",
            target="prod",
            idempotency_key="ik2",
            before_state="v1",
            after_state="v2",
            authorization="approved",
            result="ok",
        )
        r2 = effect_service.apply(
            effect_id="ef2_dupe",
            operation="deploy",
            target="prod",
            idempotency_key="ik2",
            before_state="v1",
            after_state="v3",
            authorization="approved",
            result="ok",
        )
        assert r1.effect_id == r2.effect_id  # same receipt returned
        assert r1.receipt_hash == r2.receipt_hash

    def test_hash_verify(self, effect_service):
        effect_service.apply(
            effect_id="ef3",
            operation="write",
            target="db",
            idempotency_key="ik3",
            before_state="",
            after_state="x",
            authorization="auth",
            result="ok",
        )
        assert effect_service.verify_hash("ik3") is True


# ─── §140: Budget governor tests ────────────────────────────────────


class TestBudgetGovernor:
    def test_hard_token_limit(self, budget_governor):
        assert budget_governor.can_spend(tokens=900) is True
        budget_governor.record(tokens=900)
        assert budget_governor.can_spend(tokens=200) is False
        status = budget_governor.record(tokens=200)
        assert status == "BLOCKED_BUDGET"

    def test_hard_call_limit(self):
        bg = BudgetGovernor(max_calls=2)
        bg.record(calls=1)
        bg.record(calls=1)
        assert bg.can_spend(calls=1) is False
        status = bg.record(calls=1)
        assert status == "BLOCKED_BUDGET"

    def test_hard_cost_limit(self):
        bg = BudgetGovernor(max_cost=5.0)
        bg.record(cost=3.0)
        bg.record(cost=2.5)
        status = bg.record(cost=0.5)
        assert status == "BLOCKED_BUDGET"

    def test_snapshot(self, budget_governor):
        s = budget_governor.snapshot()
        assert s["status"] == "OK"
        assert s["max_tokens"] == 1000


# ─── §140: Causal explanation tests ────────────────────────────────


class TestCausal:
    def test_record_and_explain(self, causal_store):
        rec = CausalRecord(
            action_id="act1",
            triggering_event_id="e1",
            agent_selected="a1",
            selection_reason="capability_match",
            provider="openai",
        )
        causal_store.record(rec)
        result = causal_store.explain_dict("act1")
        assert result["found"] is True
        assert result["agent_selected"] == "a1"

    def test_missing_action(self, causal_store):
        result = causal_store.explain_dict("nonexistent")
        assert result["found"] is False


# ─── §144-§145: Linter tests ───────────────────────────────────────


class TestGovernanceLinter:
    def test_unbounded_loop_detected(self, linter):
        result = linter.lint_workflow({})
        assert result.passed is False
        assert any(i.rule == "UNBOUNDED_LOOP" for i in result.issues)

    def test_missing_budget_detected(self, linter):
        result = linter.lint_workflow({"max_iterations": 10})
        assert any(i.rule == "MISSING_BUDGET" for i in result.issues)

    def test_self_certification_detected(self, linter):
        result = linter.lint_workflow({"implementer_id": "a1", "certifier_id": "a1"})
        assert any(i.rule == "SELF_CERTIFICATION" for i in result.issues)

    def test_high_authority_no_approval(self, linter):
        result = linter.lint_workflow({"authority_class": "A4"})
        assert any(i.rule == "HIGH_AUTHORITY_NO_APPROVAL" for i in result.issues)

    def test_public_agent_high_authority(self, linter):
        result = linter.lint_agent_contract({"public_agent": True, "authority_class": "A3"})
        assert any(i.rule == "PRIVILEGED_PUBLIC_AGENT" for i in result.issues)

    def test_binding_unauthorized_all_messages(self, linter):
        result = linter.lint_binding({"response_mode": "all_messages"})
        assert any(i.rule == "UNAUTHORIZED_ALL_MESSAGES" for i in result.issues)

    def test_compliant_workflow(self, linter):
        result = linter.lint_workflow(
            {"max_iterations": 10, "budget": {}, "hash": "x", "version": "1"}
        )
        assert result.passed is True

    def test_architecture_linter(self, arch_linter):
        result = arch_linter.scan_file("import openai\nclient = openai.Client()\n", "test.py")
        assert not result.passed

    def test_architecture_linter_clean(self, arch_linter):
        result = arch_linter.scan_file("print('hello')\n", "test.py")
        assert result.passed


# ─── §140: Goal drift tests ────────────────────────────────────────


class TestGoalDrift:
    def test_unauthorized_repo_detected(self):
        contract = MissionContract(scope_repos=["repo-1"])
        detector = GoalDriftDetector()
        alert = detector.detect(contract, actual_repo="repo-evil")
        assert alert is not None
        assert alert.detector == "goal_drift"

    def test_unauthorized_matter_detected(self):
        contract = MissionContract(scope_matters=["matter-a"])
        detector = GoalDriftDetector()
        alert = detector.detect(contract, actual_matter="matter-b")
        assert alert is not None

    def test_authorized_repo_ok(self):
        contract = MissionContract(scope_repos=["repo-1"])
        detector = GoalDriftDetector()
        alert = detector.detect(contract, actual_repo="repo-1")
        assert alert is None


class TestScopeCreep:
    def test_budget_exceeded(self):
        contract = MissionContract(approved_token_budget=1000)
        detector = ScopeCreepDetector()
        alerts = detector.detect(contract, actual_tokens=2000)
        assert len(alerts) > 0
        assert any(a.severity == "CRITICAL" for a in alerts)


# ─── §140: DLP tests ───────────────────────────────────────────────


class TestDLP:
    def test_secret_in_payload_detected(self):
        scanner = DLPScanner()
        verdict = scanner.scan("api_key: sk-live-1234567890abcdef")
        assert verdict.safe is False
        assert verdict.secret_found

    def test_clean_payload_ok(self):
        scanner = DLPScanner()
        verdict = scanner.scan("Hello, the analysis looks good.")
        assert verdict.safe is True

    def test_wrong_tenant_detected(self):
        scanner = DLPScanner()
        verdict = scanner.scan("data", expected_tenant="t1", actual_tenant="t2")
        assert verdict.safe is False
        assert verdict.wrong_tenant

    def test_wrong_matter_detected(self):
        scanner = DLPScanner()
        verdict = scanner.scan("data", expected_matter="m1", actual_matter="m2")
        assert verdict.safe is False
        assert verdict.wrong_matter


# ─── §140: Cross-tenant/matter via invariant engine ────────────────


class TestCrossTenantMatter:
    def test_event_injection_blocked(self, invariant_engine):
        ctx = ActionContext(
            action="activate", actor_id="a1", tenant_id="t2", metadata={"source_tenant": "t1"}
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_CROSS_TENANT_IMPLICIT_ACCESS for v in violations)

    def test_matter_isolation(self, invariant_engine):
        ctx = ActionContext(
            action="activate",
            actor_id="a1",
            tenant_id="t1",
            matter_id="matter-b",
            metadata={"source_matter": "matter-a"},
        )
        violations = invariant_engine.evaluate(ctx)
        assert any(v.invariant == Invariant.NO_CROSS_MATTER_IMPLICIT_ACCESS for v in violations)


# ─── §140: Policy engine integration (quarantine) ──────────────────


class TestPolicyQuarantineIntegration:
    def test_quarantine_skips_activation(self, quarantine_service):
        quarantine_service.quarantine("blocked-agent", QuarantineReason.SECURITY_VIOLATION)
        from collaboration.models import AgentChannelBinding, EventEnvelope
        from collaboration.models.enums import EventType

        ep = EventPolicyEngine(quarantine_service=quarantine_service)
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch1"
        )
        binding = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch1",
            agent_id="blocked-agent",
            allowed_event_types=["agent_mentioned"],
        )
        d = ep.evaluate(evt, binding)
        assert d.allow is False
        assert "quarantine" in d.skipped_reasons

    def test_clean_agent_not_quarantined(self, quarantine_service):
        from collaboration.models import AgentChannelBinding, EventEnvelope
        from collaboration.models.enums import EventType

        ep = EventPolicyEngine(quarantine_service=quarantine_service)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch1",
            actor_type="system",
        )
        binding = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch1",
            agent_id="clean-agent",
            allowed_event_types=["agent_mentioned"],
        )
        d = ep.evaluate(evt, binding)
        assert d.allow is True


# ─── §140: Persistence across restart ──────────────────────────────


class TestPersistenceRestart:
    def test_quarantine_survives(self, store):
        svc = AgentQuarantineService(store)
        svc.quarantine("a1", QuarantineReason.SECURITY_VIOLATION)
        svc2 = AgentQuarantineService(store)
        assert svc2.is_quarantined("a1")

    def test_dead_letter_survives(self, store):
        dlq = DeadLetterQueue(store)
        dlq.record_failure(
            event_id="e1", consumer_id="c1", tenant_id="t1", channel_id="ch1", failure_class="err"
        )
        dlq2 = DeadLetterQueue(store)
        entry = dlq2.get("e1")
        assert entry is not None
        assert entry.failure_count == 1

    def test_lease_survives(self, store):
        ls = LeaseService(store, default_ttl_minutes=120)
        ls.issue(lease_id="l1", agent_id="a1", capability="read", scope="r", purpose="p")
        ls2 = LeaseService(store)
        ok, _ = ls2.validate("l1", capability="read", scope="r", purpose="p")
        assert ok is True

    def test_effect_receipt_survives(self, store):
        es = EffectService(store)
        es.apply(
            effect_id="ef1",
            operation="op",
            target="t",
            idempotency_key="ik1",
            before_state="a",
            after_state="b",
            authorization="auth",
            result="ok",
        )
        es2 = EffectService(store)
        r = es2.get("ik1")
        assert r is not None

    def test_causal_survives(self, store):
        cs = CausalStore(store)
        cs.record(CausalRecord(action_id="a1"))
        cs2 = CausalStore(store)
        result = cs2.explain_dict("a1")
        assert result["found"] is True

    def test_uncertainty_survives(self, store):
        ur = UncertaintyRegistry(store)
        ur.register(UncertaintyItem(id="u1", uncertainty_type="unknown", description="test"))
        ur2 = UncertaintyRegistry(store)
        assert len(ur2.list_open()) == 1

    def test_assumption_survives(self, store):
        al = AssumptionLedger(store)
        al.register(Assumption(id="a1", assumption="x", source="s", owner="o"))
        al2 = AssumptionLedger(store)
        assert len(al2.list_active()) == 1
