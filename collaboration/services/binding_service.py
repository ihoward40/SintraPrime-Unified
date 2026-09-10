"""BindingService — agent-to-channel binding management (§VI)."""

from __future__ import annotations

from collaboration.models import AgentChannelBinding
from collaboration.services.store import CollaborationStore


class BindingService:
    def __init__(self, store: CollaborationStore):
        self.store = store

    def bind(
        self,
        *,
        tenant_id: str,
        channel_id: str,
        agent_id: str,
        allowed_event_types: list[str] | None = None,
        max_parallelism: int = 3,
        memory_mode: str = "session",
        provider_profile: str = "balanced",
        model_profile: str = "balanced",
        actor_allowlist: list[str] | None = None,
        shadow_mode: bool = False,
    ) -> AgentChannelBinding:
        b = AgentChannelBinding(
            id=f"bind_{agent_id}_{channel_id}",
            tenant_id=tenant_id,
            channel_id=channel_id,
            agent_id=agent_id,
            allowed_event_types=allowed_event_types or ["channel_message_created"],
            max_parallelism=max_parallelism,
            memory_mode=memory_mode,
            provider_profile=provider_profile,
            model_profile=model_profile,
            actor_allowlist=actor_allowlist or [],
            shadow_mode=shadow_mode,
        )
        self.store.save("bindings", b.id, b)
        return b

    def get(self, binding_id: str) -> AgentChannelBinding | None:
        return self.store.load("bindings", binding_id, AgentChannelBinding)

    def list_for_channel(self, channel_id: str) -> list[AgentChannelBinding]:
        return [
            b
            for b in self.store.load_many("bindings", AgentChannelBinding)
            if b.channel_id == channel_id
        ]

    def list_for_agent(self, agent_id: str) -> list[AgentChannelBinding]:
        return [
            b
            for b in self.store.load_many("bindings", AgentChannelBinding)
            if b.agent_id == agent_id
        ]

    def stop(self, binding_id: str) -> AgentChannelBinding | None:
        b = self.get(binding_id)
        if b is None:
            return None
        b.stopped = True
        self.store.save("bindings", b.id, b)
        return b

    def resume(self, binding_id: str) -> AgentChannelBinding | None:
        b = self.get(binding_id)
        if b is None:
            return None
        b.stopped = False
        self.store.save("bindings", b.id, b)
        return b
