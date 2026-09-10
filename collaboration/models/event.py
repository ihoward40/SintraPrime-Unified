"""EventEnvelope and EventSubscription — structured event system."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import EventType


@dataclass
class EventEnvelope:
    """Canonical structured event (directive §VIII)."""

    event_id: str
    event_type: EventType
    tenant_id: str
    channel_id: str
    actor_type: str = "human"
    actor_id: str = ""
    timestamp: str = ""
    correlation_id: str = ""
    payload: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    security_classification: str = "internal"
    # Anti-loop protection (§X)
    origin_type: str = "human"
    origin_id: str = ""
    causal_chain: list = field(default_factory=list)
    hop_count: int = 0
    workflow_run_id: str = ""


@dataclass
class EventSubscription:
    """Agent's subscription to event types in a channel (directive §VII)."""

    id: str
    agent_id: str
    channel_id: str
    event_types: list[str] = field(default_factory=list)
    active: bool = True
    created_at: str = ""
