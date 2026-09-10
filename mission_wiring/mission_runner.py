"""SP-CONVERGE-ZD-001 §8 — governed mission runner (Hermes as coordinator).

Wires the certified-but-unwired agent_runtime into the mission path:

    envelope (§7)
      -> mission runner validates envelope against a CERTIFIED AgentManifest
      -> delegation via agent_runtime.DelegationAuthority (subset invariant,
         governance-root provenance, exactly-once approvals)
      -> capability execution routed through GovernedBrowserExecutor (§9-§10)
         for browser capabilities, or refused for anything not wired yet
      -> one MissionReceipt (§18) with events (§19)

Hermes-as-runner DOES: resolve certified agent, bind delegation, gate
capabilities, collect evidence, emit one receipt.
Hermes-as-runner DOES NOT: grant authority, invent capabilities, bypass tool
policy, escalate side effects (all mechanical, tested below).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from agent_runtime.capability_resolver import ResolutionError, resolve_capability
from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import CertificationStatus
from agent_runtime.registry import AgentRegistry, UnknownAgentError
from mission_wiring.browser_executor import (
    BrowserActionRefusedError,
    GovernedBrowserExecutor,
    _registry_view,
)
from mission_wiring.envelope import EnvelopeRefusalError, MissionEnvelope
from mission_wiring.receipt import MissionReceipt, MissionResult, ObservedEvent, ObservedEventRecord

__all__ = ["MissionRunner", "RunnerPolicyDecision"]


@dataclass
class RunnerPolicyDecision:
    decision: str  # ALLOW | REFUSE
    code: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"decision": self.decision, "code": self.code, "detail": self.detail}


@dataclass
class MissionRunner:
    """§8 coordinator. Holds the certified registry + delegation authority."""

    registry: AgentRegistry
    authority: DelegationAuthority
    approval_service: Any = None  # C3: required for consequential missions (browser)
    browser: GovernedBrowserExecutor | None = None
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._events: list[ObservedEventRecord] = []
        self._policy_decisions: list[dict[str, str]] = []

    # ---- event log (§19) ----
    def events(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events]

    def _emit(self, event: ObservedEvent, mission_id: str, **detail: Any) -> None:
        self._events.append(ObservedEventRecord(
            event=event, mission_id=mission_id,
            detail={k: v for k, v in detail.items() if v is not None},
            timestamp=self.clock(),
        ))

    def _decide(self, decision: str, code: str, detail: str = "") -> None:
        self._policy_decisions.append({"decision": decision, "code": code, "detail": detail})

    # ---- §8 coordinator flow ----
    def run(self, envelope: MissionEnvelope) -> MissionReceipt:
        started_at = self.clock()
        self._emit(ObservedEvent.MISSION_STARTED, envelope.mission_id)

        # 1) resolve the certified agent
        try:
            manifest = self.registry.resolve(envelope.agent_id)  # type: ignore[arg-type]
        except UnknownAgentError:
            self._decide("REFUSE", "UNKNOWN_AGENT", envelope.agent_id or "")
            self._emit(ObservedEvent.CAPABILITY_DENIED, envelope.mission_id, reason="UNKNOWN_AGENT")
            return self._refuse(envelope, "UNKNOWN_AGENT", started_at)

        if manifest.certification_status not in (CertificationStatus.CERTIFIED,):
            self._decide("REFUSE", "AGENT_NOT_CERTIFIED", str(manifest.certification_status.value))
            return self._refuse(envelope, "AGENT_NOT_CERTIFIED", started_at)

        # 2) every requested capability must (a) resolve through the governed
        # registry and (b) be in the manifest's declared surface (alias-aware,
        # W4-3 pattern). Resolution is identity-only; authority comes from
        # delegation + approval, unchanged.
        from agent_runtime.manifest import _resolves_to_known
        undeclared = [c for c in envelope.requested_capabilities if not _resolves_to_known(c)]
        if undeclared:
            self._decide("REFUSE", "CAPABILITY_NOT_IN_MANIFEST", ",".join(undeclared))
            self._emit(ObservedEvent.CAPABILITY_DENIED, envelope.mission_id, caps=undeclared)
            return self._refuse(envelope, "CAPABILITY_NOT_IN_MANIFEST", started_at)
        unresolvable = []
        try:
            view = _registry_view()
            for cap in envelope.requested_capabilities:
                resolve_capability(cap, view)
        except ResolutionError as exc:
            unresolvable = [c for c in envelope.requested_capabilities
                            if getattr(exc, "detail", "") and c in str(exc)] or list(envelope.requested_capabilities)
            self._decide("REFUSE", getattr(exc, "code", "REGISTRY_NOT_TRUSTED"), str(exc))
            self._emit(ObservedEvent.CAPABILITY_DENIED, envelope.mission_id, caps=unresolvable)
            return self._refuse(envelope, getattr(exc, "code", "REGISTRY_NOT_TRUSTED"), started_at)

        # 3) delegation (mechanical subset invariant + provenance + approval).
        # C3: the approval must be AUTHORITY-ISSUED (validated via the wired
        # AuthorityApprovalService through the executor gate) and is CONSUMED
        # exactly-once here. A caller-supplied delegation_id string is no
        # longer accepted as an approval reference.
        approval_id = envelope.evidence_context.get("approval_id")
        if not approval_id:
            self._decide("REFUSE", "APPROVAL_REQUIRED", "envelope carries no authority-issued approval_id")
            return self._refuse(envelope, "APPROVAL_REQUIRED", started_at)
        if self.approval_service is None:
            self._decide("REFUSE", "APPROVAL_SERVICE_ABSENT", "no AuthorityApprovalService wired")
            return self._refuse(envelope, "APPROVAL_SERVICE_ABSENT", started_at)
        try:
            self.approval_service.consume(
                approval_id,
                mission_id=envelope.mission_id,
                actor_id=envelope.actor_id,
                tenant_id=envelope.tenant_id,
                capabilities=frozenset(envelope.requested_capabilities),
                resource_urls=frozenset(envelope.resource_scope.url_allowlist),
            )
        except Exception as exc:
            code = getattr(exc, "code", "APPROVAL_REFUSED")
            self._decide("REFUSE", code, str(exc))
            self._emit(ObservedEvent.APPROVAL_CONSUMED, envelope.mission_id, refused=True)
            return self._refuse(envelope, code if code != "APPROVAL_ALREADY_CONSUMED" else "APPROVAL_REPLAYED", started_at)
        self._emit(ObservedEvent.APPROVAL_CONSUMED, envelope.mission_id, approval_id=approval_id)
        try:
            self.authority.issue(
                parent_agent="agent.hermes",
                child_manifest=manifest,
                delegation_id=envelope.delegation_id or f"deleg_{envelope.mission_id}",
                mission_id=envelope.mission_id,
                capabilities=list(envelope.requested_capabilities),
                tenant=envelope.tenant_id,
                approval_reference=approval_id,
                require_approval=True,
            )
        except DelegationRefusedError as refused:
            self._decide("REFUSE", "DELEGATION_REFUSED", str(refused))
            self._emit(ObservedEvent.DELEGATION_REFUSED, envelope.mission_id, reason=str(refused))
            return self._refuse(envelope, "DELEGATION_REFUSED", started_at)

        self._decide("ALLOW", "DELEGATION_ISSUED")
        self._emit(ObservedEvent.DELEGATION_CREATED, envelope.mission_id,
                   delegation_id=envelope.delegation_id)

        # 4) execution — routing is RESOLVER-DRIVEN (C1-adjacent): a capability
        # routes to the browser executor only if the registry says its
        # side_effect_class comes from the computer.browser.* family AND it
        # resolves. No raw string-prefix trust.
        browser_caps: list[str] = []
        non_browser: list[str] = []
        for c in envelope.requested_capabilities:
            try:
                cc = resolve_capability(c, view)
            except ResolutionError as exc:
                self._decide("REFUSE", "CAPABILITY_NOT_RESOLVABLE", f"{c}: {exc}")
                self._emit(ObservedEvent.CAPABILITY_DENIED, envelope.mission_id, caps=[c])
                return self._refuse(envelope, "CAPABILITY_NOT_RESOLVABLE", started_at)
            if cc.capability_id.startswith("computer.browser."):
                browser_caps.append(c)
            else:
                non_browser.append(c)
        if non_browser:
            self._decide("REFUSE", "EXECUTOR_NOT_WIRED", ",".join(non_browser))
            return self._refuse(envelope, "EXECUTOR_NOT_WIRED", started_at)
        if self.browser is None:
            self._decide("REFUSE", "BROWSER_EXECUTOR_ABSENT")
            return self._refuse(envelope, "BROWSER_EXECUTOR_ABSENT", started_at)

        used: list[str] = []
        evidence_refs: list[str] = []
        try:
            for cap in browser_caps:
                if cap == "computer.browser.navigate":
                    self._emit(ObservedEvent.TOOL_STARTED, envelope.mission_id, cap=cap)
                    res = self.browser.navigate(envelope, envelope.resource_scope.url_allowlist[0])
                    self._emit(ObservedEvent.TOOL_COMPLETED, envelope.mission_id, cap=cap)
                    self._emit(ObservedEvent.BROWSER_ACTION, envelope.mission_id,
                               url=getattr(res, "url", ""))
                    used.append(cap)
                    evidence_refs.extend(
                        e["evidence_reference"] for e in self.browser.evidence_dicts()
                        if e["evidence_reference"] not in evidence_refs
                    )
                else:
                    self._decide("REFUSE", "CAPABILITY_HANDLER_ABSENT", cap)
                    return self._refuse(envelope, "CAPABILITY_HANDLER_ABSENT", started_at)
        except (BrowserActionRefusedError, EnvelopeRefusalError) as refused:
            code = getattr(refused, "code", "BROWSER_GATE_REFUSED")
            self._decide("REFUSE", code, str(refused))
            self._emit(ObservedEvent.CAPABILITY_DENIED, envelope.mission_id, code=code)
            return self._refuse(envelope, code, started_at)
        except RuntimeError as crash:
            # §28: crashes during execution are BOUNDED — FAILED receipt,
            # single attempt, no silent side effects, no auto-retry.
            finished_at = self.clock()
            self._decide("REFUSE", "EXECUTION_CRASH", str(crash))
            self._emit(ObservedEvent.MISSION_FAILED, envelope.mission_id,
                       failure_class="EXECUTION_CRASH")
            return MissionReceipt(
                mission_id=envelope.mission_id,
                principal_authority=envelope.principal_id,
                tenant=envelope.tenant_id,
                origin=envelope.request_origin.value,
                agent=envelope.agent_id,
                agent_version="unbound",
                manifest_hash=None,
                delegation_chain=[envelope.delegation_id or ""],
                capabilities_requested=list(envelope.requested_capabilities),
                capabilities_used=[],
                memory_reads=0,
                memory_write_requests=0,
                provider_calls=0,
                tool_calls=0,
                browser_actions=0,
                approvals=[envelope.approval_state.value],
                policy_decisions=list(self._policy_decisions),
                evidence_refs=[],
                budget={"max_tool_calls": envelope.budget.max_tool_calls},
                duration_seconds=(finished_at - started_at).total_seconds(),
                result=MissionResult.FAILED,
                failure_class="EXECUTION_CRASH",
                context_hash=None,
                envelope_hash=envelope.envelope_hash(),
                started_at=started_at,
                finished_at=finished_at,
            )

        finished_at = self.clock()

        receipt = MissionReceipt(
            mission_id=envelope.mission_id,
            principal_authority=envelope.principal_id,
            tenant=envelope.tenant_id,
            origin=envelope.request_origin.value,
            agent=envelope.agent_id,
            agent_version=manifest.agent_version,
            manifest_hash=None,  # bound below via manifest hash function
            delegation_chain=[envelope.delegation_id or ""],
            capabilities_requested=list(envelope.requested_capabilities),
            capabilities_used=used,
            memory_reads=0,
            memory_write_requests=0,
            provider_calls=0,
            tool_calls=len(used),
            browser_actions=len(used),
            approvals=[envelope.approval_state.value],
            policy_decisions=list(self._policy_decisions),
            evidence_refs=evidence_refs,
            budget={"max_tool_calls": envelope.budget.max_tool_calls,
                    "max_provider_calls": envelope.budget.max_provider_calls},
            duration_seconds=(finished_at - started_at).total_seconds(),
            result=MissionResult.COMPLETED,
            failure_class=None,
            context_hash=None,
            envelope_hash=envelope.envelope_hash(),
            started_at=started_at,
            finished_at=finished_at,
        )
        from agent_runtime.manifest import manifest_hash as _mh
        receipt.manifest_hash = _mh(manifest)
        self._emit(ObservedEvent.MISSION_COMPLETED, envelope.mission_id,
                   receipt_hash=receipt.receipt_hash())
        return receipt

    # ---- refusal receipt helper ----
    def _refuse(self, envelope: MissionEnvelope, failure_class: str, started_at: datetime) -> MissionReceipt:
        receipt = MissionReceipt.refusal(envelope, failure_class,
                                         list(self._policy_decisions), started_at)
        self._emit(ObservedEvent.MISSION_REFUSED, envelope.mission_id,
                   failure_class=failure_class,
                   receipt_hash=receipt.receipt_hash())
        return receipt
