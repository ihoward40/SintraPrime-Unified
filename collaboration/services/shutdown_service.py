"""ShutdownService — immediate agent stop control (§XV)."""

from __future__ import annotations

from collaboration.services.activation_service import ActivationService
from collaboration.services.binding_service import BindingService


class ShutdownService:
    """STOP_AGENT control: stop accepting events, cancel work, persist state."""

    def __init__(self, activations: ActivationService, bindings: BindingService):
        self.activations = activations
        self.bindings = bindings

    def stop_agent(
        self,
        agent_id: str,
        channel_id: str,
    ) -> dict:
        """Stop a specific agent binding. Returns action summary."""
        bound = self.bindings.list_for_agent(agent_id)
        for b in bound:
            if b.channel_id == channel_id and not b.stopped:
                self.bindings.stop(b.id)
        return {
            "agent_id": agent_id,
            "channel_id": channel_id,
            "bindings_stopped": len(bound),
            "status": "stopped",
        }

    def stop_all_in_channel(self, channel_id: str) -> list[dict]:
        bindings = self.bindings.list_for_channel(channel_id)
        results = []
        for b in bindings:
            if not b.stopped:
                self.bindings.stop(b.id)
                results.append({"agent_id": b.agent_id, "status": "stopped"})
        return results
