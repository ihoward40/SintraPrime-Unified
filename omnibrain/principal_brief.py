"""Principal Brief / Mission Control data contract (SP-OMNIBRAIN-RUNTIME-001 Phase 12).

A versioned, serializable snapshot of governed-runtime state for the future
GOD-0 Mission Control surface. Backend contract only — no UI is built here.

Design rules:
- Read-only aggregation over existing surfaces (receipts, envelopes, ledger,
  tool-gateway denials). It never mutates runtime state.
- recommended_principal_decisions are PROPOSALS with their provenance; the
  brief cannot execute any of them.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

SCHEMA_VERSION = "sp-principal-brief-v1"


@dataclass(frozen=True)
class BriefAgent:
    agent_id: str
    mission_id: str
    status: str                 # e.g. COMPLETE | BLOCKED | DENIED | FAILED | ACTIVE
    model: str
    context_package_hash: str | None = None
    last_receipt_id: str | None = None


@dataclass(frozen=True)
class BriefApproval:
    approval_id: str
    agent_id: str
    mission_id: str
    requested_action: str
    requested_at: datetime | None = None
    effect_class: str = ""


@dataclass(frozen=True)
class BriefSecurityEvent:
    event_id: str
    event_class: str            # e.g. DENIED_TOOL | DENIED_MEMORY | TAMPER | EXPIRED_AUTHORITY
    agent_id: str | None
    detail: str
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class PrincipalBrief:
    schema_version: str
    generated_at: datetime
    active_missions: list[str]
    agents: list[BriefAgent]
    blocked_agents: list[str]
    pending_approvals: list[BriefApproval]
    external_effect_attempts: list[BriefSecurityEvent]
    security_events: list[BriefSecurityEvent]
    recent_receipt_ids: list[str]
    authority_expirations: list[dict]     # {authority_id, expires_at}
    memory_change_summary: Mapping[str, int]
    recommended_principal_decisions: list[dict]  # proposals + provenance; never executable

    def to_dict(self) -> dict:
        from dataclasses import asdict
        d = asdict(self)
        d["generated_at"] = self.generated_at.isoformat()
        return d


def build_brief(
    *,
    agents: Sequence[BriefAgent],
    pending_approvals: Sequence[BriefApproval],
    security_events: Sequence[BriefSecurityEvent],
    recent_receipt_ids: Sequence[str],
    authority_expirations: Sequence[Mapping[str, object]],
    memory_change_summary: Mapping[str, int],
    recommended_principal_decisions: Sequence[Mapping[str, object]],
    now: datetime | None = None,
) -> PrincipalBrief:
    """Aggregate pre-collected facts into the versioned brief.

    Deliberately dumb aggregation: classification of events happens at the
    sources (receipts, gateway, memory guard). This function only shapes the
    contract so Mission Control has one stable schema to consume.
    """
    now = now or datetime.now()
    active = [a for a in agents if a.status == "ACTIVE"]
    return PrincipalBrief(
        schema_version=SCHEMA_VERSION,
        generated_at=now,
        active_missions=sorted({a.mission_id for a in agents}),
        agents=list(agents),
        blocked_agents=sorted(a.agent_id for a in agents if a.status == "BLOCKED"),
        pending_approvals=list(pending_approvals),
        external_effect_attempts=[
            e for e in security_events if e.event_class.startswith("EXTERNAL_EFFECT")
        ],
        security_events=list(security_events),
        recent_receipt_ids=list(recent_receipt_ids),
        authority_expirations=[dict(x) for x in authority_expirations],
        memory_change_summary=dict(memory_change_summary),
        recommended_principal_decisions=[dict(x) for x in recommended_principal_decisions],
    )
