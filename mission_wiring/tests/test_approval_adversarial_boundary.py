"""SP-MW-RECONCILE-001 — adversarial approval boundary matrix (C3 contract).

CARRIER_STATE != AUTHORITY_STATE. Every approval presented to the governed
browser executor gate must be validated against the AuthorityApprovalService.

Refusals required:
  ENVELOPE_APPROVAL_STATE_ONLY / FORGED_APPROVAL_ID / WRONG_MISSION /
  WRONG_ACTOR / WRONG_TENANT / WRONG_CAPABILITY / WRONG_RESOURCE /
  EXPIRED / REPLAYED
Acceptance required:
  AUTHORITY_SERVICE_ISSUED_APPROVAL / VALID_APPROVAL_CONSUMED_ONCE
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mission_wiring.approval_service import AuthorityApprovalService
from mission_wiring.browser_executor import BrowserActionRefusedError, GovernedBrowserExecutor
from mission_wiring.envelope import (
    ApprovalState,
    EnvelopeBudget,
    MemoryScope,
    MissionEnvelope,
    RequestOrigin,
    RequestType,
    ResourceScope,
)

_CAPS = frozenset({
    "computer.browser.navigate", "computer.browser.extract",
    "computer.browser.screenshot", "computer.browser.form_fill",
    "computer.browser.submit",
})


def _svc() -> AuthorityApprovalService:
    return AuthorityApprovalService()


def _issue(svc: AuthorityApprovalService, *, approval_id: str = "approval-a1",
           mission_id: str = "mission.appr-001", actor_id: str = "agent.browser.worker",
           tenant_id: str = "tenant.default", capabilities: frozenset[str] | None = None,
           resource_urls: frozenset[str] | None = None, ttl_seconds: int = 3600,
           clock_offset_seconds: int = 0) -> None:
    fixed = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
    svc.clock = lambda: fixed + timedelta(seconds=clock_offset_seconds)
    svc.issue(
        approval_id=approval_id, mission_id=mission_id, actor_id=actor_id,
        tenant_id=tenant_id,
        capabilities=capabilities or frozenset(_CAPS),
        resource_urls=resource_urls or frozenset({"https://example.com"}),
        issued_by="governance", ttl_seconds=ttl_seconds,
    )


def _env(**over) -> MissionEnvelope:
    base = {
        "mission_id": "mission.appr-001",
        "principal_id": "principal.howard",
        "tenant_id": "tenant.default",
        "request_origin": RequestOrigin.MISSION_CONTROL,
        "request_type": RequestType.BROWSER_READ,
        "actor_id": "agent.browser.worker",
        "agent_id": "agent.hermes.browser",
        "delegation_id": "deleg_appr01",
        "requested_capabilities": ("computer.browser.navigate",),
        "resource_scope": ResourceScope(url_allowlist=("https://example.com",), max_actions=4),
        "memory_scope": MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "approval_state": ApprovalState.GRANTED,
        "budget": EnvelopeBudget(max_tool_calls=8),
        "created_at": datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC),
        "correlation_id": "corr_appr_001",
    }
    base.update(over)
    return MissionEnvelope(**base)


def _gate(env: MissionEnvelope, svc: AuthorityApprovalService) -> None:
    """Drive the real executor gate in isolation (no mechanism contact)."""
    ex = GovernedBrowserExecutor.__new__(GovernedBrowserExecutor)
    ex._approval_service = svc
    ex._actions_used = 0
    ex._gate(env, "computer.browser.navigate")


def test_envelope_approval_state_only_refused():
    """Carrier state GRANTED without any approval_id => refuse."""
    svc = _svc()
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_forged_approval_id_refused():
    svc = _svc()
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-forged-xyz"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_wrong_mission_approval_refused():
    svc = _svc()
    _issue(svc, mission_id="mission.other")
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_wrong_actor_approval_refused():
    svc = _svc()
    _issue(svc, actor_id="agent.impostor")
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_wrong_tenant_approval_refused():
    svc = _svc()
    _issue(svc, tenant_id="tenant.other")
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_wrong_capability_approval_refused():
    svc = _svc()
    _issue(svc, capabilities=frozenset({"computer.browser.download"}))
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_wrong_resource_approval_refused():
    svc = _svc()
    _issue(svc, resource_urls=frozenset({"https://evil.example"}))
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_expired_approval_refused():
    svc = _svc()
    _issue(svc, ttl_seconds=60)
    # advance the service clock past expiry AFTER issuance
    svc.clock = lambda: datetime(2026, 9, 10, 12, 2, 0, tzinfo=UTC)
    with pytest.raises(BrowserActionRefusedError) as ei:
        _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_replayed_approval_refused():
    """The runner consumes exactly-once; a second run of the same approval refuses."""
    from mission_wiring.tests.test_mission_runner import _make_env, _runner, _wired_browser
    runner, approval_id = _runner(browser=_wired_browser())
    env = _make_env(mission_id="mission.e2e-001",
                    evidence_context={"approval_id": approval_id})
    r1 = runner.run(env)
    assert r1.result.value == "COMPLETED"
    r2 = runner.run(env)  # same approval_id a second time
    assert r2.result.value == "REFUSED"
    assert r2.failure_class in ("APPROVAL_REPLAYED", "APPROVAL_ALREADY_CONSUMED")


def test_authority_service_issued_approval_accepted():
    svc = _svc()
    _issue(svc)
    _gate(_env(evidence_context={"approval_id": "approval-a1"}), svc)  # no raise


def test_valid_approval_consumed_once():
    from mission_wiring.tests.test_mission_runner import _make_env, _runner, _wired_browser
    runner, approval_id = _runner(browser=_wired_browser())
    env = _make_env(mission_id="mission.e2e-001",
                    evidence_context={"approval_id": approval_id})
    assert runner.run(env).result.value == "COMPLETED"
    # exactly-once: service reports CONSUMED
    assert runner.approval_service.status(approval_id) == "CONSUMED"
