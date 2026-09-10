"""ActivationRecord — per-agent per-event execution trace."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import RuntimeStatus


@dataclass
class ActivationRecord:
    """One agent activation triggered by one event (directive §XLVIII)."""

    activation_id: str
    agent_id: str
    channel_id: str
    tenant_id: str
    trigger_event_id: str = ""
    status: RuntimeStatus = RuntimeStatus.PENDING
    provider: str = ""
    model: str = ""
    capabilities_used: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    output: dict = field(default_factory=dict)
    duration: float = 0.0
    token_usage: int = 0
    cost: float = 0.0
    host_id: str = ""
    execution_host: str = ""
    behavior_contract_hash: str = ""
    policy_version: str = ""
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    correlation_id: str = ""
