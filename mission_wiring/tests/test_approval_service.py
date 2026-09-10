"""SP-CONVERGE-ZD-001 §6 — AuthorityApprovalService tests.

Proves the Principal's semantic invariant:
  CONSEQUENTIAL_REQUEST_WITHOUT_APPROVAL = REPRESENTABLE (PENDING envelope OK)
  CONSEQUENTIAL_EXECUTION_WITHOUT_VALID_APPROVAL = IMPOSSIBLE
And the independent validation chain: mission/actor/tenant/capability/resource
binding, expiry, unused state, exactly-once consumption.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mission_wiring.approval_service import (
    ApprovalInvalidError,
    AuthorityApprovalService,
)


def _now() -> datetime:
    return datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)


def _svc() -> AuthorityApprovalService:
    return AuthorityApprovalService(clock=_now)


def test_issuance_and_validation_happy_path():
    s = _svc()
    s.issue(approval_id="appr_001", mission_id="mission.x", actor_id="agent.browser.worker",
            tenant_id="tenant.default", capabilities=frozenset({"computer.browser.submit"}),
            resource_urls=frozenset({"https://example.com/form"}), issued_by="principal.howard")
    b = s.validate("appr_001", mission_id="mission.x", actor_id="agent.browser.worker",
                   tenant_id="tenant.default",
                   capabilities=frozenset({"computer.browser.submit"}),
                   resource_urls=frozenset({"https://example.com/form"}))
    assert b.approval_id == "appr_001"
    assert s.status("appr_001") == "ISSUED"


def test_unknown_approval_refused():
    s = _svc()
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_ghost", mission_id="m", actor_id="a", tenant_id="t",
                   capabilities=frozenset(), resource_urls=frozenset())
    assert ei.value.code == "UNKNOWN_APPROVAL"


def test_mission_mismatch_refused():
    s = _svc()
    s.issue(approval_id="appr_m", mission_id="mission.alpha", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_m", mission_id="mission.beta", actor_id="a", tenant_id="t",
                   capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "MISSION_MISMATCH"


def test_actor_mismatch_refused():
    s = _svc()
    s.issue(approval_id="appr_a", mission_id="m", actor_id="agent.one", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_a", mission_id="m", actor_id="agent.two", tenant_id="t",
                   capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "ACTOR_MISMATCH"


def test_tenant_mismatch_refused():
    s = _svc()
    s.issue(approval_id="appr_t", mission_id="m", actor_id="a", tenant_id="tenant.one",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_t", mission_id="m", actor_id="a", tenant_id="tenant.two",
                   capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "TENANT_MISMATCH"


def test_capability_not_approved_refused():
    s = _svc()
    s.issue(approval_id="appr_c", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"computer.browser.navigate"}), resource_urls=frozenset(),
            issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_c", mission_id="m", actor_id="a", tenant_id="t",
                   capabilities=frozenset({"computer.browser.navigate", "computer.browser.submit"}),
                   resource_urls=frozenset())
    assert ei.value.code == "CAPABILITY_NOT_APPROVED"


def test_resource_not_approved_refused():
    s = _svc()
    s.issue(approval_id="appr_r", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset({"https://ok.com"}),
            issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_r", mission_id="m", actor_id="a", tenant_id="t",
                   capabilities=frozenset({"c.x"}), resource_urls=frozenset({"https://evil.com"}))
    assert ei.value.code == "RESOURCE_NOT_APPROVED"


def test_expired_approval_refused():
    s = _svc()
    s.issue(approval_id="appr_e", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P",
            ttl_seconds=60)
    # advance the clock past expiry
    s.clock = lambda: _now() + timedelta(seconds=120)
    with pytest.raises(ApprovalInvalidError) as ei:
        s.validate("appr_e", mission_id="m", actor_id="a", tenant_id="t",
                   capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "APPROVAL_EXPIRED"


def test_invalid_ttl_refused():
    s = _svc()
    with pytest.raises(ApprovalInvalidError) as ei:
        s.issue(approval_id="appr_z", mission_id="m", actor_id="a", tenant_id="t",
                capabilities=frozenset(), resource_urls=frozenset(), issued_by="P", ttl_seconds=0)
    assert ei.value.code == "INVALID_EXPIRY"


def test_duplicate_approval_id_refused():
    s = _svc()
    s.issue(approval_id="appr_d", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset(), resource_urls=frozenset(), issued_by="P")
    with pytest.raises(ApprovalInvalidError) as ei:
        s.issue(approval_id="appr_d", mission_id="m", actor_id="a", tenant_id="t",
                capabilities=frozenset(), resource_urls=frozenset(), issued_by="P")
    assert ei.value.code == "DUPLICATE_APPROVAL_ID"


def test_consume_exactly_once():
    s = _svc()
    s.issue(approval_id="appr_x", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    s.consume("appr_x", mission_id="m", actor_id="a", tenant_id="t",
              capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert s.status("appr_x") == "CONSUMED"
    with pytest.raises(ApprovalInvalidError) as ei:
        s.consume("appr_x", mission_id="m", actor_id="a", tenant_id="t",
                  capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "APPROVAL_ALREADY_CONSUMED"


def test_consume_after_expiry_refused():
    s = _svc()
    s.issue(approval_id="appr_ce", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P",
            ttl_seconds=30)
    s.clock = lambda: _now() + timedelta(seconds=60)
    with pytest.raises(ApprovalInvalidError) as ei:
        s.consume("appr_ce", mission_id="m", actor_id="a", tenant_id="t",
                  capabilities=frozenset({"c.x"}), resource_urls=frozenset())
    assert ei.value.code == "APPROVAL_EXPIRED"


def test_concurrent_double_consume_exactly_one_wins():
    import threading
    s = _svc()
    s.issue(approval_id="appr_cc", mission_id="m", actor_id="a", tenant_id="t",
            capabilities=frozenset({"c.x"}), resource_urls=frozenset(), issued_by="P")
    results = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        try:
            s.consume("appr_cc", mission_id="m", actor_id="a", tenant_id="t",
                      capabilities=frozenset({"c.x"}), resource_urls=frozenset())
            results.append("OK")
        except ApprovalInvalidError as e:
            results.append(e.code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["APPROVAL_ALREADY_CONSUMED", "OK"]


def test_envelope_pending_posture_representable():
    """The semantic correction: a consequential mission may EXIST awaiting approval."""
    from mission_wiring.envelope import (
        ApprovalState,
        EnvelopeBudget,
        MemoryScope,
        MissionEnvelope,
        RequestOrigin,
        RequestType,
        ResourceScope,
    )
    env = MissionEnvelope(
        mission_id="mission.pending-001",
        principal_id="principal.howard",
        tenant_id="tenant.default",
        request_origin=RequestOrigin.MISSION_CONTROL,
        request_type=RequestType.BROWSER_SUBMIT,
        actor_id="agent.browser.worker",
        agent_id="agent.browser.worker",
        delegation_id="deleg_pend01",
        requested_capabilities=("computer.browser.submit",),
        resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=1),
        memory_scope=MemoryScope(tenants=("tenant.default",)),
        approval_state=ApprovalState.PENDING,
        budget=EnvelopeBudget(max_tool_calls=2),
        created_at=_now(),
        correlation_id="corr_pending_001",
    )
    assert env.is_consequential
    assert env.approval_state is ApprovalState.PENDING
    assert env.envelope_hash()  # representable and hashable


def test_envelope_never_self_declares_not_required():
    from mission_wiring.envelope import (
        ApprovalState,
        EnvelopeBudget,
        EnvelopeRefusalError,
        MemoryScope,
        MissionEnvelope,
        RequestOrigin,
        RequestType,
        ResourceScope,
    )
    with pytest.raises(EnvelopeRefusalError, match="APPROVAL_POSTURE_REQUIRED"):
        MissionEnvelope(
            mission_id="mission.bad-001", principal_id="principal.howard",
            tenant_id="tenant.default", request_origin=RequestOrigin.MISSION_CONTROL,
            request_type=RequestType.BROWSER_SUBMIT, actor_id="agent.browser.worker",
            agent_id="agent.browser.worker", delegation_id="deleg_bad01",
            requested_capabilities=("computer.browser.submit",),
            resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=1),
            memory_scope=MemoryScope(tenants=("tenant.default",)),
            approval_state=ApprovalState.NOT_REQUIRED,
            budget=EnvelopeBudget(max_tool_calls=2), created_at=_now(),
            correlation_id="corr_bad_001",
        )
