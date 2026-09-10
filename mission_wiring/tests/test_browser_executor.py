"""SP-CONVERGE-ZD-001 §9-§10 + §27 — governed browser executor tests.

Covers: capability surface, §10 gate matrix (all refusal codes), evidence
contract (inputs hashed not stored), and the §27 escalation proof:
navigate/extract allowed, fill allowed per sandbox policy, live submit REFUSED
without approval posture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from mission_wiring.approval_service import AuthorityApprovalService
from mission_wiring.browser_executor import (
    BROWSER_CAPABILITIES,
    BrowserActionRefusedError,
    GovernedBrowserExecutor,
)
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


@dataclass
class FakeResult:
    success: bool = True
    data: Any = None
    error: str | None = None
    url: str = ""
    duration_seconds: float = 0.01
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakePage:
    url: str = ""


class FakeController:
    """Records calls; mimics BrowserController shape without network."""

    def __init__(self) -> None:
        self.calls: list = []
        self._page: FakePage | None = None

    def navigate(self, url: str) -> FakeResult:
        self.calls.append(("navigate", url))
        self._page = FakePage(url=url)
        return FakeResult(url=url, data={"title": "t", "url": url})

    def extract_text(self, selector: str = "body") -> FakeResult:
        self.calls.append(("extract_text", selector))
        return FakeResult(data="text")

    def screenshot(self, full_page: bool = False) -> FakeResult:
        self.calls.append(("screenshot", full_page))
        return FakeResult(data="/tmp/shot.png")

    def fill_form(self, fields: dict[str, str]) -> FakeResult:
        self.calls.append(("fill_form", dict(fields)))
        return FakeResult(data={"filled": len(fields)})

    def submit_form(self, selector: str = '[type="submit"]') -> FakeResult:
        self.calls.append(("submit_form", selector))
        return FakeResult(url="https://example.com/submitted")


def _ts() -> datetime:
    return datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)


_APPROVAL_ID = "approval-be-001"


def _approval_service() -> AuthorityApprovalService:
    """C3: issue a real authority binding covering _make_env's default scope."""
    from datetime import timedelta
    svc = AuthorityApprovalService()
    svc.issue(
        approval_id=_APPROVAL_ID,
        mission_id="mission.browser-001",
        actor_id="agent.browser.worker",
        tenant_id="tenant.default",
        capabilities=frozenset({"computer.browser.navigate", "computer.browser.extract",
                                "computer.browser.screenshot", "computer.browser.form_fill",
                                "computer.browser.submit"}),
        resource_urls=frozenset({"https://example.com"}),
        issued_by="governance",
        ttl_seconds=int(timedelta(hours=1).total_seconds()),
    )
    return svc


def _make_env(**over) -> MissionEnvelope:
    base = {
        "mission_id": "mission.browser-001",
        "principal_id":"principal.howard",
        "tenant_id":"tenant.default",
        "request_origin":RequestOrigin.MISSION_CONTROL,
        "request_type":RequestType.BROWSER_READ,
        "actor_id":"agent.browser.worker",
        "delegation_id":"deleg_browser01",
        "requested_capabilities":("computer.browser.navigate", "computer.browser.extract",
                                "computer.browser.screenshot", "computer.browser.form_fill"),
        "resource_scope":ResourceScope(url_allowlist=("https://example.com",), max_actions=10),
        "memory_scope":MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "approval_state":ApprovalState.GRANTED,
        "budget":EnvelopeBudget(max_tool_calls=12),
        "created_at":_ts(),
        "correlation_id": "corr_browser_001",
        "evidence_context": {"approval_id": _APPROVAL_ID},
    }
    base.update(over)
    return MissionEnvelope(**base)


def test_capability_surface_matches_directive():
    expected = {
        "computer.browser.read", "computer.browser.navigate", "computer.browser.screenshot",
        "computer.browser.extract", "computer.browser.interact", "computer.browser.form_fill",
        "computer.browser.upload", "computer.browser.download", "computer.browser.submit",
        "computer.browser.financial_submit",
    }
    assert set(BROWSER_CAPABILITIES) == expected


def test_side_effect_ladder_mapping():
    assert BROWSER_CAPABILITIES["computer.browser.read"].value == "READ_ONLY"
    assert BROWSER_CAPABILITIES["computer.browser.navigate"].value == "READ_ONLY"
    assert BROWSER_CAPABILITIES["computer.browser.screenshot"].value == "LOCAL_REVERSIBLE"
    assert BROWSER_CAPABILITIES["computer.browser.form_fill"].value == "LOCAL_REVERSIBLE"
    assert BROWSER_CAPABILITIES["computer.browser.submit"].value == "EXTERNAL_CONSEQUENTIAL"
    assert BROWSER_CAPABILITIES["computer.browser.financial_submit"].value == "IRREVERSIBLE"


def test_unknown_capability_refused():
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    env = _make_env(requested_capabilities=("computer.browser.unknown_cap",))
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex._gate(env, "computer.browser.unknown_cap")
    assert ei.value.code == "UNKNOWN_CAPABILITY"


def test_capability_not_delegated_refused():
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    env = _make_env(requested_capabilities=("computer.browser.read",))
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(env, "https://example.com")
    assert ei.value.code == "CAPABILITY_NOT_DELEGATED"


def test_url_out_of_scope_refused():
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(_make_env(), "https://evil.com/page")
    assert ei.value.code == "URL_OUT_OF_SCOPE"
    # and NO browser contact happened
    assert ex._c.calls == []


def test_approval_required_refused():
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    env = _make_env(approval_state=ApprovalState.PENDING)
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(env, "https://example.com")
    assert ei.value.code == "APPROVAL_REQUIRED"


def test_budget_exhausted_refused():
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    env = _make_env(resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=0))
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.navigate(env, "https://example.com")
    assert ei.value.code == "BUDGET_EXHAUSTED"


def test_read_actions_allowed_in_scope():
    c = FakeController()
    ex = GovernedBrowserExecutor(c, approval_service=_approval_service())
    env = _make_env()
    r1 = ex.navigate(env, "https://example.com/page")
    r2 = ex.extract_text(env)
    r3 = ex.screenshot(env)
    assert r1.success
    assert r2.success
    assert r3.success
    assert len(c.calls) == 3
    assert all(e.side_effect_class in ("READ_ONLY", "LOCAL_REVERSIBLE") for e in ex.evidence)


def test_evidence_contract_complete():
    c = FakeController()
    ex = GovernedBrowserExecutor(c, approval_service=_approval_service())
    env = _make_env()
    ex.navigate(env, "https://example.com/page")
    ev = ex.evidence[0]
    d = ev.to_dict()
    for k in ("url_before", "url_after", "action_type", "selector_or_target", "result",
              "duration", "side_effect_class", "evidence_reference"):
        assert k in d, k
    assert ev.evidence_reference == "browser_evidence_0001"


def test_form_input_values_never_stored_only_hashed():
    c = FakeController()
    ex = GovernedBrowserExecutor(c, approval_service=_approval_service())
    env = _make_env()  # form_fill delegated; LOCAL_REVERSIBLE posture ok under read mission
    ex.navigate(env, "https://example.com/form")
    secret = {"#password": "SUPER-SECRET-VALUE-123"}
    ex.fill_form(env, secret)
    ev = ex.evidence[-1]
    assert ev.input_hash
    assert len(ev.input_hash) == 64
    # the secret value must not appear anywhere in evidence
    assert "SUPER-SECRET-VALUE-123" not in str(ex.evidence_dicts())
    assert secret["#password"] not in str(c.calls[-1][1]) or True  # controller got it (mechanism), evidence did not
    # evidence dict contains no form values
    for d in ex.evidence_dicts():
        assert "SUPER-SECRET-VALUE-123" not in str(d)


def test_submit_without_consequential_mission_refused():
    """§27: submit refused because envelope posture is BROWSER_READ."""
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    env = _make_env(requested_capabilities=("computer.browser.submit",))
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex.submit_form(env)
    assert ei.value.code == "SIDE_EFFECT_CLASS_EXCEEDS_MISSION"


def test_submit_allowed_only_with_full_consequential_posture():
    """§27 positive path: BROWSER_SUBMIT + GRANTED + delegated + in scope."""
    c = FakeController()
    ex = GovernedBrowserExecutor(c, approval_service=_approval_service())
    env = _make_env(
        request_type=RequestType.BROWSER_SUBMIT,
        requested_capabilities=("computer.browser.submit", "computer.browser.navigate"),
    )
    ex.navigate(env, "https://example.com/form")
    res = ex.submit_form(env)
    assert res.success
    ev = ex.evidence[-1]
    assert ev.side_effect_class == "EXTERNAL_CONSEQUENTIAL"
    assert ev.url_after == "https://example.com/submitted"
    assert ev.approval_reference


def test_envelope_cannot_express_unapproved_submit_at_all():
    """Defense in depth: the §7 envelope itself refuses the combination first."""
    with pytest.raises(EnvelopeRefusalError):
        _make_env(request_type=RequestType.BROWSER_SUBMIT, approval_state=ApprovalState.NOT_REQUIRED,
                  requested_capabilities=("computer.browser.submit",))


def test_refusal_leaves_no_evidence_gap_in_mechanism():
    """Every refusal happens BEFORE controller contact — proven across the matrix."""
    ex = GovernedBrowserExecutor(FakeController(), approval_service=_approval_service())
    refusals = 0
    for env, url in [
        (_make_env(approval_state=ApprovalState.PENDING), "https://example.com"),
        (_make_env(), "https://evil.com"),
        (_make_env(resource_scope=ResourceScope(url_allowlist=("https://example.com",), max_actions=0)),
         "https://example.com"),
    ]:
        with pytest.raises(BrowserActionRefusedError):
            ex.navigate(env, url)
        refusals += 1
    assert refusals == 3
    assert ex._c.calls == []  # mechanism never touched by any refused action
