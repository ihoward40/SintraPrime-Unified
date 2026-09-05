"""ExecutionHost — host-independent execution location metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import HostTrustLevel, HostType


@dataclass
class ExecutionHost:
    """Execution location. Agent identity is independent of host (§XX-XXI)."""

    host_id: str
    name: str
    host_type: HostType = HostType.LOCAL_WORKSTATION
    status: str = "online"
    capabilities: list[str] = field(default_factory=list)
    last_heartbeat: str = ""
    resource_profile: str = "standard"
    trust_level: HostTrustLevel = HostTrustLevel.BASIC
    max_concurrent_activations: int = 5
    current_load: int = 0
