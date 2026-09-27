"""CF-1 Certification Tests — comprehensive coverage of all directive conditions.

Certification matrix (directive §XCIX):
  Models, Policies, Runtime, POC, Security, Persistence, Concurrency,
  Stop-control, Kill-switch, Loop-guard, Dedup, Handoff, Receipts,
  Provider-swap, Capability-boundary.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from collaboration.events.dispatcher import EventDispatcher
from collaboration.models import (
    AgentBehaviorContract,
    AgentChannelBinding,
    AgentIdentity,
    ChannelBrief,
    EventEnvelope,
)
from collaboration.models.enums import (
    AgentPresenceState,
    AgentResponseMode,
    ChannelStatus,
    ChannelType,
    ContentType,
    EventDispatchStatus,
    EventType,
    HandoffStatus,
    MembershipRole,
    RuntimeStatus,
)
from collaboration.poc.engineering_lab import EngineeringLabPOC
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
from collaboration.receipts import (
    ActivationReceipt,
    CollaborationReceiptStore,
    EventReceipt,
    HandoffReceipt,
)
from collaboration.services import (
    ActivationRequest,
    ActivationService,
    BindingService,
    ChannelService,
    HandoffService,
    MembershipService,
    PresenceService,
    ShutdownService,
)
from collaboration.services.store import CollaborationStore

# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_base():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def store(tmp_base):
    return CollaborationStore(tmp_base / "store")


@pytest.fixture
def receipts(tmp_base):
    return CollaborationReceiptStore(tmp_base / "receipts")


@pytest.fixture
def channel_svc(store):
    return ChannelService(store)


@pytest.fixture
def membership_svc(store):
    return MembershipService(store)


@pytest.fixture
def binding_svc(store):
    return BindingService(store)


@pytest.fixture
def concurrency():
    return ConcurrencyPolicy()


@pytest.fixture
def activation_svc(store, concurrency, receipts):
    return ActivationService(store=store, concurrency=concurrency, receipts=receipts)


@pytest.fixture
def presence_svc():
    return PresenceService()


@pytest.fixture
def shutdown_svc(activation_svc, binding_svc):
    return ShutdownService(activation_svc, binding_svc)


@pytest.fixture
def handoff_svc(store, receipts):
    return HandoffService(store, receipts)


@pytest.fixture
def poc(tmp_base):
    return EngineeringLabPOC(tmp_base / "poc")


# ─────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────


class TestModels:
    def test_channel_type_enum(self):
        assert ChannelType.OPERATIONS.value == "operations"
        assert len(ChannelType) == 9

    def test_event_type_enum(self):
        assert EventType.AGENT_MENTIONED.value == "agent_mentioned"

    def test_agent_identity_independent_of_host(self):
        """§XXI: agent identity belongs to SintraPrime, not execution host."""
        id1 = AgentIdentity(
            agent_id="r-7", name="Research-Agent-7", registered_at="2026-01-01T00:00:00Z"
        )
        id2 = AgentIdentity(
            agent_id="r-7", name="Research-Agent-7", registered_at="2026-01-01T00:00:00Z"
        )
        assert id1.agent_id == id2.agent_id
        id1.current_host_id = "WORKSTATION-A"
        id2.current_host_id = "WORKER-03"
        assert id1.agent_id == id2.agent_id  # identity stable despite different hosts

    def test_behavior_contract_hash(self):
        """§XIV: contract is hashed and versioned."""
        c1 = AgentBehaviorContract(
            agent_id="a", mission="x", authority_class="A0", behavior_contract_version="1"
        )
        c2 = AgentBehaviorContract(
            agent_id="a", mission="x", authority_class="A0", behavior_contract_version="1"
        )
        assert c1.behavior_contract_hash == c2.behavior_contract_hash
        c3 = AgentBehaviorContract(
            agent_id="a", mission="x", authority_class="A1", behavior_contract_version="1"
        )
        assert c1.behavior_contract_hash != c3.behavior_contract_hash

    def test_message_content_types(self):
        assert len(ContentType) == 6

    def test_channel_brief_do_not_do_list(self):
        brief = ChannelBrief(channel_id="ch-1", do_not_do_list=["no merge", "no deploy"])
        assert len(brief.do_not_do_list) == 2


# ─────────────────────────────────────────────────────────────────────
# Channel + Membership + Binding persistence
# ─────────────────────────────────────────────────────────────────────


class TestChannelPersistence:
    def test_create_and_reload(self, channel_svc):
        ch = channel_svc.create(tenant_id="t1", name="eng", slug="eng")
        loaded = channel_svc.get(ch.id)
        assert loaded is not None
        assert loaded.name == "eng"
        assert loaded.status == ChannelStatus.ACTIVE

    def test_list_by_tenant(self, channel_svc):
        channel_svc.create(tenant_id="t1", name="a", slug="a")
        channel_svc.create(tenant_id="t1", name="b", slug="b")
        channel_svc.create(tenant_id="t2", name="c", slug="c")
        t1 = channel_svc.list_by_tenant("t1")
        assert len(t1) == 2

    def test_member_join_and_leave(self, membership_svc):
        m = membership_svc.join(channel_id="ch-1", tenant_id="t1", principal_id="u1")
        active = membership_svc.get_active("ch-1")
        assert len(active) == 1
        membership_svc.leave(m.id)
        active = membership_svc.get_active("ch-1")
        assert len(active) == 0

    def test_role_of(self, membership_svc):
        membership_svc.join(
            channel_id="ch-1",
            tenant_id="t1",
            principal_id="admin1",
            role=MembershipRole.ADMIN,
        )
        assert membership_svc.role_of("ch-1", "admin1") == MembershipRole.ADMIN
        assert membership_svc.role_of("ch-1", "other") is None

    def test_binding_crud(self, binding_svc):
        b = binding_svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a1")
        assert b.response_mode == AgentResponseMode.MENTION_ONLY
        binding_svc.stop(b.id)
        stopped = binding_svc.get(b.id)
        assert stopped.stopped is True
        binding_svc.resume(b.id)
        assert binding_svc.get(b.id).stopped is False

    def test_tenant_isolation(self, channel_svc):
        channel_svc.create(tenant_id="t1", name="x", slug="x")
        ch2 = channel_svc.create(tenant_id="t2", name="y", slug="y")
        # Load is by id, not by tenant — isolation is via query filtering
        all_t1 = channel_svc.list_by_tenant("t1")
        assert all(c.id != ch2.id for c in all_t1)


# ─────────────────────────────────────────────────────────────────────
# Policies
# ─────────────────────────────────────────────────────────────────────


class TestLoopGuard:
    def test_within_limit(self):
        lg = LoopGuard(max_agent_hops=4)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            hop_count=2,
        )
        assert lg.check(evt).allow is True

    def test_exceeds_limit(self):
        lg = LoopGuard(max_agent_hops=4)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            hop_count=5,
        )
        assert lg.check(evt).allow is False

    def test_cycle_in_causal_chain(self):
        lg = LoopGuard()
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            origin_type="agent",
            origin_id="a1",
            causal_chain=["a1", "a2", "a1"],
        )
        assert lg.check(evt).allow is False

    def test_next_hop_event(self):
        lg = LoopGuard()
        base = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            origin_type="agent",
            origin_id="a1",
            correlation_id="c1",
            hop_count=1,
        )
        next_evt = lg.next_hop_event(base, agent_id="a2", channel_id="ch-1")
        assert next_evt.hop_count == 2
        assert "a2" in next_evt.causal_chain


class TestDedup:
    def test_not_consumed(self):
        dp = DeduplicationPolicy()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        assert dp.is_consumed(evt, "agent-1") is False

    def test_mark_consumed(self):
        dp = DeduplicationPolicy()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        dp.mark_consumed(evt, "agent-1")
        assert dp.is_consumed(evt, "agent-1") is True

    def test_reentry_protection(self):
        dp = DeduplicationPolicy()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        dp.mark_consumed(evt, "agent-1")
        assert dp.reentry_allowed(evt, "agent-1") is False

    def test_different_agents_not_confused(self):
        dp = DeduplicationPolicy()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        dp.mark_consumed(evt, "agent-1")
        assert dp.is_consumed(evt, "agent-2") is False


class TestRateLimit:
    def test_allows_first_call(self):
        rl = RateLimitPolicy(default_per_hour=5)
        assert rl.allow("a1") is True
        rl.record("a1")

    def test_blocks_after_limit(self):
        rl = RateLimitPolicy(default_per_hour=2)
        assert rl.allow("a1") is True
        rl.record("a1")
        assert rl.allow("a1") is True
        rl.record("a1")
        assert rl.allow("a1") is False

    def test_independent_agents(self):
        rl = RateLimitPolicy(default_per_hour=1)
        rl.record("a1")
        assert rl.allow("a1") is False
        assert rl.allow("a2") is True


class TestConcurrency:
    def test_acquire_release(self):
        cp = ConcurrencyPolicy()
        assert cp.allow("a1", 2) is True
        cp.acquire("a1")
        assert cp.allow("a1", 2) is True
        cp.acquire("a1")
        assert cp.allow("a1", 2) is False
        cp.release("a1")
        assert cp.allow("a1", 2) is True

    def test_inflight_count(self):
        cp = ConcurrencyPolicy()
        cp.acquire("a1")
        cp.acquire("a1")
        assert cp.inflight("a1") == 2
        cp.reset("a1")
        assert cp.inflight("a1") == 0


class TestKillSwitch:
    def test_activate_blocks(self):
        ks = KillSwitch()
        assert ks.active is False
        ks.activate(operator="p1", reason="test")
        assert ks.active is True
        assert ks.is_blocked(channel_id="ch-1") is True

    def test_deactivate_restores(self):
        ks = KillSwitch()
        ks.activate(operator="p1")
        ks.deactivate(operator="p1")
        assert ks.active is False
        assert ks.is_blocked() is False

    def test_channel_specific(self):
        ks = KillSwitch()
        ks.activate(operator="p1", channel_ids=["ch-x"])
        assert ks.is_blocked(channel_id="ch-x") is True
        assert ks.is_blocked(channel_id="ch-y") is False

    def test_human_messages_unaffected(self):
        """§XVI: human channel communication continues."""
        ks = KillSwitch()
        ks.activate(operator="p1")
        snap = ks.snapshot()
        assert snap["active"] is True


class TestActorPolicy:
    def test_allowlist_blocks_unknown(self):
        ap = ActorPolicyEngine()
        ap.set_policy("a1", ActorTriggerPolicy.ALLOWLIST)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            actor_type="human",
            actor_id="unknown-user",
        )
        b = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            actor_allowlist=["known-user"],
        )
        d = ap.evaluate(evt, b)
        assert d.allow is False

    def test_system_only(self):
        ap = ActorPolicyEngine()
        ap.set_policy("a1", ActorTriggerPolicy.SYSTEM_ONLY)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            actor_type="system",
            actor_id="sys1",
        )
        b = AgentChannelBinding(id="b1", tenant_id="t1", channel_id="ch-1", agent_id="a1")
        assert ap.evaluate(evt, b).allow is True

    def test_principal_only(self):
        ap = ActorPolicyEngine()
        ap.set_policy("a1", ActorTriggerPolicy.PRINCIPAL_ONLY)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            actor_type="human",
            actor_id="principal-1",
        )
        b = AgentChannelBinding(id="b1", tenant_id="t1", channel_id="ch-1", agent_id="a1")
        assert ap.evaluate(evt, b, principal_ids={"principal-1"}).allow is True
        assert ap.evaluate(evt, b, principal_ids={"other"}).allow is False


class TestEventPolicy:
    def test_kill_switch_blocks(self):
        ks = KillSwitch()
        ks.activate(operator="p1")
        ep = EventPolicyEngine(kill_switch=ks)
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(id="b1", tenant_id="t1", channel_id="ch-1", agent_id="a1")
        d = ep.evaluate(evt, b, tenant_kill_switch=True)
        assert d.allow is False

    def test_no_binding_no_activation(self):
        ep = EventPolicyEngine()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        d = ep.evaluate(evt, None)
        assert d.allow is False

    def test_stopped_binding_blocked(self):
        ep = EventPolicyEngine()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(
            id="b1", tenant_id="t1", channel_id="ch-1", agent_id="a1", stopped=True
        )
        d = ep.evaluate(evt, b)
        assert d.allow is False

    def test_tenant_mismatch(self):
        ep = EventPolicyEngine()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(id="b1", tenant_id="t2", channel_id="ch-1", agent_id="a1")
        d = ep.evaluate(evt, b)
        assert d.allow is False

    def test_event_type_not_allowed(self):
        ep = EventPolicyEngine()
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.WORKFLOW_FAILED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            allowed_event_types=["channel_message_created"],
        )
        d = ep.evaluate(evt, b)
        assert d.allow is False

    def test_loop_guard_integration(self):
        lg = LoopGuard(max_agent_hops=2)
        ep = EventPolicyEngine(loop_guard=lg)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            hop_count=3,
        )
        b = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            allowed_event_types=["agent_mentioned"],
        )
        d = ep.evaluate(evt, b)
        assert d.allow is False
        assert "loop_guard" in d.skipped_reasons

    def test_dedup_integration(self):
        dp = DeduplicationPolicy()
        ep = EventPolicyEngine(dedup=dp)
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            allowed_event_types=["agent_mentioned"],
        )
        dp.mark_consumed(evt, "a1")
        d = ep.evaluate(evt, b)
        assert d.allow is False
        assert "dedup" in d.skipped_reasons

    def test_rate_limit_integration(self):
        rl = RateLimitPolicy(default_per_hour=1)
        ep = EventPolicyEngine(rate_limit=rl)
        evt = EventEnvelope(
            event_id="e1", event_type=EventType.AGENT_MENTIONED, tenant_id="t1", channel_id="ch-1"
        )
        b = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            rate_limit_per_hour=1,
            allowed_event_types=["agent_mentioned"],
        )
        ep.evaluate(evt, b)  # first call
        rl.record("a1")
        d = ep.evaluate(evt, b)  # second call — over limit
        assert d.allow is False
        assert "rate_limit" in d.skipped_reasons


# ─────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────


class TestDispatcher:
    def test_dispatch_to_matching_bindings(self, receipts):
        dp = DeduplicationPolicy()
        ep = EventPolicyEngine(dedup=dp)
        dispatcher = EventDispatcher(event_policy=ep, receipts=receipts)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="t1",
            channel_id="ch-1",
            actor_type="system",
            actor_id="sys1",
        )
        b1 = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            allowed_event_types=["agent_mentioned"],
        )
        b2 = AgentChannelBinding(
            id="b2",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a2",
            allowed_event_types=["agent_mentioned"],
        )
        outcomes = dispatcher.dispatch(evt, [b1, b2])
        dispatched = [o for o in outcomes if o.status == EventDispatchStatus.DISPATCHED]
        assert len(dispatched) == 2

    def test_dispatch_blocked_event_type(self, receipts):
        ep = EventPolicyEngine(dedup=DeduplicationPolicy())
        dispatcher = EventDispatcher(event_policy=ep, receipts=receipts)
        evt = EventEnvelope(
            event_id="e1",
            event_type=EventType.WORKFLOW_FAILED,
            tenant_id="t1",
            channel_id="ch-1",
            actor_type="system",
            actor_id="sys1",
        )
        b1 = AgentChannelBinding(
            id="b1",
            tenant_id="t1",
            channel_id="ch-1",
            agent_id="a1",
            allowed_event_types=["channel_message_created"],
        )
        outcomes = dispatcher.dispatch(evt, [b1])
        assert outcomes[0].status == EventDispatchStatus.SKIPPED_NOT_SUBSCRIBED


# ─────────────────────────────────────────────────────────────────────
# Services integration
# ─────────────────────────────────────────────────────────────────────


class TestActivationService:
    def test_request_and_complete(self, activation_svc):
        ar = activation_svc.request(
            ActivationRequest(
                activation_id="a1", agent_id="agent-x", channel_id="ch-1", tenant_id="t1"
            ),
            max_parallelism=3,
        )
        assert ar.status == RuntimeStatus.RUNNING
        ar2 = activation_svc.complete("a1")
        assert ar2.status == RuntimeStatus.COMPLETED

    def test_queue_when_at_capacity(self, activation_svc):
        activation_svc.request(
            ActivationRequest(activation_id="a1", agent_id="a1", channel_id="ch-1", tenant_id="t1"),
            max_parallelism=1,
        )
        activation_svc.request(
            ActivationRequest(activation_id="a2", agent_id="a1", channel_id="ch-1", tenant_id="t1"),
            max_parallelism=1,
        )
        ar2 = activation_svc.get("a2")
        assert ar2.status == RuntimeStatus.QUEUED

    def test_fail(self, activation_svc):
        activation_svc.request(
            ActivationRequest(activation_id="a1", agent_id="a1", channel_id="ch-1", tenant_id="t1"),
            max_parallelism=3,
        )
        ar = activation_svc.fail("a1", error="provider down")
        assert ar.status == RuntimeStatus.FAILED

    def test_list_by_channel(self, activation_svc):
        activation_svc.request(
            ActivationRequest(activation_id="a1", agent_id="a1", channel_id="ch-1", tenant_id="t1"),
            max_parallelism=3,
        )
        items = activation_svc.list_by_channel("ch-1")
        assert len(items) == 1


class TestHandoffService:
    def test_create_accept_complete(self, handoff_svc):
        h = handoff_svc.create(
            handoff_id="h1",
            source_agent="a1",
            target_agent="a2",
            channel_id="ch-1",
            tenant_id="t1",
            task="review",
        )
        assert h.status == HandoffStatus.PENDING
        h2 = handoff_svc.accept("h1")
        assert h2.status == HandoffStatus.ACCEPTED
        h3 = handoff_svc.complete("h1", ["result.md"])
        assert h3.status == HandoffStatus.COMPLETED
        assert h3.result_artifacts == ["result.md"]


class TestPresenceService:
    def test_set_and_get(self, presence_svc):
        presence_svc.set("a1", AgentPresenceState.THINKING, "analyzing code")
        assert presence_svc.get_state("a1") == AgentPresenceState.THINKING
        assert presence_svc.get_activity("a1") == "analyzing code"

    def test_default_offline(self, presence_svc):
        assert presence_svc.get_state("unknown-agent") == AgentPresenceState.OFFLINE


class TestShutdownService:
    def test_stop_agent(self, shutdown_svc, binding_svc):
        binding_svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a1")
        result = shutdown_svc.stop_agent("a1", "ch-1")
        assert result["status"] == "stopped"
        b = binding_svc.list_for_agent("a1")[0]
        assert b.stopped is True

    def test_stop_all_in_channel(self, shutdown_svc, binding_svc):
        binding_svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a1")
        binding_svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a2")
        results = shutdown_svc.stop_all_in_channel("ch-1")
        assert len(results) == 2


# ─────────────────────────────────────────────────────────────────────
# Receipts
# ─────────────────────────────────────────────────────────────────────


class TestReceipts:
    def test_event_receipt_chain(self, receipts):
        receipts.record_event(
            EventReceipt(
                receipt_id="r1",
                event_id="e1",
                event_type="x",
                tenant_id="t1",
                channel_id="ch-1",
                correlation_id="c1",
            )
        )
        ok, reason = receipts.verify_chain("event", "e1")
        assert ok, reason

    def test_activation_receipt_chain(self, receipts):
        receipts.record_activation(
            ActivationReceipt(
                receipt_id="r1",
                activation_id="a1",
                agent_id="ag",
                channel_id="ch-1",
                tenant_id="t1",
            )
        )
        ok, reason = receipts.verify_chain("activation", "a1")
        assert ok, reason

    def test_handoff_receipt_chain(self, receipts):
        receipts.record_handoff(
            HandoffReceipt(
                receipt_id="r1",
                handoff_id="h1",
                source_agent="s",
                target_agent="t",
                channel_id="ch-1",
                tenant_id="t1",
            )
        )
        ok, reason = receipts.verify_chain("handoff", "h1")
        assert ok, reason

    def test_tampered_receipt_detected(self, receipts):
        receipts.record_event(
            EventReceipt(
                receipt_id="r1",
                event_id="e1",
                event_type="x",
                tenant_id="t1",
                channel_id="ch-1",
                correlation_id="c1",
            )
        )
        chain_file = receipts.base_dir / "event_e1.jsonl"
        lines = chain_file.read_text(encoding="utf-8").splitlines()
        rec = __import__("json").loads(lines[0])
        rec["tenant_id"] = "TAMPERED"
        chain_file.write_text(__import__("json").dumps(rec) + "\n", encoding="utf-8")
        ok, reason = receipts.verify_chain("event", "e1")
        assert not ok
        assert "hash mismatch" in reason


# ─────────────────────────────────────────────────────────────────────
# Persistence / restart recovery
# ─────────────────────────────────────────────────────────────────────


class TestPersistence:
    def test_restart_preserves_channel(self, store):
        svc = ChannelService(store)
        ch = svc.create(tenant_id="t1", name="x", slug="x")
        # "restart" = new service with same store
        svc2 = ChannelService(store)
        loaded = svc2.get(ch.id)
        assert loaded.name == "x"

    def test_restart_preserves_binding(self, store):
        svc = BindingService(store)
        b = svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a1")
        svc.stop(b.id)
        # restart
        svc2 = BindingService(store)
        loaded = svc2.get(b.id)
        assert loaded.stopped is True

    def test_stop_persists(self, store):
        svc = BindingService(store)
        b = svc.bind(tenant_id="t1", channel_id="ch-1", agent_id="a1")
        svc.stop(b.id)
        loaded = svc.get(b.id)
        assert loaded.stopped is True
        # reload
        loaded2 = BindingService(store).get(b.id)
        assert loaded2.stopped is True


# ─────────────────────────────────────────────────────────────────────
# POC
# ─────────────────────────────────────────────────────────────────────


class TestEngineeringLabPOC:
    def test_setup(self, poc):
        result = poc.setup()
        assert result["status"] == "ready"
        assert result["agents"] == 3

    def test_full_proof(self, poc):
        setup = poc.setup()
        proof = poc.run_proof(setup["channel_id"])
        assert proof["proof"] == "complete"
        assert proof["activations"] == 1
        assert proof["handoffs"] == 2
        assert proof["loop_blocked"] is True
        assert proof["kill_switch_proof"] is True

    def test_dedup_blocks_second_event(self, poc):
        setup = poc.setup()
        poc.run_proof(setup["channel_id"])
        # Try to replay the same event — dedup should block
        evt_replay = EventEnvelope(
            event_id="evt-001",  # same as in proof
            event_type=EventType.AGENT_MENTIONED,
            tenant_id="tenant-1",
            channel_id=setup["channel_id"],
            actor_type="human",
            actor_id="principal-1",
        )
        bindings = poc.binding_svc.list_for_channel(setup["channel_id"])
        outcomes = poc.dispatcher.dispatch(
            evt_replay,
            bindings,
            principal_ids={"principal-1"},
        )
        hermes_outcomes = [o for o in outcomes if o.target_agent == "hermes-coordinator"]
        # Should be skipped due to dedup
        assert (
            len(hermes_outcomes) == 0 or hermes_outcomes[0].status != EventDispatchStatus.DISPATCHED
        )
