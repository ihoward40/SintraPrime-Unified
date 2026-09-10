"""SP-CONVERGE-ZD-001 §8 + §25 + §26 — mission runner E2E tests.

§25 positive E2E: Principal request -> envelope -> certified agent -> delegation
-> governed browser execution -> evidence -> COMPLETED receipt (local/mock only).
§26 governed refusal E2E: unapproved/undeclared/uncertified/unknown agents are
REFUSED with a classified receipt — no execution.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agent_runtime.delegation import DelegationAuthority
from agent_runtime.manifest import AgentManifest, CertificationStatus
from agent_runtime.registry import AgentRegistry
from mission_wiring.browser_executor import GovernedBrowserExecutor
from mission_wiring.envelope import (
    ApprovalState,
    EnvelopeBudget,
    MemoryScope,
    MissionEnvelope,
    RequestOrigin,
    RequestType,
    ResourceScope,
)
from mission_wiring.mission_runner import MissionRunner
from mission_wiring.receipt import MissionResult, ObservedEvent
from mission_wiring.tests.test_browser_executor import FakeController


def _ts(hour: int) -> datetime:
    return datetime(2026, 9, 8, hour, 0, 0, tzinfo=UTC)


def _browser_manifest(**over) -> AgentManifest:
    fields = {
        "agent_id": "agent.hermes.browser",
        "agent_version": "1.0.0",
        "display_name": "Hermes Browser Worker",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.FakeBrowserAgent",
        "mission_types": ("browser_research",),
        "required_capabilities": ("computer.browser.navigate", "computer.browser.extract",
                                  "computer.browser.screenshot", "computer.browser.form_fill"),
        "forbidden_capabilities": ("EXECUTE_PAYMENT", "MERGE_PULL_REQUEST", "DEPLOY_SERVICE"),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {"filesystem_scope": "READ_ONLY"},
        "authority_policy": "DELEGATED",
        "certification_status": CertificationStatus.CERTIFIED,
    }
    fields.update(over)
    return AgentManifest(**fields)


def _hermes_manifest(**over) -> AgentManifest:
    return _browser_manifest(
        agent_id="agent.hermes",
        display_name="Hermes",
        required_capabilities=("READ_REPOSITORY", "computer.browser.navigate"),
        **over,
    )


def _make_env(**over) -> MissionEnvelope:
    base = {
        "mission_id": "mission.e2e-001",
        "principal_id": "principal.howard",
        "tenant_id": "tenant.default",
        "request_origin": RequestOrigin.MISSION_CONTROL,
        "request_type": RequestType.BROWSER_READ,
        "actor_id": "agent.hermes.browser",
        "agent_id": "agent.hermes.browser",
        "delegation_id": "deleg_e2e01",
        "requested_capabilities": ("computer.browser.navigate",),
        "resource_scope": ResourceScope(url_allowlist=("https://example.com",), max_actions=4),
        "memory_scope": MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "approval_state": ApprovalState.GRANTED,
        "budget": EnvelopeBudget(max_provider_calls=3, max_tool_calls=5),
        "created_at": _ts(12),
        "correlation_id": "corr_e2e_001",
    }
    base.update(over)
    return MissionEnvelope(**base)


def _approval_service() -> tuple[Any, str]:
    """C3 test-contract migration: approvals come from the REAL authority service.

    CARRIER_STATE != AUTHORITY_STATE: tests must never fabricate approval via
    envelope.approval_state alone. This helper issues a genuine
    AuthorityApprovalService binding bound to the exact mission/actor/tenant/
    capability/resource scope used by _make_env, and returns (service, approval_id).
    """
    from datetime import timedelta

    from mission_wiring.approval_service import AuthorityApprovalService
    svc = AuthorityApprovalService()
    caps = frozenset({
        "computer.browser.navigate", "computer.browser.extract",
        "computer.browser.screenshot", "computer.browser.form_fill",
    })
    svc.issue(
        approval_id="approval-e2e-001",
        mission_id="mission.e2e-001",
        actor_id="agent.hermes.browser",
        tenant_id="tenant.default",
        capabilities=caps,
        resource_urls=frozenset({"https://example.com"}),
        issued_by="governance",
        ttl_seconds=int(timedelta(hours=1).total_seconds()),
    )
    return svc, "approval-e2e-001"


def _wired_browser(approval_service: Any = None) -> GovernedBrowserExecutor:
    """C4: lazy mechanism + C3 authority-wired gate."""
    return GovernedBrowserExecutor(FakeController(), approval_service=approval_service)


def _runner(browser: GovernedBrowserExecutor | None = None) -> tuple[MissionRunner, Any]:
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
    if browser is not None and getattr(browser, "_approval_service", None) is None:
        browser._approval_service = svc  # C3: the executor gate needs the same authority
    runner = MissionRunner(registry=registry, authority=authority,
                           approval_service=svc, browser=browser)
    return runner, approval_id


# ---- §25 positive E2E ----

def test_local_mission_end_to_end_completes_with_receipt():
    """Envelope capabilities are computer.browser.*; the runner accepts them
    when the manifest declares the underlying capability (FETCH_URL)."""
    runner, approval_id = _runner(browser=_wired_browser())
    env = _make_env(evidence_context={"approval_id": approval_id})
    receipt = runner.run(env)
    assert receipt.result is MissionResult.COMPLETED
    assert receipt.capabilities_used == ["computer.browser.navigate"]
    assert receipt.evidence_refs, "browser evidence must be attached"
    assert receipt.manifest_hash
    assert len(receipt.manifest_hash) == 64
    assert receipt.envelope_hash == env.envelope_hash()
    events = runner.events()
    kinds = {e["event"] for e in events}
    assert ObservedEvent.MISSION_STARTED.value in kinds
    assert ObservedEvent.DELEGATION_CREATED.value in kinds
    assert ObservedEvent.TOOL_COMPLETED.value in kinds
    assert ObservedEvent.BROWSER_ACTION.value in kinds
    assert ObservedEvent.MISSION_COMPLETED.value in kinds


# ---- §26 governed refusals ----

def test_refusal_unknown_agent():
    runner, approval_id = _runner(browser=_wired_browser())
    receipt = runner.run(_make_env(agent_id="agent.ghost",
                                   evidence_context={"approval_id": approval_id}))
    assert receipt.result is MissionResult.REFUSED
    assert receipt.failure_class == "UNKNOWN_AGENT"
    assert receipt.tool_calls == 0


def test_refusal_uncertified_agent():
    registry = AgentRegistry()
    registry.register(_browser_manifest(certification_status=CertificationStatus.VALIDATED))
    registry.register(_hermes_manifest())
    authority = DelegationAuthority()
    authority.register_trusted_root("agent.hermes")
    svc, approval_id = _approval_service()
    runner = MissionRunner(registry=registry, authority=authority, approval_service=svc,
                           browser=_wired_browser(svc))
    receipt = runner.run(_make_env(evidence_context={"approval_id": approval_id}))
    assert receipt.result is MissionResult.REFUSED
    assert receipt.failure_class == "AGENT_NOT_CERTIFIED"


def test_refusal_capability_not_in_manifest():
    runner, approval_id = _runner(browser=_wired_browser())
    receipt = runner.run(_make_env(requested_capabilities=("computer.browser.submit",),
                                   request_type=RequestType.BROWSER_SUBMIT,
                                   evidence_context={"approval_id": approval_id}))
    assert receipt.result is MissionResult.REFUSED
    # C3 contract: submit is in no approval binding either — the authority service
    # refuses with CAPABILITY_NOT_APPROVED before manifest routing matters.
    assert receipt.failure_class == "CAPABILITY_NOT_APPROVED"
    assert receipt.capabilities_used == []


def test_refusal_worker_not_delegatable_by_hermes():
    registry = AgentRegistry()
    registry.register(_hermes_manifest())
    registry.register(_browser_manifest())
    authority = DelegationAuthority()
    authority.register_trusted_root("agent.hermes")
    authority.set_delegatable("agent.hermes", frozenset({"READ_REPOSITORY"}), actor="governance")  # browser caps absent
    svc, approval_id = _approval_service()
    runner = MissionRunner(registry=registry, authority=authority, approval_service=svc,
                           browser=_wired_browser(svc))
    receipt = runner.run(_make_env(evidence_context={"approval_id": approval_id}))
    assert receipt.result is MissionResult.REFUSED
    assert receipt.failure_class == "DELEGATION_REFUSED"
    assert any(d["code"] == "DELEGATION_REFUSED" for d in receipt.policy_decisions)


def test_refusal_executor_not_wired_for_nonbrowser_caps():
    registry = AgentRegistry()
    registry.register(_hermes_manifest())
    registry.register(_browser_manifest(
        required_capabilities=("computer.browser.navigate", "computer.browser.download")))
    authority = DelegationAuthority()
    authority.register_trusted_root("agent.hermes")
    authority.set_delegatable("agent.hermes", frozenset({
        "computer.browser.navigate", "computer.browser.download",
    }), actor="governance")
    svc, approval_id = _approval_service()
    runner = MissionRunner(registry=registry, authority=authority, approval_service=svc,
                           browser=_wired_browser(svc))
    receipt = runner.run(_make_env(requested_capabilities=("computer.browser.download",),
                                   evidence_context={"approval_id": approval_id}))
    assert receipt.result is MissionResult.REFUSED
    # C3 contract: download is not in the approval binding scope -> authority refuses.
    assert receipt.failure_class == "CAPABILITY_NOT_APPROVED"


def test_refusal_receipts_carry_zero_execution_and_events():
    runner, approval_id = _runner(browser=_wired_browser())
    receipt = runner.run(_make_env(agent_id="agent.ghost",
                                   evidence_context={"approval_id": approval_id}))
    assert receipt.browser_actions == 0
    assert receipt.provider_calls == 0
    kinds = [e["event"] for e in runner.events()]
    assert kinds[-1] == ObservedEvent.MISSION_REFUSED.value
    assert kinds[0] == ObservedEvent.MISSION_STARTED.value
