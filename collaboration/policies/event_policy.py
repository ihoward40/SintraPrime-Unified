"""EventPolicyEngine — deterministic filtering before model invocation (§IX)."""

from __future__ import annotations

from dataclasses import dataclass, field

from collaboration.models import AgentChannelBinding, EventEnvelope, EventType

from .concurrency_policy import ConcurrencyPolicy
from .dedup import DeduplicationPolicy
from .kill_switch import KillSwitch
from .loop_guard import LoopGuard
from .rate_limit import RateLimitPolicy


@dataclass
class EventPolicyDecision:
    allow: bool = False
    reason: str = ""
    matched_subscription: bool = False
    event_type_allowed: bool = False
    tenant_match: bool = False
    actor_authorized: bool = False
    binding_active: bool = False
    budget_ok: bool = True
    rate_limit_ok: bool = True
    concurrency_ok: bool = True
    loop_ok: bool = True
    dedup_ok: bool = True
    kill_switch_ok: bool = True
    untrusted_input: bool = False
    skipped_reasons: list[str] = field(default_factory=list)


class EventPolicyEngine:
    """Fail-closed event gate: every check must pass for activation."""

    def __init__(
        self,
        *,
        max_agent_hops: int = 4,
        kill_switch: KillSwitch | None = None,
        dedup: DeduplicationPolicy | None = None,
        rate_limit: RateLimitPolicy | None = None,
        loop_guard: LoopGuard | None = None,
        concurrency: ConcurrencyPolicy | None = None,
        quarantine_service: object | None = None,
        invariant_engine: object | None = None,
    ):
        self.max_agent_hops = max_agent_hops
        self.kill_switch = kill_switch
        self.dedup = dedup
        self.rate_limit = rate_limit
        self.loop_guard = loop_guard
        self.concurrency = concurrency
        self.quarantine_service = quarantine_service
        self.invariant_engine = invariant_engine

    def evaluate(
        self,
        event: EventEnvelope,
        binding: AgentChannelBinding | None,
        *,
        channel_kill_switch: bool = False,
        tenant_kill_switch: bool = False,
    ) -> EventPolicyDecision:
        d = EventPolicyDecision()

        # 1. Kill switch (tenant or channel) — absolute gate
        if tenant_kill_switch or channel_kill_switch:
            d.allow = False
            d.kill_switch_ok = False
            d.reason = "kill_switch_active"
            d.skipped_reasons.append("kill_switch")
            return d

        # 2. No binding → no activation
        if binding is None:
            d.allow = False
            d.reason = "agent_not_bound_to_channel"
            d.skipped_reasons.append("no_binding")
            return d

        d.binding_active = binding.status == "active" and not binding.stopped
        if not d.binding_active:
            d.allow = False
            d.reason = "binding_inactive_or_stopped"
            d.skipped_reasons.append("binding_stopped")
            return d

        # 3. Tenant match
        d.tenant_match = event.tenant_id == binding.tenant_id
        if not d.tenant_match:
            d.allow = False
            d.reason = "tenant_mismatch"
            d.skipped_reasons.append("tenant_mismatch")
            return d

        # 3a. Agent quarantine — quarantined agents receive no new activation (§47)
        if self.quarantine_service and hasattr(self.quarantine_service, "is_quarantined"):
            if self.quarantine_service.is_quarantined(binding.agent_id):
                d.allow = False
                d.reason = "agent_quarantined"
                d.skipped_reasons.append("quarantine")
                return d

        # 3b. Constitutional invariant gate (§2)
        if self.invariant_engine and hasattr(self.invariant_engine, "evaluate_all"):
            from collaboration.governance.invariants import ActionContext

            ctx = ActionContext(
                action="activate",
                actor_id=binding.agent_id,
                actor_type="agent",
                tenant_id=event.tenant_id,
                matter_id=event.payload.get("matter_id", ""),
            )
            if not self.invariant_engine.evaluate_all(ctx):
                d.allow = False
                d.reason = "constitutional_invariant_violation"
                d.skipped_reasons.append("invariant")
                return d

        # 4. Event type allowed by binding
        d.event_type_allowed = event.event_type.value in binding.allowed_event_types or (
            event.event_type.value in (EventType.CHANNEL_MESSAGE_CREATED.value,)
            and binding.response_mode.value != "passive"
        )
        if not d.event_type_allowed:
            d.allow = False
            d.reason = "event_type_not_allowed"
            d.skipped_reasons.append("event_type_not_allowed")
            return d

        # 5. Subscription match (if subscription provided via binding events)
        d.matched_subscription = True  # bindings are the subscription in CF-1

        # 6. Loop guard — agent-originated chains bounded
        if self.loop_guard:
            loop_verdict = self.loop_guard.check(event)
            d.loop_ok = loop_verdict.allow
            if not d.loop_ok:
                d.allow = False
                d.reason = loop_verdict.reason
                d.skipped_reasons.append("loop_guard")
                return d
        elif event.hop_count > self.max_agent_hops:
            d.loop_ok = False
            d.allow = False
            d.reason = f"hop_count_exceeds_max({self.max_agent_hops})"
            d.skipped_reasons.append("loop_guard")
            return d

        # 7. Dedup — event already consumed by this agent
        if self.dedup:
            if self.dedup.is_consumed(event, binding.agent_id):
                d.dedup_ok = False
                d.allow = False
                d.reason = "event_already_consumed"
                d.skipped_reasons.append("dedup")
                return d

        # 8. Rate limit
        if self.rate_limit:
            if not self.rate_limit.allow(binding.agent_id):
                d.rate_limit_ok = False
                d.allow = False
                d.reason = "rate_limit_exceeded"
                d.skipped_reasons.append("rate_limit")
                return d

        # 9. Concurrency limit
        if self.concurrency:
            if not self.concurrency.allow(binding.agent_id, binding.max_parallelism):
                d.concurrency_ok = False
                d.allow = False
                d.reason = "concurrency_limit_exceeded"
                d.skipped_reasons.append("concurrency")
                return d

        # 10. Untrusted input detection (prompt injection heuristic)
        if event.actor_type == "agent" and event.actor_id != binding.agent_id:
            d.untrusted_input = True

        d.allow = True
        d.reason = "allowed"
        return d
