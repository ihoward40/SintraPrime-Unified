"""Event dispatcher integration — triggers swarm execution from events.

Correct canonical ordering:
  Event/Activation Policy → SwarmController → worker execution

This module ports the minimum abstractions from PR #276 needed to trigger
swarm execution through an event/policy gate:

  EventEnvelope — typed event wrapper
  EventPolicyEngine — policy evaluation before dispatch
  SwarmActivationAdapter — translates approved activation → SwarmController

COLLABORATION != EXECUTION_AUTHORITY
The event dispatcher authorizes triggering a swarm but does NOT execute workers.
SwarmController remains the sole execution authority.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EventDispatchStatus(StrEnum):
    DISPATCHED = "dispatched"
    SKIPPED_POLICY = "skipped_policy"
    BLOCKED = "blocked"
    QUEUED = "queued"


class KillSwitchState:
    """Emergency stop — stops agent activation, keeps humans online."""
    def __init__(self) -> None:
        self.active: bool = False
        self.activated_by: str = ""
        self.activated_at: str = ""
        self.reason: str = ""


@dataclass
class EventEnvelope:
    """Typed event wrapper — the input to the dispatch pipeline."""
    event_id: str
    event_type: str
    tenant_id: str
    channel_id: str = ""
    origin_agent_id: str = ""
    hop_count: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    causal_chain: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        event_type: str,
        tenant_id: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> EventEnvelope:
        return cls(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            tenant_id=tenant_id,
            payload=payload or {},
            **kwargs,
        )


@dataclass
class EventPolicyDecision:
    allow: bool = True
    reason: str = ""
    policy_version: str = "1"


class EventPolicyEngine:
    """Evaluates events against policies before dispatch.

    Checks:
    - Kill switch (tenant-level)
    - Deduplication (event already processed)
    - Loop guard (hop count / causal chain)
    - Rate limiting (per-agent activation rate)
    """
    def __init__(
        self,
        *,
        kill_switch: KillSwitchState | None = None,
        max_hops: int = 4,
        rate_per_hour: int = 60,
    ) -> None:
        self.kill_switch = kill_switch or KillSwitchState()
        self.max_hops = max_hops
        self.rate_per_hour = rate_per_hour
        self._consumed: set[str] = set()
        self._rate_window: dict[str, list[float]] = {}

    def evaluate(self, event: EventEnvelope) -> EventPolicyDecision:
        # Kill switch
        if self.kill_switch.active:
            return EventPolicyDecision(False, "BLOCKED_KILL_SWITCH")

        # Loop guard
        if event.hop_count > self.max_hops:
            return EventPolicyDecision(False, f"BLOCKED_LOOP_GUARD: hop_count={event.hop_count}")

        # Cycle detection
        if event.origin_agent_id and event.origin_agent_id in event.causal_chain:
            return EventPolicyDecision(False, "BLOCKED_CYCLE_DETECTED")

        # Dedup
        dedup_key = hashlib.sha256(
            f"{event.event_id}:{event.event_type}".encode()
        ).hexdigest()[:16]
        if dedup_key in self._consumed:
            return EventPolicyDecision(False, "SKIPPED_DUPLICATE")
        self._consumed.add(dedup_key)

        # Rate limit
        now = time.time()
        window = self._rate_window.setdefault(event.tenant_id, [])
        while window and now - window[0] > 3600:
            window.pop(0)
        if len(window) >= self.rate_per_hour:
            return EventPolicyDecision(False, "BLOCKED_RATE_LIMIT")
        window.append(now)

        return EventPolicyDecision(True, "ALLOWED")


@dataclass
class DispatchOutcome:
    event: EventEnvelope
    decision: EventPolicyDecision
    status: EventDispatchStatus
    activation_id: str = ""
    swarm_id: str = ""


class SwarmActivationAdapter:
    """Translates an approved event activation into a SwarmController submission.

    EventDispatcher → SwarmActivationAdapter → SwarmController

    The adapter does NOT execute workers. It translates the approved event
    into WorkerSpec(s) and submits them to SwarmController.
    """
    def __init__(self, controller: Any) -> None:
        self._controller = controller

    def activate(
        self,
        event: EventEnvelope,
        decision: EventPolicyDecision,
        worker_specs: list[Any],  # list[WorkerSpec]
    ) -> DispatchOutcome:
        """Submit approved event's worker specs to SwarmController."""
        if not decision.allow:
            return DispatchOutcome(
                event=event,
                decision=decision,
                status=EventDispatchStatus.BLOCKED,
            )

        # Submit each worker spec to the controller
        launched: list[str] = []
        for spec in worker_specs:
            # Bind identity from event
            if not spec.base_sha:
                spec.base_sha = event.payload.get("base_sha", "")
            wid = self._controller.launch(spec)
            launched.append(wid)

        return DispatchOutcome(
            event=event,
            decision=decision,
            status=EventDispatchStatus.DISPATCHED,
            activation_id=f"act_{uuid.uuid4().hex[:8]}",
            swarm_id=self._controller.swarm_id,
        )


class EventDispatcher:
    """Event → policy → activation pipeline.

    Fail-closed: events are blocked unless policy explicitly allows.
    """
    def __init__(
        self,
        *,
        policy: EventPolicyEngine | None = None,
        activation_adapter: SwarmActivationAdapter | None = None,
    ) -> None:
        self.policy = policy or EventPolicyEngine()
        self.activation_adapter = activation_adapter

    def dispatch(
        self,
        event: EventEnvelope,
        worker_specs: list[Any] | None = None,
    ) -> DispatchOutcome:
        decision = self.policy.evaluate(event)

        if not decision.allow:
            return DispatchOutcome(
                event=event,
                decision=decision,
                status=EventDispatchStatus.SKIPPED_POLICY,
            )

        if self.activation_adapter and worker_specs:
            return self.activation_adapter.activate(event, decision, worker_specs)

        return DispatchOutcome(
            event=event,
            decision=decision,
            status=EventDispatchStatus.DISPATCHED if decision.allow else EventDispatchStatus.BLOCKED,
        )
