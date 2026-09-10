"""SP-CONVERGE-ZD-001 §18 + §19 — unified MissionReceipt + observability events.

One final receipt per mission (completed/refused/failed), hash-bound to the
envelope that authorized it. No private chain-of-thought is ever stored.
§19 event taxonomy rides on the same module so observability reports FROM
canonical runtime events, not from side channels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from agent_runtime.canonical import canonical_hash
from agent_runtime.receipts import canonicalize_capability_for_hash
from mission_wiring.envelope import MissionEnvelope

__all__ = ["OBSERVABILITY_EVENTS", "MissionReceipt", "MissionResult", "ObservedEvent"]


class MissionResult(StrEnum):
    COMPLETED = "COMPLETED"
    REFUSED = "REFUSED"
    FAILED = "FAILED"


class ObservedEvent(StrEnum):
    """§19 canonical observability taxonomy (exact directive event names)."""
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETED = "mission_completed"
    MISSION_REFUSED = "mission_refused"
    MISSION_FAILED = "mission_failed"
    DELEGATION_CREATED = "delegation_created"
    DELEGATION_REFUSED = "delegation_refused"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_CONSUMED = "approval_consumed"
    CAPABILITY_DENIED = "capability_denied"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    PROVIDER_STARTED = "provider_started"
    PROVIDER_COMPLETED = "provider_completed"
    PROVIDER_FAILED = "provider_failed"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE_REQUESTED = "memory_write_requested"
    BROWSER_ACTION = "browser_action"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXHAUSTED = "budget_exhausted"
    AGENT_QUARANTINED = "agent_quarantined"


OBSERVABILITY_EVENTS = frozenset(e.value for e in ObservedEvent)


@dataclass
class ObservedEventRecord:
    event: ObservedEvent
    mission_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"event": self.event.value, "mission_id": self.mission_id,
                "timestamp": self.timestamp.isoformat(), "detail": self.detail}


@dataclass
class MissionReceipt:
    """§18 minimum fields — exactly the directive list, no private CoT."""
    mission_id: str
    principal_authority: str
    tenant: str
    origin: str
    agent: str | None
    agent_version: str
    manifest_hash: str | None
    delegation_chain: list[str]
    capabilities_requested: list[str]
    capabilities_used: list[str]
    memory_reads: int
    memory_write_requests: int
    provider_calls: int
    tool_calls: int
    browser_actions: int
    approvals: list[str]
    policy_decisions: list[dict[str, Any]]
    evidence_refs: list[str]
    budget: dict[str, Any]
    duration_seconds: float
    result: MissionResult
    failure_class: str | None
    context_hash: str | None
    envelope_hash: str
    started_at: datetime
    finished_at: datetime

    def __post_init__(self) -> None:
        if self.result is MissionResult.REFUSED and not self.failure_class:
            raise ValueError("REFUSED receipts must carry a failure_class")
        if self.result is MissionResult.FAILED and not self.failure_class:
            raise ValueError("FAILED receipts must carry a failure_class")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at before started_at")

    # ---- §18 hash binding ----
    def hash_payload(self, registry_view: Any = None) -> dict[str, Any]:
        """C2: capabilities_requested/used are canonicalized (W4-4) before hash.
        Raw alias strings never enter a security-sensitive hash."""
        def _canon(caps: list[str]) -> list[str]:
            if not caps:
                return []
            if registry_view is None:
                from mission_wiring.browser_executor import _registry_view
                rv = _registry_view()
            else:
                rv = registry_view
            out = []
            for cap in caps:
                try:
                    cid, _gen, _rh = canonicalize_capability_for_hash(cap, rv)
                except ValueError as exc:
                    raise ValueError(f"capability {cap!r} not resolvable for receipt hash: {exc}") from exc
                out.append(cid)
            return sorted(out)
        self._canonical_requested = _canon(self.capabilities_requested)
        self._canonical_used = _canon(self.capabilities_used)
        return {
            "mission_id": self.mission_id,
            "principal_authority": self.principal_authority,
            "tenant": self.tenant,
            "origin": self.origin,
            "agent": self.agent,
            "agent_version": self.agent_version,
            "manifest_hash": self.manifest_hash,
            "delegation_chain": list(self.delegation_chain),
            "capabilities_requested": list(self._canonical_requested),
            "capabilities_used": list(self._canonical_used),
            "memory_reads": self.memory_reads,
            "memory_write_requests": self.memory_write_requests,
            "provider_calls": self.provider_calls,
            "tool_calls": self.tool_calls,
            "browser_actions": self.browser_actions,
            "approvals": list(self.approvals),
            "policy_decisions": self.policy_decisions,
            "evidence_refs": list(self.evidence_refs),
            "budget": self.budget,
            "duration_seconds": self.duration_seconds,
            "result": self.result.value,
            "failure_class": self.failure_class,
            "context_hash": self.context_hash,
            "envelope_hash": self.envelope_hash,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }

    def receipt_hash(self) -> str:
        return canonical_hash(self.hash_payload())

    def to_dict(self) -> dict[str, Any]:
        d = self.hash_payload()
        d["receipt_hash"] = self.receipt_hash()
        return d

    # ---- §19 helpers ----
    @staticmethod
    def start_event(mission_id: str) -> ObservedEventRecord:
        return ObservedEventRecord(event=ObservedEvent.MISSION_STARTED, mission_id=mission_id)

    def terminal_event(self) -> ObservedEventRecord:
        event = {
            MissionResult.COMPLETED: ObservedEvent.MISSION_COMPLETED,
            MissionResult.REFUSED: ObservedEvent.MISSION_REFUSED,
            MissionResult.FAILED: ObservedEvent.MISSION_FAILED,
        }[self.result]
        return ObservedEventRecord(
            event=event, mission_id=self.mission_id,
            detail={"result": self.result.value, "failure_class": self.failure_class,
                    "receipt_hash": self.receipt_hash()},
        )

    @classmethod
    def refusal(cls, envelope: MissionEnvelope, failure_class: str,
                policy_decisions: list[dict[str, Any]], started_at: datetime) -> MissionReceipt:
        """Receipt for a mission refused before any execution."""
        return cls(
            mission_id=envelope.mission_id,
            principal_authority=envelope.principal_id,
            tenant=envelope.tenant_id,
            origin=envelope.request_origin.value,
            agent=envelope.agent_id,
            agent_version="unbound",
            manifest_hash=None,
            delegation_chain=[envelope.delegation_id] if envelope.delegation_id else [],
            capabilities_requested=list(envelope.requested_capabilities),
            capabilities_used=[],
            memory_reads=0,
            memory_write_requests=0,
            provider_calls=0,
            tool_calls=0,
            browser_actions=0,
            approvals=[envelope.approval_state.value],
            policy_decisions=policy_decisions,
            evidence_refs=[],
            budget={"max_provider_calls": envelope.budget.max_provider_calls,
                    "max_tool_calls": envelope.budget.max_tool_calls,
                    "max_loop_observations": envelope.budget.max_loop_observations,
                    "deadline_seconds": envelope.budget.deadline_seconds},
            duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
            result=MissionResult.REFUSED,
            failure_class=failure_class,
            context_hash=None,
            envelope_hash=envelope.envelope_hash(),
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )
