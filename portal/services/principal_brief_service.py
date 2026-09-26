"""Principal Brief service (SP-GOD0-MISSION-CONTROL-001 Phase 1).

Bridges the governed runtime's sp-principal-brief-v1 contract (omnibrain.
principal_brief) into the Portal's permission-gated read model.

Design rules:
- READ-ONLY: no runtime state is mutated by aggregation.
- Recommendations are proposals with provenance; they can never become
  approvals through this service. Approvals flow exclusively through the
  existing governed approval service (mission_control_approval_service),
  which enforces exactly-once consumption and strict approval provenance.
- Tenant-scoped: an actor only ever sees briefs for their own tenant.
- Fail-closed: missing/failed subsystem inputs surface as explicit
  "unavailable" fields, never as fabricated zeros or plausible data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone

# The brief schema version this service guarantees.
BRIEF_SCHEMA_VERSION = "sp-principal-brief-v2"


@dataclass(frozen=True)
class BriefSection:
    """One rendered section of the Principal Brief."""

    key: str                 # stable section key (see SECTIONS)
    title: str
    status: str              # "ok" | "unavailable"
    rows: list[dict] = field(default_factory=list)
    detail: str = ""


SECTIONS = (
    "system_status",
    "active_missions",
    "blocked_missions",
    "active_agents",
    "blocked_agents",
    "pending_approvals",
    "authority_expirations",
    "external_effect_attempts",
    "recent_evidence",
    "memory_changes",
    "security_events",
    "runtime_failures",
    "recommended_principal_decisions",
)


def empty_brief_payload(*, reason: str) -> dict:
    """A well-formed brief with every section marked unavailable.

    Used when a subsystem input is missing or fails: the shape of the
    contract is preserved so the UI never has to special-case absence,
    and no fabricated data is ever produced.
    """
    now = datetime.now(UTC).isoformat()
    return {
        "schema_version": BRIEF_SCHEMA_VERSION,
        "generated_at": now,
        "available": False,
        "unavailable_reason": reason,
        "active_missions": [],
        "agents": [],
        "blocked_agents": [],
        "pending_approvals": [],
        "external_effect_attempts": [],
        "security_events": [],
        "recent_receipt_ids": [],
        "authority_expirations": [],
        "memory_change_summary": {},
        "recommended_principal_decisions": [],
    }


def normalize_brief(raw: dict) -> dict:
    """Validate/coerce an omnibrain PrincipalBrief dict to the served shape.

    Raises ValueError when the schema_version does not match: the contract
    is controlling, and silent drift would put lies in front of the
    Principal.
    """
    if raw.get("schema_version") != BRIEF_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported brief schema_version: {raw.get('schema_version')!r}"
        )
    allowed = {
        "schema_version", "generated_at", "available", "unavailable_reason",
        "active_missions", "agents", "blocked_agents", "pending_approvals",
        "external_effect_attempts", "security_events", "recent_receipt_ids",
        "authority_expirations", "memory_change_summary",
        "recommended_principal_decisions", "execution_state",
    }
    return {k: raw.get(k) for k in allowed}


def recommendation_is_proposal_only(recommendation: dict) -> bool:
    """Guard: a recommendation object can never be executed as an approval.

    A recommendation is a proposal iff it carries no consumable approval
    token — i.e. it must NOT contain an approval_reference / approval_id
    field that the runtime would accept under strict approval provenance.
    """
    forbidden = {"approval_reference", "approval_token", "approval_id"}
    return not (set(recommendation) & forbidden)
