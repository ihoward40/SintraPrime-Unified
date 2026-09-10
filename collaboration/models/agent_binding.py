"""AgentChannelBinding — scoped agent participation in a channel."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import AgentPresenceState, AgentResponseMode


@dataclass
class AgentChannelBinding:
    id: str
    tenant_id: str
    channel_id: str
    agent_id: str
    status: str = "active"
    response_mode: AgentResponseMode = AgentResponseMode.MENTION_ONLY
    allowed_event_types: list[str] = field(default_factory=list)
    actor_allowlist: list[str] = field(default_factory=list)
    max_parallelism: int = 3
    queue_depth: int = 10
    rate_limit_per_hour: int = 60
    execution_profile: str = "standard"
    memory_mode: str = "session"
    provider_profile: str = "balanced"
    model_profile: str = "balanced"
    budget: dict = field(
        default_factory=lambda: {
            "max_tokens_per_activation": 12000,
            "max_tokens_per_hour": 100000,
            "max_provider_cost_per_day": 25.0,
            "max_activations_per_hour": 40,
        }
    )
    created_at: str = ""
    stopped: bool = False
    shadow_mode: bool = False
    quiet_mode: str = "normal"
    current_presence: AgentPresenceState = AgentPresenceState.OFFLINE
