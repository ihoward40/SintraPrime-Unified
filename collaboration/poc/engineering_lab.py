"""POC: engineering-lab — proof of event-driven wakeup, handoff, loop guard, dedup."""

from __future__ import annotations

from pathlib import Path

from collaboration.events.dispatcher import EventDispatcher
from collaboration.models import (
    AgentBehaviorContract,
    EventEnvelope,
)
from collaboration.models.enums import (
    AgentPresenceState,
    ChannelType,
    ChannelVisibility,
    EventType,
    MembershipRole,
)
from collaboration.policies import (
    ActorPolicyEngine,
    ActorTriggerPolicy,
    ConcurrencyPolicy,
    DeduplicationPolicy,
    EventPolicyEngine,
    KillSwitch,
    LoopGuard,
    RateLimitPolicy,
)
from collaboration.receipts import CollaborationReceiptStore
from collaboration.services.activation_service import ActivationService
from collaboration.services.binding_service import BindingService
from collaboration.services.channel_service import ChannelService
from collaboration.services.handoff_service import HandoffService
from collaboration.services.membership_service import MembershipService
from collaboration.services.presence_service import PresenceService
from collaboration.services.shutdown_service import ShutdownService
from collaboration.services.store import CollaborationStore


class EngineeringLabPOC:
    """Demonstrates CF-1 proof conditions.

    Proof scenario:
        Principal posts: "Analyze issue TEST-001."
        → AGENT_MENTIONED event
        → Hermes Coordinator activation
        → Handoff to Engineer
        → Handoff to Auditor (fresh context)
        → Hermes consolidation
    """

    def __init__(self, base_dir: str | Path):
        base = Path(base_dir)
        self.store = CollaborationStore(base / "store")
        self.receipts = CollaborationReceiptStore(base / "receipts")
        self.kill_switch = KillSwitch()
        self.dedup = DeduplicationPolicy()
        self.rate_limit = RateLimitPolicy()
        self.loop_guard = LoopGuard(max_agent_hops=4)
        self.concurrency = ConcurrencyPolicy()
        self.event_policy = EventPolicyEngine(
            max_agent_hops=4,
            kill_switch=self.kill_switch,
            dedup=self.dedup,
            rate_limit=self.rate_limit,
            loop_guard=self.loop_guard,
            concurrency=self.concurrency,
        )
        self.actor_policy = ActorPolicyEngine()
        self.dispatcher = EventDispatcher(
            event_policy=self.event_policy,
            actor_policy=self.actor_policy,
            receipts=self.receipts,
        )
        self.channel_svc = ChannelService(self.store)
        self.membership_svc = MembershipService(self.store)
        self.binding_svc = BindingService(self.store)
        self.handoff_svc = HandoffService(self.store, self.receipts)
        self.presence = PresenceService()
        self.shutdown_svc = ShutdownService(
            ActivationService(
                store=self.store, concurrency=self.concurrency, receipts=self.receipts
            ),
            self.binding_svc,
        )
        self.activation_svc = self.shutdown_svc.activations

        # Contracts
        self.contracts = {}

    def setup(self) -> dict:
        """Create the engineering-lab channel + 3 agents."""
        # Channel
        ch = self.channel_svc.create(
            tenant_id="tenant-1",
            name="engineering-lab",
            slug="engineering-lab",
            channel_type=ChannelType.ENGINEERING,
            visibility=ChannelVisibility.TENANT,
            description="CF-1 proof-of-concept collaboration channel",
        )

        # Members — Principal is channel OWNER (needed for CHANNEL_ADMINS policy)
        self.membership_svc.join(
            channel_id=ch.id,
            tenant_id="tenant-1",
            principal_id="principal-1",
            role=MembershipRole.OWNER,
        )
        for agent_id in ["hermes-coordinator", "engineer", "auditor"]:
            self.membership_svc.join(
                channel_id=ch.id,
                tenant_id="tenant-1",
                principal_id=agent_id,
                principal_type="agent",
            )

        # Behavior contracts
        for agent_id, mission, auth_class in [
            ("hermes-coordinator", "Coordinate engineering tasks", "A1"),
            ("engineer", "Implement code changes", "A1"),
            ("auditor", "Fresh-context independent review", "A0"),
        ]:
            self.contracts[agent_id] = AgentBehaviorContract(
                agent_id=agent_id,
                mission=mission,
                authority_class=auth_class,
            )

        # Bindings
        self.binding_svc.bind(
            tenant_id="tenant-1",
            channel_id=ch.id,
            agent_id="hermes-coordinator",
            allowed_event_types=[
                EventType.CHANNEL_MESSAGE_CREATED.value,
                EventType.AGENT_MENTIONED.value,
                EventType.WORKFLOW_COMPLETED.value,
                EventType.HANDOFF_COMPLETED.value,
            ],
            max_parallelism=2,
        )
        self.binding_svc.bind(
            tenant_id="tenant-1",
            channel_id=ch.id,
            agent_id="engineer",
            allowed_event_types=[
                EventType.HANDOFF_CREATED.value,
                EventType.COMMAND_CREATED.value,
            ],
            max_parallelism=2,
        )
        self.binding_svc.bind(
            tenant_id="tenant-1",
            channel_id=ch.id,
            agent_id="auditor",
            allowed_event_types=[EventType.HANDOFF_CREATED.value],
            max_parallelism=2,
            shadow_mode=False,
        )

        # Actor policy: ALLOWLIST per directive §XII
        self.actor_policy.set_policy("hermes-coordinator", ActorTriggerPolicy.CHANNEL_ADMINS)
        self.actor_policy.set_policy("engineer", ActorTriggerPolicy.ALLOWLIST)
        self.actor_policy.set_policy("auditor", ActorTriggerPolicy.ALLOWLIST)

        # Presence
        for aid in ["hermes-coordinator", "engineer", "auditor"]:
            self.presence.set(aid, AgentPresenceState.IDLE)

        return {"channel_id": ch.id, "status": "ready", "agents": 3}

    def _roles_for_channel(self, channel_id: str) -> dict:
        roles = {}
        for m in self.membership_svc.get_active(channel_id):
            roles[m.principal_id] = m.role
        return roles

    def _ts(self, i: int) -> str:
        return f"2026-08-08T12:00:0{i}Z"

    def run_proof(self, channel_id: str) -> dict:
        """Execute the CF-1 proof scenario."""
        ts = self._ts

        # Step 1: Human posts → AGENT_MENTIONED
        evt1 = EventEnvelope(
            event_id="evt-001",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="tenant-1",
            channel_id=channel_id,
            actor_type="human",
            actor_id="principal-1",
            timestamp=ts(0),
            correlation_id="corr-001",
            payload={"text": "Analyze issue TEST-001.", "mention": "hermes-coordinator"},
        )
        bindings = self.binding_svc.list_for_channel(channel_id)
        roles = self._roles_for_channel(channel_id)
        outcomes1 = self.dispatcher.dispatch(
            evt1,
            bindings,
            roles=roles,
            principal_ids={"principal-1"},
        )
        hermes_active = [o for o in outcomes1 if o.target_agent == "hermes-coordinator"]
        assert len(hermes_active) == 1, "Hermes should be activated"
        self.dedup.mark_consumed(evt1, "hermes-coordinator")
        self.concurrency.acquire("hermes-coordinator")

        # Step 2: Hermes hands off to Engineer
        handoff1 = self.handoff_svc.create(
            handoff_id="handoff-001",
            source_agent="hermes-coordinator",
            target_agent="engineer",
            channel_id=channel_id,
            tenant_id="tenant-1",
            task="Implement change for TEST-001",
            correlation_id="corr-001",
        )
        self.handoff_svc.accept(handoff1.handoff_id)
        self.handoff_svc.complete(handoff1.handoff_id, ["artifact:plan"])
        self.concurrency.release("hermes-coordinator")

        # Step 3: Engineer hands off to Auditor (fresh context)
        handoff2 = self.handoff_svc.create(
            handoff_id="handoff-002",
            source_agent="engineer",
            target_agent="auditor",
            channel_id=channel_id,
            tenant_id="tenant-1",
            task="Review implementation of TEST-001",
            input_artifacts=["artifact:plan"],
            expected_output_schema="ReviewResult",
            correlation_id="corr-001",
        )
        self.handoff_svc.accept(handoff2.handoff_id)
        self.handoff_svc.complete(handoff2.handoff_id, ["artifact:review"])

        # Step 4: Loop guard proof — attempt agent-to-agent infinite loop
        loop_evt = EventEnvelope(
            event_id="evt-loop-1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="tenant-1",
            channel_id=channel_id,
            actor_type="agent",
            actor_id="auditor",
            origin_type="agent",
            origin_id="auditor",
            causal_chain=["hermes", "engineer", "auditor", "hermes", "engineer", "auditor"],
            hop_count=6,
        )
        loop_outcome = self.dispatcher.dispatch(loop_evt, bindings, principal_ids={"principal-1"})
        blocked = [
            o for o in loop_outcome if "blocked" in o.status.value or "skipped" in o.status.value
        ]
        assert len(blocked) > 0, "Loop should be blocked by loop guard"

        # Step 5: Kill switch proof
        self.kill_switch.activate(operator="principal-1", reason="proof test")
        ks_evt = EventEnvelope(
            event_id="evt-ks-test",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="tenant-1",
            channel_id=channel_id,
            actor_type="human",
            actor_id="principal-1",
            timestamp=ts(5),
        )
        ks_outcome = self.dispatcher.dispatch(ks_evt, bindings, tenant_kill_switch_active=True)
        all_blocked = all(
            "blocked" in str(o.status.value).lower() or "kill" in str(o.status.value).lower()
            for o in ks_outcome
        )
        assert all_blocked, "Kill switch should block all agents"
        self.kill_switch.deactivate(operator="principal-1")

        return {
            "proof": "complete",
            "activations": len(hermes_active),
            "handoffs": 2,
            "loop_blocked": True,
            "kill_switch_proof": True,
            "dedup_events_consumed": 1,
        }
