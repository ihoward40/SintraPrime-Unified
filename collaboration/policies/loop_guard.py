"""LoopGuard — anti-loop protection with causal chains (§X)."""

from __future__ import annotations

from dataclasses import dataclass

from collaboration.models import EventEnvelope

MAX_AGENT_HOPS_DEFAULT = 4


@dataclass
class LoopGuardVerdict:
    allow: bool = True
    reason: str = ""


class LoopGuard:
    """Bounded agent-to-agent causal chains. Exceeding max hops → BLOCKED_LOOP_GUARD."""

    def __init__(self, max_agent_hops: int = MAX_AGENT_HOPS_DEFAULT):
        self.max_agent_hops = max_agent_hops
        self._blocked: set[str] = set()

    def check(self, event: EventEnvelope) -> LoopGuardVerdict:
        # Hard stop: chain length
        if event.hop_count > self.max_agent_hops:
            return LoopGuardVerdict(False, f"BLOCKED_LOOP_GUARD: hop_count={event.hop_count}")

        # Cycle detection within causal chain: same origin_id already in chain
        if event.origin_id and event.origin_id in event.causal_chain:
            return LoopGuardVerdict(False, "BLOCKED_LOOP_GUARD: origin already in causal chain")

        # Explicit agent-origin blocking for self-origin cycles
        chain_key = f"{event.origin_type}:{event.origin_id}"
        if chain_key in self._blocked:
            return LoopGuardVerdict(False, "BLOCKED_LOOP_GUARD: chain previously blocked")

        return LoopGuardVerdict(True, "allowed")

    def record_blocked(self, event: EventEnvelope) -> None:
        self._blocked.add(f"{event.origin_type}:{event.origin_id}")

    def next_hop_event(
        self, base: EventEnvelope, *, agent_id: str, channel_id: str
    ) -> EventEnvelope:
        """Build a follow-on event with incremented hop and causal chain."""
        return EventEnvelope(
            event_id=f"evt_{agent_id}_hop{base.hop_count + 1}",
            event_type=base.event_type,
            tenant_id=base.tenant_id,
            channel_id=channel_id,
            actor_type="agent",
            actor_id=agent_id,
            correlation_id=base.correlation_id,
            origin_type="agent",
            origin_id=agent_id,
            causal_chain=[*base.causal_chain, agent_id],
            hop_count=base.hop_count + 1,
            workflow_run_id=base.workflow_run_id,
        )
