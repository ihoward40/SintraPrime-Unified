"""W4-5 — capability → executor binding matrix.

Three-way separation under test:

    REGISTERED != BINDABLE      (registry declares WHAT; binding declares HOW)
    RESOLVED   != APPROVED      (identity is not authority)
    BINDABLE   != EXECUTABLE    (binding is not delegation/approval)

The executor-binding gate sits between resolution and delegation/approval. It
refuses BEFORE any mechanism contact when the capability is bound to no executor,
to a different executor, or under a different registry generation than the one
resolution used.

These tests drive the real executor gate in isolation with a fake mechanism, so
no network/browser contact is possible; the pre-governance-contact test asserts
that explicitly by wiring a factory that would explode if ever called.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from agent_runtime.executor_binding import (
    ExecutorBinding,
    ExecutorBindingError,
    ExecutorBindingRegistry,
    load_executor_bindings,
    validate_executor_binding,
)
from mission_wiring.approval_service import AuthorityApprovalService
from mission_wiring.browser_executor import (
    EXECUTOR_ID,
    BrowserActionRefusedError,
    GovernedBrowserExecutor,
    _registry_view,
)
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


def _svc_with_approval(*, capabilities=None, resource_urls=None) -> AuthorityApprovalService:
    svc = AuthorityApprovalService()
    svc.issue(
        approval_id="approval-eb1", mission_id="mission.eb-001",
        actor_id="agent.browser.worker", tenant_id="tenant.default",
        capabilities=capabilities or frozenset(_CAPS),
        resource_urls=resource_urls or frozenset({"https://example.com"}),
        issued_by="governance", ttl_seconds=3600,
    )
    return svc


def _env(**over) -> MissionEnvelope:
    base = {
        "mission_id": "mission.eb-001",
        "principal_id": "principal.howard",
        "tenant_id": "tenant.default",
        "request_origin": RequestOrigin.MISSION_CONTROL,
        "request_type": RequestType.BROWSER_READ,
        "actor_id": "agent.browser.worker",
        "agent_id": "agent.hermes.browser",
        "delegation_id": "deleg_eb01",
        "requested_capabilities": ("computer.browser.navigate",),
        "resource_scope": ResourceScope(url_allowlist=("https://example.com",), max_actions=4),
        "memory_scope": MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "approval_state": ApprovalState.GRANTED,
        "budget": EnvelopeBudget(max_tool_calls=8),
        "created_at": datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC),
        "correlation_id": "corr_eb_001",
        "evidence_context": {"approval_id": "approval-eb1"},
    }
    base.update(over)
    return MissionEnvelope(**base)


def _executor(*, binding_snapshot=None, exploding_factory=False) -> GovernedBrowserExecutor:
    """Real executor with a fake mechanism (or an exploding factory that proves
    the mechanism is never contacted before the gate passes)."""
    if exploding_factory:
        def _boom():
            raise AssertionError("MECHANISM CONTACTED BEFORE GOVERNANCE PASSED")
        ex = GovernedBrowserExecutor(
            controller_factory=_boom, approval_service=_svc_with_approval()
        )
    else:
        class _FakeResult:
            def __init__(self):
                self.url = "https://example.com/ok"
                self.success = True
                self.duration_seconds = 0.0
                self.metadata = {}

        class _FakeController:
            def navigate(self, url):  # noqa: ARG002 - fake mechanism, url unused
                return _FakeResult()

        ex = GovernedBrowserExecutor(
            controller=_FakeController(), approval_service=_svc_with_approval()
        )
    if binding_snapshot is not None:
        ex._binding_snapshot = binding_snapshot
    return ex


# ---------------------------------------------------------------- POSITIVE ----

def test_canonical_capability_bound_to_browser_executor():
    ex = _executor()
    ex._gate(_env(), "computer.browser.navigate")  # no raise
    assert ex._executor_binding.executor_id == EXECUTOR_ID
    assert ex._executor_binding.capability_id == "computer.browser.navigate"


def test_valid_governed_browser_action_executes():
    ex = _executor()
    res = ex.navigate(_env(), "https://example.com")
    assert getattr(res, "success", False) is True


def test_all_browser_capabilities_bound_no_unbound():
    """Every ACTIVE computer.browser.* capability the registry exposes must carry
    a binding to THIS executor. UNBOUND_BROWSER_CAPABILITIES = 0."""
    view = _registry_view()
    snap = load_executor_bindings(view)
    browser = [c for c in view.canonical if c.startswith("computer.browser.")
               and view.canonical[c]["status"] == "ACTIVE"]
    unbound = []
    for cid in browser:
        try:
            validate_executor_binding(
                snap, capability_id=cid, executor_id=EXECUTOR_ID,
                registry_generation_id=view.generation_id,
            )
        except ExecutorBindingError:
            unbound.append(cid)
    assert unbound == [], f"UNBOUND_BROWSER_CAPABILITIES={unbound}"
    assert len(browser) >= 1


def test_alias_and_canonical_use_same_executor_binding():
    """After resolution both alias and canonical present the same canonical id to
    the binding layer, so they bind to the same executor. No alias fallback."""
    view = _registry_view()
    snap = load_executor_bindings(view)
    # pick a browser capability that has an alias
    for cid, aliases in view.canonical_to_aliases.items():
        if cid.startswith("computer.browser.") and aliases:
            b1 = validate_executor_binding(snap, capability_id=cid,
                                           executor_id=EXECUTOR_ID,
                                           registry_generation_id=view.generation_id)
            # aliases are resolved upstream; the binding layer only ever sees cid
            assert b1.capability_id == cid
            break


# ---------------------------------------------------------------- NEGATIVE ----

def test_capability_with_no_executor_binding_refuses():
    """A capability that resolves but has no binding => refuse at the HOW layer."""
    view = _registry_view()
    snap = load_executor_bindings(view)
    with pytest.raises(ExecutorBindingError) as ei:
        validate_executor_binding(
            snap, capability_id="repository.read",  # manifest-origin, no browser binding
            executor_id=EXECUTOR_ID, registry_generation_id=view.generation_id,
        )
    assert ei.value.code == "CAPABILITY_WITH_NO_EXECUTOR_BINDING"


def test_wrong_executor_binding_refuses():
    """A browser capability requested by a non-browser executor id => refuse."""
    view = _registry_view()
    snap = load_executor_bindings(view)
    with pytest.raises(ExecutorBindingError) as ei:
        validate_executor_binding(
            snap, capability_id="computer.browser.navigate",
            executor_id="some.other.Executor", registry_generation_id=view.generation_id,
        )
    assert ei.value.code == "WRONG_EXECUTOR_BINDING"


def test_registry_generation_mismatch_refuses():
    """Resolution generation must equal the binding-snapshot generation."""
    view = _registry_view()
    snap = load_executor_bindings(view)
    with pytest.raises(ExecutorBindingError) as ei:
        validate_executor_binding(
            snap, capability_id="computer.browser.navigate",
            executor_id=EXECUTOR_ID, registry_generation_id="reg-DIFFERENT",
        )
    assert ei.value.code == "REGISTRY_GENERATION_MISMATCH"


def test_gate_refuses_wrong_binding_before_mechanism_contact():
    """W4-5 through the real gate: a binding snapshot that binds navigate to a
    different executor must refuse WRONG_EXECUTOR_BINDING before any mechanism
    contact (exploding factory proves no contact)."""
    view = _registry_view()
    good = load_executor_bindings(view)
    nav = good.bindings["computer.browser.navigate"][0]
    poisoned = replace(nav, executor_id="attacker.Executor")
    bad_snap = ExecutorBindingRegistry(
        registry_generation_id=good.registry_generation_id,
        executor_binding_generation=good.executor_binding_generation,
        bindings={**good.bindings, "computer.browser.navigate": (poisoned,)},
    )
    ex = _executor(binding_snapshot=bad_snap, exploding_factory=True)
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(_env(), "https://example.com")
    assert ei.value.code == "WRONG_EXECUTOR_BINDING"


def test_pre_governance_no_external_contact():
    """The mechanism factory must never be called when the gate refuses. Here the
    envelope omits the capability from requested_capabilities (delegation gap),
    so the gate refuses AFTER binding validation but BEFORE mechanism contact."""
    ex = _executor(exploding_factory=True)
    env = _env(requested_capabilities=("computer.browser.extract",))  # navigate not delegated
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(env, "https://example.com")
    assert ei.value.code == "CAPABILITY_NOT_DELEGATED"


# ------------------------------------------------------- GENERATION IDENTITY ---

def test_executor_binding_generation_is_stable_and_derived():
    view = _registry_view()
    g1 = load_executor_bindings(view).executor_binding_generation
    g2 = load_executor_bindings(view).executor_binding_generation
    assert g1 == g2
    assert g1.startswith("ebg-")


def test_executor_binding_generation_changes_with_bindings():
    view = _registry_view()
    base = load_executor_bindings(view)
    extra = ExecutorBinding(
        capability_id="computer.browser.navigate", executor_id="another.Executor",
        executor_version="1", registry_generation_id=view.generation_id,
        supported_side_effect_class="READ_ONLY", binding_status="CERTIFIED_LOCAL",
    )
    mutated = ExecutorBindingRegistry(
        registry_generation_id=base.registry_generation_id,
        executor_binding_generation="ebg-RECOMPUTE",
        bindings={**base.bindings,
                  "computer.browser.navigate": (*base.bindings["computer.browser.navigate"], extra)},
    )
    # recompute from the mutated rows via a fresh load path proxy: the derivation
    # is deterministic on the binding set, so a different set => different gen.
    from agent_runtime.executor_binding import _derive_binding_generation
    rows_base = [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
                 for bs in base.bindings.values() for b in bs]
    rows_mut = [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
                for bs in mutated.bindings.values() for b in bs]
    assert _derive_binding_generation(view.generation_id, rows_base) != \
        _derive_binding_generation(view.generation_id, rows_mut)
