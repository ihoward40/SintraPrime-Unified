"""Agent quarantine (§47, §140, §141)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


class QuarantineReason(str):
    SECURITY_VIOLATION = "security_violation"
    CAPABILITY_VIOLATION = "capability_violation"
    REPEATED_MALFORMED_OUTPUTS = "repeated_malformed_outputs"
    REPEATED_HALLUCINATED_CAPABILITIES = "repeated_hallucinated_capabilities"
    LOOP_BEHAVIOR = "loop_behavior"
    COST_ANOMALY = "cost_anomaly"
    DATA_BOUNDARY_VIOLATION = "data_boundary_violation"
    POISON_EVENT = "poison_event"


@dataclass
class AgentQuarantineRecord:
    agent_id: str
    reason: str
    trigger: str = ""
    quarantined_at: str = field(default_factory=_now)
    quarantined_by: str = ""
    diagnostic_only: bool = True
    active: bool = True


class AgentQuarantineService:
    """QUARANTINED agents: no new tasks, no new leases, inspectable (§47)."""

    def __init__(self, store: CollaborationStore):
        self.store = store

    def quarantine(
        self,
        agent_id: str,
        reason: str,
        *,
        trigger: str = "",
        quarantined_by: str = "",
    ) -> AgentQuarantineRecord:
        rec = AgentQuarantineRecord(
            agent_id=agent_id,
            reason=reason,
            trigger=trigger,
            quarantined_by=quarantined_by,
        )
        self.store.save("agent_quarantine", agent_id, rec)
        return rec

    def is_quarantined(self, agent_id: str) -> bool:
        rec = self.store.load("agent_quarantine", agent_id, AgentQuarantineRecord)
        return rec is not None and rec.active

    def release(self, agent_id: str, *, released_by: str = "") -> AgentQuarantineRecord | None:
        del released_by
        rec = self.store.load("agent_quarantine", agent_id, AgentQuarantineRecord)
        if rec is None:
            return None
        rec.active = False
        self.store.save("agent_quarantine", agent_id, rec)
        return rec

    def get(self, agent_id: str) -> AgentQuarantineRecord | None:
        return self.store.load("agent_quarantine", agent_id, AgentQuarantineRecord)

    def list_active(self) -> list[AgentQuarantineRecord]:
        return [
            r for r in self.store.load_many("agent_quarantine", AgentQuarantineRecord) if r.active
        ]
