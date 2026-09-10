"""EventDispatcher — deterministic routing of events to agent bindings.

Runs the policy engine before any model invocation (§IX, §LX).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collaboration.models import (
    AgentChannelBinding,
    EventEnvelope,
)
from collaboration.models.enums import EventDispatchStatus, MembershipRole
from collaboration.policies import (
    ActorPolicyDecision,
    ActorPolicyEngine,
    EventPolicyDecision,
    EventPolicyEngine,
)
from collaboration.receipts import CollaborationReceiptStore, EventReceipt


@dataclass
class DispatchOutcome:
    event: EventEnvelope
    decision: EventPolicyDecision = field(default_factory=EventPolicyDecision)
    actor_decision: ActorPolicyDecision | None = None
    target_agent: str = ""
    status: EventDispatchStatus = EventDispatchStatus.SKIPPED_POLICY
    activation_id: str = ""


class EventDispatcher:
    """Fail-closed event → policy → activation pipeline."""

    def __init__(
        self,
        *,
        event_policy: EventPolicyEngine | None = None,
        actor_policy: ActorPolicyEngine | None = None,
        receipts: CollaborationReceiptStore | None = None,
    ):
        self.event_policy = event_policy or EventPolicyEngine()
        self.actor_policy = actor_policy or ActorPolicyEngine()
        self.receipts = receipts

    def _skipped_entry(self, agent_id: str, reason: str) -> dict:
        return {"agent_id": agent_id, "reason": reason}

    def dispatch(
        self,
        event: EventEnvelope,
        bindings: list[AgentChannelBinding],
        *,
        roles: dict[str, MembershipRole] | None = None,
        principal_ids: set[str] | None = None,
        tenant_kill_switch_active: bool = False,
    ) -> list[DispatchOutcome]:
        """Evaluate event against every binding; return outcomes (deterministic)."""
        outcomes: list[DispatchOutcome] = []
        activated: list[str] = []
        skipped: list[dict] = []
        roles = roles or {}

        for binding in bindings:
            outcome = DispatchOutcome(event=event)

            # Channel-level kill switch reflected in event_policy via binding path
            decision = self.event_policy.evaluate(
                event,
                binding,
                channel_kill_switch=False,
                tenant_kill_switch=tenant_kill_switch_active,
            )

            if not decision.allow:
                outcome.decision = decision
                outcome.status = self._status_for_skipped(decision)
                skipped.append(self._skipped_entry(binding.agent_id, decision.reason))
                outcomes.append(outcome)
                continue

            # Actor policy — role of the event ACTOR, not the agent
            actor_decision = self.actor_policy.evaluate(
                event,
                binding,
                actor_role=roles.get(event.actor_id),
                principal_ids=principal_ids,
            )
            outcome.actor_decision = actor_decision
            if not actor_decision.allow:
                outcome.status = EventDispatchStatus.SKIPPED_POLICY
                skipped.append(self._skipped_entry(binding.agent_id, actor_decision.reason))
                outcomes.append(outcome)
                continue

            # Shadow mode: agent evaluates but does not activate
            if binding.shadow_mode:
                outcome.status = EventDispatchStatus.SKIPPED_SHADOW
                skipped.append(self._skipped_entry(binding.agent_id, "shadow_mode"))
                outcomes.append(outcome)
                continue

            # Passed all gates → activation
            outcome.target_agent = binding.agent_id
            outcome.activation_id = f"act_{event.event_id}_{binding.agent_id}"
            outcome.status = EventDispatchStatus.DISPATCHED
            activated.append(binding.agent_id)
            outcomes.append(outcome)

        if self.receipts:
            self.receipts.record_event(
                EventReceipt(
                    receipt_id=f"recv_{event.event_id}",
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    tenant_id=event.tenant_id,
                    channel_id=event.channel_id,
                    correlation_id=event.correlation_id,
                    matched_agents=len(bindings),
                    activated_agents=activated,
                    skipped=skipped,
                )
            )

        return outcomes

    @staticmethod
    def _status_for_skipped(decision: EventPolicyDecision) -> EventDispatchStatus:
        if not decision.kill_switch_ok:
            return EventDispatchStatus.BLOCKED_KILL_SWITCH
        if not decision.loop_ok:
            return EventDispatchStatus.SKIPPED_LOOP_GUARD
        if not decision.dedup_ok:
            return EventDispatchStatus.SKIPPED_DEDUP
        if not decision.rate_limit_ok:
            return EventDispatchStatus.SKIPPED_RATE_LIMIT
        if not decision.concurrency_ok:
            return EventDispatchStatus.QUEUED
        if not decision.binding_active:
            return EventDispatchStatus.SKIPPED_AGENT_STOPPED
        if not decision.event_type_allowed:
            return EventDispatchStatus.SKIPPED_NOT_SUBSCRIBED
        if not decision.tenant_match:
            return EventDispatchStatus.SKIPPED_POLICY
        return EventDispatchStatus.SKIPPED_POLICY
