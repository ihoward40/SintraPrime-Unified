"""AgentIdentity — durable, host-independent agent identity (§XX)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentIdentity:
    """Identity belongs to SintraPrime; execution location is ephemeral."""

    agent_id: str
    name: str
    role: str = ""
    allowed_domains: list[str] = field(default_factory=list)
    provider_profile: str = "balanced"
    model_profile: str = "balanced"
    authority_class: str = "A0"
    status: str = "registered"
    registered_at: str = ""
