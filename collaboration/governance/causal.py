"""Causal records — 'Why did this happen?' (§89-90, §117)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class CausalRecord:
    """Operational causality, never chain-of-thought (§89)."""

    action_id: str
    triggering_event_id: str = ""
    matched_policy: str = ""
    agent_selected: str = ""
    selection_reason: str = ""
    workflow_version: str = ""
    capability_lease_id: str = ""
    approval: str = ""
    provider: str = ""
    effect_receipt_id: str = ""
    reason_code: str = ""
    tenant_id: str = ""
    channel_id: str = ""
    created_at: str = field(default_factory=_now)


class CausalStore:
    """Why-Did-This-Happen API backing store (§89)."""

    def __init__(self, store: CollaborationStore):
        self.store = store

    def record(self, rec: CausalRecord) -> CausalRecord:
        self.store.save("causal", rec.action_id, rec)
        return rec

    def explain(self, action_id: str) -> CausalRecord | None:
        """Given an action_id, return the causal explanation."""
        return self.store.load("causal", action_id, CausalRecord)

    def explain_dict(self, action_id: str) -> dict:
        rec = self.explain(action_id)
        if rec is None:
            return {"action_id": action_id, "found": False}
        return {
            "action_id": rec.action_id,
            "triggering_event_id": rec.triggering_event_id,
            "matched_policy": rec.matched_policy,
            "agent_selected": rec.agent_selected,
            "selection_reason": rec.selection_reason,
            "workflow_version": rec.workflow_version,
            "capability_lease_id": rec.capability_lease_id,
            "approval": rec.approval,
            "provider": rec.provider,
            "effect_receipt_id": rec.effect_receipt_id,
            "reason_code": rec.reason_code,
            "found": True,
        }
