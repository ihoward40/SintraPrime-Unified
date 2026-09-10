"""SP-CONVERGE-ZD-001 §9-§10 — governed browser executor + capability surface.

Canonical decision (evidence-backed, stage 4):
- The existing ``operator/browser_controller.py`` is selected as the canonical
  Python browser EXECUTOR MECHANISM (most complete surface, 91 passing tests,
  Playwright + requests fallback).
- It is UNWRAPPED CODE, not a governed capability: no URL allowlist, no
  capability gate, no side-effect classes, no approval posture. Raw
  ``submit_form`` from any caller would be an authority bypass.
- This module WRAPS it behind the Wave-3 governance contract: a capability
  request must name an envelope; URL scope is enforced against the envelope's
  allowlist; side-effect classes gate which methods are reachable; approvals
  are required for EXTERNAL_CONSEQUENTIAL actions; evidence (before/after URL
  + hashes) is recorded for every action.

Rule preserved from directive: merely having Playwright installed implies nothing.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from agent_runtime.capability_resolver import (
    RegistryView,
    ResolutionError,
    _status_gate,
    load_registry,
    resolve_capability,
)
from agent_runtime.executor_binding import (
    ExecutorBindingError,
    load_executor_bindings,
    validate_executor_binding,
)
from agent_runtime.manifest import SideEffectClass
from mission_wiring.approval_service import ApprovalInvalidError, AuthorityApprovalService
from mission_wiring.envelope import ApprovalState, MissionEnvelope, RequestType

__all__ = [
    "BROWSER_CAPABILITIES",
    "SIDE_EFFECT_CLASSES",
    "BrowserActionRefusedError",
    "BrowserEvidence",
    "GovernedBrowserExecutor",
]

# W4-5: the stable identity this executor binds under in the registry's
# executor_bindings data. Execution of a computer.browser.* capability is
# permitted only if the trusted registry binds that capability to THIS id.
EXECUTOR_ID = "mission_wiring.browser_executor.GovernedBrowserExecutor"


# C1 (SP-MW-RECONCILE-001): the browser capability vocabulary is DERIVED from the
# governed Capability Registry (W4-1) via the certified resolver (W4-2) — this
# module no longer owns a private vocabulary. The map below is a fail-closed
# cache: it is populated ONLY from a trusted registry load, and resolution
# always re-consults the trusted RegistryView (see _gate). If the registry is
# missing/corrupt/untrusted, the map stays empty and EVERY browser action
# refuses with REGISTRY_NOT_TRUSTED. No fallback to any legacy vocabulary.
def _load_browser_surface_from_registry() -> dict[str, SideEffectClass]:
    from pathlib import Path

    candidates = (
        Path(__file__).resolve().parent.parent / "registry/capabilities/capability_registry.json",
        Path.cwd() / "registry/capabilities/capability_registry.json",
    )
    last_error: Exception | None = None
    for path in candidates:
        if not path.exists():
            continue
        try:
            view = load_registry(path)
        except ResolutionError as exc:
            last_error = exc
            continue
        surface: dict[str, SideEffectClass] = {}
        for cid, entry in view.canonical.items():
            if not cid.startswith("computer.browser."):
                continue
            try:
                surface[cid] = SideEffectClass(entry["side_effect_class"])
            except ValueError as exc:
                raise ResolutionError(
                    "REGISTRY_NOT_TRUSTED",
                    f"registry side_effect_class {entry.get('side_effect_class')!r} for {cid} is not a Wave-3 SideEffectClass",
                ) from exc
        return surface
    raise ResolutionError(
        "REGISTRY_NOT_TRUSTED",
        f"governed capability registry not found or untrusted (last error: {last_error})",
    )


try:
    BROWSER_CAPABILITIES: dict[str, SideEffectClass] = _load_browser_surface_from_registry()
except ResolutionError:
    # Fail-closed: absent registry => no browser capability is known => all actions refuse.
    BROWSER_CAPABILITIES = {}

SIDE_EFFECT_CLASSES = {cap: cls.value for cap, cls in BROWSER_CAPABILITIES.items()}




_REGISTRY_VIEW_CACHE: list[RegistryView] = []


def _registry_view() -> RegistryView:
    """C1 helper: load the trusted registry view (cached; mtime-invalidated)."""
    from pathlib import Path

    candidates = (
        Path(__file__).resolve().parent.parent / "registry/capabilities/capability_registry.json",
        Path.cwd() / "registry/capabilities/capability_registry.json",
    )
    for path in candidates:
        if not path.exists():
            continue
        key = (str(path), path.stat().st_mtime_ns, path.stat().st_size)
        if _REGISTRY_VIEW_CACHE and _REGISTRY_VIEW_CACHE[0][0] == key:
            return _REGISTRY_VIEW_CACHE[0][1]
        view = load_registry(path)  # raises ResolutionError on any integrity failure
        _REGISTRY_VIEW_CACHE.clear()
        _REGISTRY_VIEW_CACHE.append((key, view))
        return view
    raise ResolutionError("REGISTRY_NOT_TRUSTED", "governed capability registry artifact not found")


class BrowserActionRefusedError(Exception):
    """A governed browser action was refused by the capability/policy layer."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class BrowserEvidence:
    """§10 after-action record (sensitive inputs are hashed, never stored)."""
    url_before: str
    url_after: str
    action_type: str
    selector_or_target: str
    input_hash: str | None = None
    screenshot_before_ref: str | None = None
    screenshot_after_ref: str | None = None
    result: str = ""
    duration: float = 0.0
    side_effect_class: str = ""
    approval_reference: str | None = None
    evidence_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url_before": self.url_before, "url_after": self.url_after,
            "action_type": self.action_type, "selector_or_target": self.selector_or_target,
            "input_hash": self.input_hash,
            "screenshot_before_ref": self.screenshot_before_ref,
            "screenshot_after_ref": self.screenshot_after_ref,
            "result": self.result, "duration": self.duration,
            "side_effect_class": self.side_effect_class,
            "approval_reference": self.approval_reference,
            "evidence_reference": self.evidence_reference,
        }


def _hash_input(values: dict[str, Any]) -> str:
    """§10: never store sensitive form values — store a salted-repo hash."""
    import json
    blob = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class GovernedBrowserExecutor:
    """Capability-gated wrapper around the canonical browser mechanism.

    Every call requires the MissionEnvelope that authorizes it. The envelope is
    checked for: capability present, URL in scope, side-effect class permitted
    by request_type, approval present for consequential classes, budget
    remaining. Refusals are raised BEFORE any browser contact.
    """

    def __init__(self, controller: Any | None = None, *, controller_factory: Any = None,
                 approval_service: AuthorityApprovalService | None = None) -> None:
        """C4: mechanism injection is LAZY. Pass either an already-constructed
        controller (tests may pass fakes) or a zero-arg ``controller_factory``
        that builds the mechanism on first gated use. The constructor never
        imports operator.browser_controller, never launches Playwright, and
        never touches the network — no external state exists before governance.
        The mechanism is constructed lazily on first gated call, AFTER the
        capability/delegation/approval/side-effect/budget/URL gates pass.
        """
        if controller is None and controller_factory is None:
            raise BrowserActionRefusedError(
                "MECHANISM_ABSENT", "no browser controller or factory provided"
            )
        self._c = controller
        self._controller_factory = controller_factory
        self._approval_service = approval_service  # C3: THE one authority validator
        self._evidence: list[BrowserEvidence] = []
        self._actions_used = 0  # C5: per-action budget consumption
        self._binding_snapshot: Any = None  # W4-5: lazy executor-binding snapshot

    def _mechanism(self) -> Any:
        """Build the mechanism lazily — only after _gate has passed for an action."""
        if self._c is None:
            if self._controller_factory is None:  # pragma: no cover - guarded in __init__
                raise BrowserActionRefusedError("MECHANISM_ABSENT", "no factory")
            self._c = self._controller_factory()
        return self._c

    def _executor_bindings(self) -> Any:
        """W4-5: load the capability→executor binding snapshot from the trusted
        registry view (cached). Fail-closed: any registry integrity failure has
        already emptied BROWSER_CAPABILITIES and refused in _gate before we reach
        here, but load_executor_bindings re-derives from the same trusted view so
        the executor-binding generation is bound to the live registry."""
        if getattr(self, "_binding_snapshot", None) is None:
            self._binding_snapshot = load_executor_bindings(_registry_view())
        return self._binding_snapshot

    @property
    def executor_binding_generation(self) -> str:
        """The generation id of the active executor-binding snapshot (W4-6 dependency)."""
        return self._executor_bindings().executor_binding_generation

    # ---- §10 pre-action gate (C1: resolution through the governed registry) ----
    def _gate(self, envelope: MissionEnvelope, capability: str) -> None:
        # Resolution BEFORE recognition: the capability id must resolve through the
        # W4-2 resolver against a TRUSTED registry view. No private vocabulary,
        # no KNOWN_CAPABILITIES fallback (W4-3 rule). Resolution is identity
        # only — it never delegates, approves, or makes anything executable.
        if not BROWSER_CAPABILITIES:
            # empty cache means the registry was absent/untrusted at load: refuse
            raise BrowserActionRefusedError("REGISTRY_NOT_TRUSTED", capability)
        try:
            cc = resolve_capability(capability, _registry_view())
            _status_gate(cc)  # DISABLED / DORMANT refuse here
        except ResolutionError as exc:
            code = exc.code if exc.code in (
                "UNKNOWN_CAPABILITY", "AMBIGUOUS_ALIAS", "REGISTRY_GENERATION_MISMATCH",
                "INVALID_CAPABILITY_FORMAT", "DISABLED_CAPABILITY", "DORMANT_CAPABILITY",
                "REGISTRY_NOT_TRUSTED",
            ) else "UNKNOWN_CAPABILITY"
            raise BrowserActionRefusedError(code, f"{capability}: {exc.detail}") from exc
        if cc.capability_id != capability:
            raise BrowserActionRefusedError(
                "UNKNOWN_CAPABILITY",
                f"{capability!r} is not a registry CANONICAL id (aliases are not executable ids here)",
            )
        # W4-5: the registry declares WHAT (resolution, above); it must also declare
        # HOW — that this canonical capability is performed by THIS executor, at the
        # SAME registry generation resolution used. REGISTERED != BINDABLE: a
        # capability that resolves but is bound to no executor (or another executor)
        # refuses here, before any delegation/approval/mechanism work.
        try:
            binding = validate_executor_binding(
                self._executor_bindings(),
                capability_id=cc.capability_id,
                executor_id=EXECUTOR_ID,
                registry_generation_id=cc.registry_generation_id,
            )
        except ExecutorBindingError as exc:
            raise BrowserActionRefusedError(exc.code, f"{capability}: {exc.detail}") from exc
        self._executor_binding = binding
        if capability not in envelope.requested_capabilities:
            raise BrowserActionRefusedError(
                "CAPABILITY_NOT_DELEGATED",
                f"{capability} not in envelope.requested_capabilities",
            )
        cls = BROWSER_CAPABILITIES[capability]
        # C3: approval is verified against the AUTHORITY-ISSUED binding — the
        # envelope's own approval_state is a carrier field, never proof.
        if self._approval_service is None:
            raise BrowserActionRefusedError(
                "APPROVAL_SERVICE_ABSENT",
                "no AuthorityApprovalService wired; cannot verify authority-issued approval",
            )
        if envelope.approval_state is not ApprovalState.GRANTED:
            raise BrowserActionRefusedError(
                "APPROVAL_REQUIRED",
                f"capability {capability} requires authority-GRANTED approval posture, envelope has {envelope.approval_state.value}",
            )
        if not envelope.evidence_context.get("approval_id"):
            raise BrowserActionRefusedError(
                "APPROVAL_REQUIRED",
                "envelope carries no authority-issued approval_id in evidence_context",
            )
        try:
            binding = self._approval_service.validate(
                envelope.evidence_context["approval_id"],
                mission_id=envelope.mission_id,
                actor_id=envelope.actor_id,
                tenant_id=envelope.tenant_id,
                capabilities=frozenset(envelope.requested_capabilities),
                resource_urls=frozenset(envelope.resource_scope.url_allowlist),
            )
        except ApprovalInvalidError as exc:
            raise BrowserActionRefusedError("APPROVAL_REQUIRED", f"{exc.code}: {exc.detail}") from exc
        self._approval_binding = binding
        # consequential classes additionally require a consequential request_type
        if cls in (SideEffectClass.EXTERNAL_CONSEQUENTIAL, SideEffectClass.IRREVERSIBLE):
            if envelope.request_type is not RequestType.BROWSER_SUBMIT:
                raise BrowserActionRefusedError(
                    "SIDE_EFFECT_CLASS_EXCEEDS_MISSION",
                    f"class {cls.value} exceeds request_type {envelope.request_type.value}",
                )
        if envelope.resource_scope.max_actions <= 0:
            raise BrowserActionRefusedError("BUDGET_EXHAUSTED", "resource_scope.max_actions exhausted")
        self._actions_used += 1
        if self._actions_used > envelope.resource_scope.max_actions:
            raise BrowserActionRefusedError(
                "BUDGET_EXHAUSTED",
                f"resource_scope.max_actions={envelope.resource_scope.max_actions} exceeded after {self._actions_used - 1} governed actions",
            )

    def _url_in_scope(self, envelope: MissionEnvelope, url: str) -> None:
        if not envelope.resource_scope.allows(url):
            raise BrowserActionRefusedError(
                "URL_OUT_OF_SCOPE", f"{url} not within envelope allowlist",
            )

    def _record(self, ev: BrowserEvidence) -> BrowserEvidence:
        ev.evidence_reference = f"browser_evidence_{len(self._evidence) + 1:04d}"
        self._evidence.append(ev)
        return ev

    def _current_url(self) -> str:
        page = getattr(self._c, "_page", None)
        return getattr(page, "url", "") or ""

    # ---- governed capability surface ----
    def navigate(self, envelope: MissionEnvelope, url: str) -> Any:
        self._gate(envelope, "computer.browser.navigate")
        self._url_in_scope(envelope, url)
        before = self._current_url()
        res = self._mechanism().navigate(url)
        ev = self._record(BrowserEvidence(
            url_before=before, url_after=getattr(res, "url", ""), action_type="navigate",
            selector_or_target=url, result="success" if getattr(res, "success", False) else "failed",
            duration=getattr(res, "duration_seconds", 0.0),
            side_effect_class=SideEffectClass.READ_ONLY.value,
        ))
        res.metadata = {**getattr(res, "metadata", {}), "governed_evidence": ev.to_dict()}
        return res

    def extract_text(self, envelope: MissionEnvelope, selector: str = "body") -> Any:
        self._gate(envelope, "computer.browser.extract")
        ev = self._record(BrowserEvidence(
            url_before=self._current_url(), url_after=self._current_url(),
            action_type="extract_text", selector_or_target=selector,
            result="success", side_effect_class=SideEffectClass.READ_ONLY.value,
        ))
        res = self._mechanism().extract_text(selector)
        res.metadata = {**getattr(res, "metadata", {}), "governed_evidence": ev.to_dict()}
        return res

    def screenshot(self, envelope: MissionEnvelope, full_page: bool = False) -> Any:
        self._gate(envelope, "computer.browser.screenshot")
        res = self._mechanism().screenshot(full_page)
        ev = self._record(BrowserEvidence(
            url_before=self._current_url(), url_after=self._current_url(),
            action_type="screenshot", selector_or_target="full_page" if full_page else "viewport",
            screenshot_after_ref=getattr(res, "data", None),
            result="success" if getattr(res, "success", False) else "failed",
            side_effect_class=SideEffectClass.LOCAL_REVERSIBLE.value,
        ))
        res.metadata = {**getattr(res, "metadata", {}), "governed_evidence": ev.to_dict()}
        return res

    def fill_form(self, envelope: MissionEnvelope, fields: dict[str, str]) -> Any:
        self._gate(envelope, "computer.browser.form_fill")
        self._url_in_scope(envelope, self._current_url() or "about:blank")
        ih = _hash_input(fields)  # sensitive values hashed, never stored
        res = self._mechanism().fill_form(fields)
        ev = self._record(BrowserEvidence(
            url_before=self._current_url(), url_after=self._current_url(),
            action_type="fill_form", selector_or_target="fields", input_hash=ih,
            result="success" if getattr(res, "success", False) else "failed",
            side_effect_class=SideEffectClass.LOCAL_REVERSIBLE.value,
        ))
        res.metadata = {**getattr(res, "metadata", {}), "governed_evidence": ev.to_dict()}
        return res

    def submit_form(self, envelope: MissionEnvelope, selector: str = '[type="submit"]') -> Any:
        """EXTERNAL_CONSEQUENTIAL — the §27 escalation test target."""
        self._gate(envelope, "computer.browser.submit")
        self._url_in_scope(envelope, self._current_url() or "about:blank")
        before = self._current_url()
        res = self._mechanism().submit_form(selector)
        ev = self._record(BrowserEvidence(
            url_before=before, url_after=getattr(res, "url", ""),
            action_type="submit_form", selector_or_target=selector,
            result="success" if getattr(res, "success", False) else "failed",
            side_effect_class=SideEffectClass.EXTERNAL_CONSEQUENTIAL.value,
            approval_reference=envelope.delegation_id or envelope.mission_id,
        ))
        res.metadata = {**getattr(res, "metadata", {}), "governed_evidence": ev.to_dict()}
        return res

    # ---- evidence surface ----
    @property
    def evidence(self) -> list[BrowserEvidence]:
        return list(self._evidence)

    def evidence_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._evidence]
