"""PresenceService — observable agent status (§XXIII-XXIV)."""

from __future__ import annotations

from collaboration.models import AgentChannelBinding
from collaboration.models.enums import AgentPresenceState


class PresenceService:
    """Operational status only. No private chain-of-thought surfacing (§XLVII)."""

    def __init__(self):
        self._presence: dict[str, AgentPresenceState] = {}
        self._activity: dict[str, str] = {}  # agent_id → current activity description

    def set(self, agent_id: str, state: AgentPresenceState, activity: str = "") -> None:
        self._presence[agent_id] = state
        self._activity[agent_id] = activity

    def get_state(self, agent_id: str) -> AgentPresenceState:
        return self._presence.get(agent_id, AgentPresenceState.OFFLINE)

    def get_activity(self, agent_id: str) -> str:
        return self._activity.get(agent_id, "")

    def channel_status(self, bindings: list[AgentChannelBinding]) -> list[dict]:
        return [
            {
                "agent_id": b.agent_id,
                "presence": self.get_state(b.agent_id).value,
                "activity": self.get_activity(b.agent_id),
            }
            for b in bindings
        ]
