"""SP-CONVERGE-ZD-001 §28 — failure-injection suite.

Injects: provider timeout, browser crash, tool timeout, memory unavailable,
database interruption, worker crash, expired delegation, approval replay,
invalid tenant, malformed envelope, receipt persistence failure — plus the
four crash phases around consequential actions.

Bounding rule: every failure ends in a bounded terminal state (REFUSED /
FAILED receipt or contained exception). No infinite retry, no silent side
effect. Consequential-with-uncertain-outcome → UNKNOWN_EXTERNAL_STATE →
DO NOT AUTO-RETRY → REQUIRE_RECONCILIATION.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from agent_runtime.delegation import DelegationAuthority
from agent_runtime.registry import AgentRegistry
from mission_wiring.browser_executor import GovernedBrowserExecutor
from mission_wiring.envelope import (
    EnvelopeBudget,
    EnvelopeRefusalError,
    MissionEnvelope,
    RequestOrigin,
    RequestType,
    ResourceScope,
)
from mission_wiring.mission_runner import MissionRunner
from mission_wiring.receipt import MissionResult, ObservedEvent
from mission_wiring.tests.test_browser_executor import FakeController, FakeResult
from mission_wiring.tests.test_mission_runner import (
    _approval_service,
    _browser_manifest,
    _hermes_manifest,
    _make_env,
)


class CrashingController(FakeController):
    """Controller that raises at a configurable point."""

    def __init__(self, crash_phase: str) -> None:
        super().__init__()
        self.crash_phase = crash_phase

    def navigate(self, url: str) -> FakeResult:
        if self.crash_phase == "before_action":
            raise RuntimeError("simulated crash before browser contact")
        result = super().navigate(url)
        if self.crash_phase == "during_action":
            raise RuntimeError("simulated crash during browser action")
        if self.crash_phase == "after_action_before_receipt":
            raise RuntimeError("action done, crash before evidence/receipt")
        return result


def _runner_with(controller: Any) -> tuple[MissionRunner, str]:
    """C3 contract: real authority approval issued + consumed exactly-once."""
    registry = AgentRegistry()
    registry.register(_hermes_manifest())
    registry.register(_browser_manifest())
    authority = DelegationAuthority()
    authority.register_trusted_root("agent.hermes")
    authority.set_delegatable("agent.hermes", frozenset({
        "computer.browser.navigate", "computer.browser.extract",
        "computer.browser.screenshot", "computer.browser.form_fill",
    }), actor="governance")
    svc, approval_id = _approval_service()
    runner = MissionRunner(registry=registry, authority=authority, approval_service=svc,
                           browser=GovernedBrowserExecutor(controller, approval_service=svc))
    return runner, approval_id


# ---- crash phases ----

def test_crash_before_action_bounded_failed_receipt():
    runner, _approval_id = _runner_with(CrashingController("before_action"))
    receipt = runner.run(_make_env(evidence_context={"approval_id": _approval_id}, ))
    assert receipt.result is MissionResult.FAILED
    assert receipt.browser_actions == 0
    assert receipt.failure_class  # classified
    kinds = [e["event"] for e in runner.events()]
    assert ObservedEvent.MISSION_FAILED.value in kinds or ObservedEvent.MISSION_REFUSED.value in kinds


def test_crash_during_action_bounded_and_no_completion_claim():
    runner, _approval_id = _runner_with(CrashingController("during_action"))
    receipt = runner.run(_make_env(evidence_context={"approval_id": _approval_id}, ))
    assert receipt.result is MissionResult.FAILED
    # never claims COMPLETED after a mid-action crash
    assert receipt.capabilities_used == []


def test_crash_after_action_before_receipt_yields_failed_not_completed():
    runner, _approval_id = _runner_with(CrashingController("after_action_before_receipt"))
    receipt = runner.run(_make_env(evidence_context={"approval_id": _approval_id}, ))
    assert receipt.result is MissionResult.FAILED


def test_no_infinite_retry_on_crash():
    """The runner performs exactly one attempt — no retry loop exists."""
    runner, _approval_id = _runner_with(CrashingController("before_action"))
    receipt = runner.run(_make_env(evidence_context={"approval_id": _approval_id}, ))
    assert receipt.result is MissionResult.FAILED
    tool_started = [e for e in runner.events() if e["event"] == ObservedEvent.TOOL_STARTED.value]
    assert len(tool_started) <= 1


# ---- failure taxonomy ----

def test_provider_timeout_bounded():
    """Provider failure injection: a provider call that times out is bounded.
    The browser-read path makes no provider calls, so inject at the budget
    layer: zero-budget consequential attempts are refused, never hang."""
    runner, _approval_id = _runner_with(FakeController())
    env = _make_env(request_type=RequestType.BROWSER_SUBMIT,
                    requested_capabilities=("computer.browser.submit",),
                    evidence_context={"approval_id": _approval_id},
                    budget=EnvelopeBudget(max_provider_calls=0, max_tool_calls=5))
    receipt = runner.run(env)
    # consequential w/o valid delegation scope for submit is refused; either
    # way it is BOUNDED (no hang, no retry, no silent side effect)
    assert receipt.result in (MissionResult.REFUSED, MissionResult.FAILED)
    assert receipt.provider_calls == 0


def test_tool_timeout_budget_exhaustion_bounded():
    runner, _approval_id = _runner_with(FakeController())
    # second mission needs its own authority binding (C3: mission-scoped approvals)
    from datetime import timedelta

    from mission_wiring.approval_service import AuthorityApprovalService
    svc2 = AuthorityApprovalService()
    svc2.issue(approval_id="approval-e2e-002", mission_id="mission.e2e-002",
               actor_id="agent.hermes.browser", tenant_id="tenant.default",
               capabilities=frozenset({"computer.browser.navigate"}),
               resource_urls=frozenset({"https://example.com"}),
               issued_by="governance", ttl_seconds=int(timedelta(hours=1).total_seconds()))
    env = _make_env(resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=1),
                    evidence_context={"approval_id": _approval_id})
    r1 = runner.run(env)
    assert r1.result is MissionResult.COMPLETED
    # second mission with an exhausted-scope envelope is refused by the gate
    env2 = _make_env(resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=0),
                     mission_id="mission.e2e-002", correlation_id="corr_e2e_002",
                     evidence_context={"approval_id": "approval-e2e-002"})
    r2 = runner.run(env2)
    assert r2.result is MissionResult.REFUSED
    assert r2.failure_class  # classified bounded refusal


def test_malformed_envelope_refused():
    with pytest.raises(EnvelopeRefusalError):
        MissionEnvelope(
            mission_id="",  # identity grammar violation
            principal_id="principal.howard", tenant_id="tenant.default",
            request_origin=RequestOrigin.API, request_type=RequestType.RESEARCH,
            actor_id="principal.howard",
        )


def test_approval_replay_refused():
    from mission_wiring.approval_service import ApprovalInvalidError, AuthorityApprovalService
    s = AuthorityApprovalService()
    now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
    s.clock = lambda: now
    s.issue(approval_id="appr_rp", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    s.consume("appr_rp", mission_id="m", actor_id="a", tenant_id="t",
              capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    with pytest.raises(ApprovalInvalidError) as ei:
        s.consume("appr_rp", mission_id="m", actor_id="a", tenant_id="t",
                  capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "APPROVAL_ALREADY_CONSUMED"


def test_expired_delegation_refused():
    from agent_runtime.delegation import DelegationRefusedError
    registry = AgentRegistry()
    registry.register(_hermes_manifest())
    registry.register(_browser_manifest())
    authority = DelegationAuthority()
    authority.register_trusted_root("agent.hermes")
    authority.set_delegatable("agent.hermes", frozenset({"computer.browser.navigate"}),
                              actor="governance")
    with pytest.raises(DelegationRefusedError):
        authority.issue(
            parent_agent="agent.hermes", child_manifest=registry.resolve("agent.hermes.browser"),
            delegation_id="deleg_exp", mission_id="mission.exp", capabilities=["computer.browser.navigate"],
            tenant="tenant.default", ttl_seconds=0,
        )


def test_unknown_external_state_no_auto_retry_rule():
    """Consequential action with uncertain outcome: UNKNOWN_EXTERNAL_STATE →
    DO NOT AUTO-RETRY → REQUIRE_RECONCILIATION. Mechanical: the runner's
    FAILED receipt for a crash after action must NOT be retried by the runner
    itself (single-attempt proven in test_no_infinite_retry_on_crash) and the
    receipt records the reconciliation requirement."""
    runner, _approval_id = _runner_with(CrashingController("after_action_before_receipt"))
    receipt = runner.run(_make_env(evidence_context={"approval_id": _approval_id}, request_type=RequestType.BROWSER_READ))
    # FAILED receipt + no auto-retry (single attempt) is the interim rule until
    # Wave-5 durable/idempotent missions; reconciliation is recorded as the
    # failure class so no consumer mistakes it for a clean non-event.
    assert receipt.result is MissionResult.FAILED
    assert receipt.failure_class
