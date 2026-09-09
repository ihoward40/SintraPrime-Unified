"""Wave 3 MEMORY + RUNTIME-RECEIPT layers — write requests, provenance,
receipts, outcomes (§21-§23, §38-§39, §44)."""
from __future__ import annotations

import pytest

from agent_runtime.context import BudgetExhaustedError, BudgetTracker, ContextPackage
from agent_runtime.manifest import BudgetPolicy, MemoryScope
from agent_runtime.receipts import (
    AgentRuntimeReceipt,
    MemoryWriteAuthority,
    MemoryWriteDeniedError,
    RuntimeOutcome,
)


class TestMemoryScopeContract:
    def test_write_request_requires_manifest_permission(self):
        a = MemoryWriteAuthority()
        with pytest.raises(MemoryWriteDeniedError, match="not manifest-permitted"):
            a.submit(
                agent_id="agent.x",
                proposed_scope="MISSION",
                content="c",
                mission_id="m",
                tenant="t",
                evidence_reference="ev",
            )

    def test_governance_memory_never_writable(self):
        a = MemoryWriteAuthority()
        a.allow_write_scope("agent.x", "GOVERNANCE_READONLY")  # even misconfigured
        with pytest.raises(MemoryWriteDeniedError, match="read-only"):
            a.submit(
                agent_id="agent.x",
                proposed_scope="GOVERNANCE_READONLY",
                content="c",
                evidence_reference="ev",
            )

    def test_anonymous_write_refused(self):
        a = MemoryWriteAuthority()
        a.allow_write_scope("agent.x", "MISSION")
        with pytest.raises(MemoryWriteDeniedError, match=r"evidence_reference required|NO_MISSION"):
            a.submit(agent_id="agent.x", proposed_scope="MISSION", content="c", evidence_reference="")

    def test_provenance_complete_on_success(self):
        a = MemoryWriteAuthority()
        a.allow_write_scope("agent.howard", "MISSION")
        rec = a.submit(
            agent_id="agent.howard",
            proposed_scope="MISSION",
            content="finding",
            mission_id="M1",
            tenant="t1",
            evidence_reference="ev-1",
            classification="VERIFIED",
            confidence=0.9,
        )
        assert rec.actor_agent == "agent.howard"
        assert rec.mission_id == "M1"
        assert rec.tenant == "t1"
        assert rec.timestamp
        assert rec.trust_level in ("VERIFIED", "GOVERNING", "OBSERVED")
        assert a.persisted == [rec]


class TestRuntimeReceipts:
    def test_receipt_roundtrip_all_outcomes(self):
        for outcome in RuntimeOutcome:
            r = AgentRuntimeReceipt(
                agent_id="agent.a",
                agent_version="1.0.0",
                mission_id="M1",
                result=outcome,
                capabilities_used=("READ_REPOSITORY",),
                provider_calls=2,
                tool_calls=3,
                duration_seconds=1.5,
                evidence_refs=("ev-1",),
            )
            assert r.result is outcome

    def test_refused_is_explicit_not_failed(self):
        r = AgentRuntimeReceipt(
            agent_id="agent.a", agent_version="1.0.0", mission_id="M1", result=RuntimeOutcome.REFUSED
        )
        assert r.result is RuntimeOutcome.REFUSED
        assert r.result is not RuntimeOutcome.FAILED

    def test_receipt_has_no_reasoning_field(self):
        fields = set(AgentRuntimeReceipt.model_fields)
        assert not any("thought" in f or "reasoning" in f or "chain" in f for f in fields)


class TestContextAndBudget:
    def test_context_minimization(self):
        ctx = ContextPackage(
            mission_id="M1",
            mission_type="t",
            parent_agent="agent.hermes",
            agent_id="agent.w",
            delegation_id="d1",
            tenant="t1",
            payload={"file": "a.py"},
        )
        assert ctx.memory_scope is MemoryScope.NONE  # minimal by default
        assert set(ctx.payload) == {"file"}

    def test_oversized_context_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="minimization"):
            ContextPackage(
                mission_id="M1",
                mission_type="t",
                parent_agent="p",
                agent_id="a",
                delegation_id="d",
                tenant="t",
                payload={"blob": "x" * 200_000},
            )

    def test_iteration_exhaustion_bounded(self):
        def _run_four():
            bt = BudgetTracker(BudgetPolicy(max_iterations=3, timeout_seconds=60))
            for _ in range(4):
                bt.begin_iteration()

        with pytest.raises(BudgetExhaustedError):
            _run_four()

    def test_provider_and_tool_budgets(self):
        bt = BudgetTracker(BudgetPolicy(max_iterations=10, timeout_seconds=60, max_provider_calls=1, max_tool_calls=1))
        bt.consume_provider_call()
        with pytest.raises(BudgetExhaustedError):
            bt.consume_provider_call()
        bt.consume_tool_call()
        with pytest.raises(BudgetExhaustedError):
            bt.consume_tool_call()

    def test_identical_request_loop_detected(self):
        bt = BudgetTracker(BudgetPolicy())
        hints = [bt.observe("same_request", "same_output") for _ in range(8)]
        # ladder: None -> RETRY x2 -> STRATEGY x3 -> STOP (never an infinite loop)
        assert hints[0] is None
        assert any(h == "STRATEGY_TRANSITION" for h in hints)
        assert hints[-1] == "NO_PROGRESS_STOP"

    def test_varied_requests_no_loop_flag(self):
        bt = BudgetTracker(BudgetPolicy())
        assert bt.observe("r1", "o1") is None
        assert bt.observe("r2", "o2") is None
        assert bt.observe("r3", "o3") is None
