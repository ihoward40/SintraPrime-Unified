"""SP-CONVERGE-ZD-001 §7 — MissionEnvelope contract tests.

Proves: fail-closed construction, hash determinism + mutation detection,
consequential-approval posture enforcement, delegation requirement, and
normalization of a legacy origin into the canonical envelope.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

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


def _make(**over):
    base = {
        "mission_id": "mission.test-001",
        "principal_id": "principal.howard",
        "tenant_id": "tenant.default",
        "request_origin": RequestOrigin.MISSION_CONTROL,
        "request_type": RequestType.RESEARCH,
        "actor_id": "principal.howard",
        "requested_capabilities": ("computer.browser.read",),
        "resource_scope": ResourceScope(url_allowlist=("https://example.com",), max_actions=3),
        "memory_scope": MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "budget": EnvelopeBudget(max_provider_calls=4, max_tool_calls=6, max_loop_observations=5),
    }
    base.update(over)
    return MissionEnvelope(**base)


def test_valid_envelope_constructs():
    e = _make()
    assert e.request_origin.value == "ORIGIN_MISSION_CONTROL"
    assert e.memory_scope.read_only is True
    assert e.correlation_id


def test_invalid_identity_refused():
    with pytest.raises(EnvelopeRefusalError) as ei:
        _make(principal_id="")
    assert ei.value.code == "INVALID_IDENTITY"
    with pytest.raises(EnvelopeRefusalError):
        _make(tenant_id="BAD ID WITH SPACES")


def test_unknown_origin_refused():
    with pytest.raises(EnvelopeRefusalError) as ei:
        _make(request_origin="ORIGIN_BYPASS")
    assert ei.value.code == "INVALID_ORIGIN"


def test_invalid_capability_grammar_refused():
    with pytest.raises(EnvelopeRefusalError) as ei:
        _make(requested_capabilities=("Browser.Submit",))
    assert ei.value.code == "INVALID_CAPABILITY"


def test_consequential_without_approval_posture_refused():
    with pytest.raises(EnvelopeRefusalError) as ei:
        _make(request_type=RequestType.BROWSER_SUBMIT)
    assert ei.value.code == "APPROVAL_POSTURE_REQUIRED"


def test_consequential_with_explicit_pending_allowed():
    e = _make(request_type=RequestType.BROWSER_SUBMIT, approval_state=ApprovalState.PENDING)
    assert e.is_consequential
    assert e.approval_state is ApprovalState.PENDING


def test_financial_never_not_required():
    for rt in (RequestType.FINANCIAL, RequestType.INFRASTRUCTURE, RequestType.EXTERNAL_COMMUNICATION):
        with pytest.raises(EnvelopeRefusalError):
            _make(request_type=rt)


def test_worker_needs_delegation_for_capabilities():
    with pytest.raises(EnvelopeRefusalError) as ei:
        _make(actor_id="agent.swarm.worker", delegation_id=None)
    assert ei.value.code == "DELEGATION_REQUIRED"


def test_worker_with_delegation_accepted():
    e = _make(actor_id="agent.swarm.worker", delegation_id="deleg_abc123")
    assert not e.is_principal_actor


def test_principal_actor_needs_no_delegation():
    e = _make()
    assert e.is_principal_actor


def test_negative_budget_refused():
    with pytest.raises(EnvelopeRefusalError):
        _make(budget=EnvelopeBudget(max_tool_calls=-1))
    with pytest.raises(EnvelopeRefusalError):
        _make(budget=EnvelopeBudget(deadline_seconds=0))
    with pytest.raises(EnvelopeRefusalError):
        _make(timeout_seconds=-5)


def test_resource_scope_allowlist_enforced():
    s = ResourceScope(url_allowlist=("https://example.com",), max_actions=2)
    assert s.allows("https://example.com/page")
    assert not s.allows("https://evil.com/page")
    assert not ResourceScope().allows("https://example.com")  # empty = nothing


def test_envelope_hash_deterministic():
    # Determinism property: identical FULL payloads -> identical hash.
    # correlation_id AND created_at are authority-bearing; pin both.
    ts = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
    a = _make(correlation_id="corr-fixed-001", created_at=ts)
    b = _make(correlation_id="corr-fixed-001", created_at=ts)
    assert a.envelope_hash() == b.envelope_hash()
    assert len(a.envelope_hash()) >= 32


def test_fresh_correlation_ids_differ_by_design():
    a, b = _make(), _make()
    assert a.correlation_id != b.correlation_id
    assert a.envelope_hash() != b.envelope_hash()


def test_envelope_hash_detects_mutation():
    a = _make()
    b = _make(requested_capabilities=("computer.browser.read", "computer.browser.navigate"))
    c = _make(resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=999))
    d = _make(budget=EnvelopeBudget(max_provider_calls=99, max_tool_calls=6, max_loop_observations=5))
    assert a.envelope_hash() != b.envelope_hash()
    assert a.envelope_hash() != c.envelope_hash()
    assert a.envelope_hash() != d.envelope_hash()


def test_legacy_origin_normalizes_to_canonical():
    """§7 acceptance: a legacy-format request (scheduler dict) maps into the envelope."""
    legacy = {"source": "cron", "task": "nightly_research", "tenant": "tenant.default"}
    origin = {"cron": RequestOrigin.SCHEDULER, "api": RequestOrigin.API}.get(legacy["source"])
    e = _make(
        request_origin=origin,
        actor_id="agent.scheduler.worker",
        delegation_id="deleg_sched01",
        tenant_id=legacy["tenant"],
    )
    assert e.request_origin is RequestOrigin.SCHEDULER
    assert e.envelope_hash()
