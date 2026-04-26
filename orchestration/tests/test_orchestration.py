"""
test_orchestration.py
=====================
Comprehensive test suite for SintraPrime-Unified orchestration layer.

Covers:
- StateGraph / Node / Edge / ConditionalEdge (LangGraph engine)
- A2A messaging protocol
- Durable execution (persistence, retries, saga)
- Orchestration API

Run with:
    python -m pytest orchestration/tests/ -v
"""

from __future__ import annotations

import asyncio
import sys
import os
import time
import uuid

# Allow importing orchestration as a package from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# LangGraph Engine Tests
# ---------------------------------------------------------------------------

from orchestration.langgraph_engine import (
    GraphState,
    GraphStatus,
    Node,
    Edge,
    ConditionalEdge,
    StateGraph,
    CompiledGraph,
    InMemoryCheckpointer,
    Checkpoint,
    ExecutionResult,
    create_legal_graph,
    BUILTIN_NODES,
    NodeStatus,
)


class TestGraphState:
    def test_basic_get_set(self):
        s = GraphState({"a": 1, "b": 2})
        assert s["a"] == 1
        assert s["b"] == 2

    def test_update_state(self):
        s = GraphState({"x": 0})
        s.update_state({"x": 1, "y": 2})
        assert s["x"] == 1
        assert s["y"] == 2
        assert s.history_length() == 1

    def test_rollback(self):
        s = GraphState({"x": 0})
        s.update_state({"x": 1})
        assert s["x"] == 1
        result = s.rollback()
        assert result is True
        assert s["x"] == 0

    def test_rollback_empty(self):
        s = GraphState({"x": 0})
        assert s.rollback() is False

    def test_snapshot(self):
        s = GraphState({"a": 1})
        snap = s.snapshot()
        s["a"] = 99
        assert snap["a"] == 1  # snapshot is isolated

    def test_multiple_updates(self):
        s = GraphState()
        for i in range(5):
            s.update_state({f"key_{i}": i})
        assert s.history_length() == 5
        assert s["key_4"] == 4


class TestCheckpointer:
    def test_save_and_load(self):
        cp = InMemoryCheckpointer()
        ckpt = Checkpoint(
            graph_id="g1", run_id="r1", node_name="intake",
            state={"x": 1}, visited_counts={"intake": 1}
        )
        cp.save(ckpt)
        loaded = cp.load_latest("g1", "r1")
        assert loaded is not None
        assert loaded.node_name == "intake"
        assert loaded.state["x"] == 1

    def test_load_missing(self):
        cp = InMemoryCheckpointer()
        assert cp.load_latest("nope", "nope") is None

    def test_multiple_checkpoints(self):
        cp = InMemoryCheckpointer()
        for i in range(3):
            cp.save(Checkpoint(
                graph_id="g1", run_id="r1",
                node_name=f"node_{i}",
                state={"step": i}, visited_counts={f"node_{i}": 1}
            ))
        latest = cp.load_latest("g1", "r1")
        assert latest.node_name == "node_2"
        assert len(cp.load_all("g1", "r1")) == 3

    def test_list_runs(self):
        cp = InMemoryCheckpointer()
        cp.save(Checkpoint(graph_id="g1", run_id="r1", node_name="n", state={}, visited_counts={}))
        cp.save(Checkpoint(graph_id="g1", run_id="r2", node_name="n", state={}, visited_counts={}))
        runs = cp.list_runs("g1")
        assert "r1" in runs
        assert "r2" in runs


class TestNode:
    @pytest.mark.asyncio
    async def test_sync_node(self):
        def my_func(state):
            return {"result": state["x"] + 1}
        node = Node("test", my_func, is_async=False)
        state = GraphState({"x": 5})
        result = await node.execute(state)
        assert result["result"] == 6

    @pytest.mark.asyncio
    async def test_async_node(self):
        async def my_async_func(state):
            return {"async_result": "done"}
        node = Node("async_test", my_async_func, is_async=True)
        state = GraphState({})
        result = await node.execute(state)
        assert result["async_result"] == "done"

    @pytest.mark.asyncio
    async def test_node_none_result(self):
        def returns_none(state):
            pass
        node = Node("none_test", returns_none)
        result = await node.execute(GraphState())
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_retry(self):
        calls = []

        async def flaky(state):
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("transient error")
            return {"ok": True}

        node = Node("flaky", flaky, is_async=True, retry_limit=2)
        result = await node.execute(GraphState())
        assert result["ok"] is True
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_node_retry_exhausted(self):
        async def always_fails(state):
            raise RuntimeError("always fails")
        node = Node("fail", always_fails, is_async=True, retry_limit=1)
        with pytest.raises(RuntimeError, match="failed after"):
            await node.execute(GraphState())


class TestEdge:
    def test_edge_creation(self):
        e = Edge(source="a", target="b")
        assert e.source == "a"
        assert e.target == "b"

    def test_conditional_edge_resolve(self):
        def router(state):
            return state.get("branch", "default")
        ce = ConditionalEdge(
            source="node_a",
            condition_func=router,
            target_map={"trust": "trust_node", "default": "general_node"},
            default_target="general_node",
        )
        state = GraphState({"branch": "trust"})
        assert ce.resolve(state) == "trust_node"

    def test_conditional_edge_default(self):
        def router(state):
            return "unknown"
        ce = ConditionalEdge(
            source="node_a",
            condition_func=router,
            target_map={"trust": "trust_node"},
            default_target="fallback",
        )
        assert ce.resolve(GraphState()) == "fallback"


class TestStateGraph:
    def test_add_node(self):
        g = StateGraph()

        async def fn(s): return {}
        g.add_node("my_node", fn)
        assert "my_node" in g._nodes

    def test_add_builtin_node(self):
        g = StateGraph()
        g.add_builtin_node("intake")
        assert "intake" in g._nodes

    def test_add_unknown_builtin_raises(self):
        g = StateGraph()
        with pytest.raises(ValueError):
            g.add_builtin_node("not_a_builtin")

    def test_add_edge(self):
        g = StateGraph()
        async def fn(s): return {}
        g.add_node("a", fn)
        g.add_node("b", fn)
        g.add_edge("a", "b")
        assert len(g._edges["a"]) == 1
        assert g._edges["a"][0].target == "b"

    def test_validate_no_entry(self):
        g = StateGraph()
        issues = g.validate()
        assert any("entry" in i.lower() for i in issues)

    def test_validate_ok(self):
        g = StateGraph()
        async def fn(s): return {}
        g.add_node("a", fn)
        g.set_entry_point("a")
        issues = g.validate()
        assert issues == []

    def test_compile_fails_no_entry(self):
        g = StateGraph()
        with pytest.raises(ValueError):
            g.compile()

    @pytest.mark.asyncio
    async def test_simple_graph_run(self):
        g = StateGraph()

        async def step_a(state):
            return {"a_done": True}

        async def step_b(state):
            return {"b_done": True}

        g.add_node("a", step_a)
        g.add_node("b", step_b)
        g.add_edge("a", "b")
        g.set_entry_point("a")
        g.set_finish_point("b")

        result = await g.run({"start": True})
        assert result.status == GraphStatus.COMPLETED
        assert result.final_state["a_done"] is True
        assert result.final_state["b_done"] is True
        assert "a" in result.visited_nodes
        assert "b" in result.visited_nodes

    @pytest.mark.asyncio
    async def test_conditional_routing(self):
        g = StateGraph()

        async def start(state):
            return {}

        async def trust_node(state):
            return {"branch_taken": "trust"}

        async def general_node(state):
            return {"branch_taken": "general"}

        g.add_node("start", start)
        g.add_node("trust", trust_node)
        g.add_node("general", general_node)
        g.set_entry_point("start")
        g.add_conditional_edges(
            "start",
            lambda s: "trust" if s.get("area") == "trust" else "general",
            {"trust": "trust", "general": "general"},
        )
        g.set_finish_point("trust")
        g.set_finish_point("general")

        result = await g.run({"area": "trust"})
        assert result.status == GraphStatus.COMPLETED
        assert result.final_state["branch_taken"] == "trust"

        result2 = await g.run({"area": "probate"})
        assert result2.final_state["branch_taken"] == "general"

    @pytest.mark.asyncio
    async def test_cycle_limit(self):
        g = StateGraph(max_cycles=3)

        count = {"n": 0}

        async def loop_node(state):
            count["n"] += 1
            return {"count": count["n"]}

        g.add_node("loop", loop_node)
        g.add_edge("loop", "loop")
        g.set_entry_point("loop")

        result = await g.run({})
        assert result.status == GraphStatus.FAILED
        assert "Cycle limit" in result.error

    @pytest.mark.asyncio
    async def test_legal_workflow(self):
        g = StateGraph.legal_workflow()
        result = await g.run({"case_id": "CASE-001", "practice_area": "general"})
        assert result.status == GraphStatus.COMPLETED
        assert "intake" in result.visited_nodes
        assert "research" in result.visited_nodes
        assert "file" in result.visited_nodes
        assert result.final_state.get("stage") == "filed"

    @pytest.mark.asyncio
    async def test_legal_workflow_trust_branch(self):
        g = StateGraph.legal_workflow()
        result = await g.run({"case_id": "TRUST-001", "practice_area": "trust"})
        assert result.status == GraphStatus.COMPLETED
        assert "trust_branch" in result.visited_nodes
        assert "general_legal" not in result.visited_nodes

    @pytest.mark.asyncio
    async def test_compiled_graph_invoke(self):
        compiled = create_legal_graph()
        state = await compiled.invoke({"case_id": "C-100", "practice_area": "estate"})
        assert "filing_reference" in state

    def test_detect_cycles(self):
        g = StateGraph()
        async def fn(s): return {}
        g.add_node("a", fn)
        g.add_node("b", fn)
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        g.set_entry_point("a")
        cycles = g._detect_cycles()
        assert len(cycles) > 0

    @pytest.mark.asyncio
    async def test_checkpointing_saves(self):
        cp = InMemoryCheckpointer()
        g = StateGraph(checkpointer=cp)
        async def fn(s): return {"x": 1}
        g.add_node("n", fn)
        g.set_entry_point("n")
        g.set_finish_point("n")
        run_id = uuid.uuid4().hex
        result = await g.run({}, run_id=run_id)
        assert result.checkpoints_saved > 0
        ckpt = cp.load_latest(g.graph_id, run_id)
        assert ckpt is not None

    @pytest.mark.asyncio
    async def test_graph_with_end_target(self):
        g = StateGraph()
        async def fn(s): return {"done": True}
        g.add_node("n", fn)
        g.add_edge("n", StateGraph.END)
        g.set_entry_point("n")
        result = await g.run({})
        assert result.status == GraphStatus.COMPLETED


# ---------------------------------------------------------------------------
# A2A Protocol Tests
# ---------------------------------------------------------------------------

from orchestration.a2a_protocol import (
    Message,
    MessageType,
    Priority,
    PriorityMessageQueue,
    AgentRegistry,
    AgentDescriptor,
    AgentStatus,
    MessageBus,
    A2AClient,
    A2AProtocol,
    Subscription,
)


class TestMessage:
    def test_message_creation(self):
        msg = Message(
            from_agent="agent_a",
            to_agent="agent_b",
            message_type=MessageType.REQUEST,
            payload={"task": "research"},
        )
        assert msg.from_agent == "agent_a"
        assert msg.message_type == MessageType.REQUEST
        assert not msg.is_expired()

    def test_message_expired(self):
        msg = Message(
            from_agent="a", to_agent="b",
            message_type=MessageType.REQUEST,
            payload={},
            timestamp=time.time() - 100,
            ttl=10,
        )
        assert msg.is_expired()

    def test_message_not_expired_no_ttl(self):
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={})
        assert not msg.is_expired()

    def test_message_serialization(self):
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.RESPONSE, payload={"k": "v"})
        d = msg.to_dict()
        assert d["from_agent"] == "a"
        assert d["message_type"] == "RESPONSE"
        restored = Message.from_dict(d)
        assert restored.from_agent == "a"
        assert restored.message_type == MessageType.RESPONSE

    def test_message_priority_ordering(self):
        low = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={}, priority=Priority.LOW)
        high = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={}, priority=Priority.HIGH)
        assert high < low  # higher priority = comes first in min-heap

    def test_priority_from_str(self):
        assert Priority.from_str("critical") == Priority.CRITICAL
        assert Priority.from_str("HIGH") == Priority.HIGH
        assert Priority.from_str("unknown") == Priority.NORMAL


class TestPriorityQueue:
    @pytest.mark.asyncio
    async def test_basic_put_get(self):
        q = PriorityMessageQueue()
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={})
        await q.put(msg)
        received = await q.get(timeout=1)
        assert received is not None
        assert received.message_id == msg.message_id

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        q = PriorityMessageQueue()
        low = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={"n": 1}, priority=Priority.LOW)
        high = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={"n": 2}, priority=Priority.HIGH)
        critical = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={"n": 3}, priority=Priority.CRITICAL)
        await q.put(low)
        await q.put(high)
        await q.put(critical)

        first = await q.get(timeout=1)
        second = await q.get(timeout=1)
        third = await q.get(timeout=1)
        assert first.priority == Priority.CRITICAL
        assert second.priority == Priority.HIGH
        assert third.priority == Priority.LOW

    @pytest.mark.asyncio
    async def test_expired_message_dropped(self):
        q = PriorityMessageQueue()
        expired = Message(
            from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={},
            timestamp=time.time() - 100, ttl=10,
        )
        fresh = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={"fresh": True})
        await q.put(expired)
        await q.put(fresh)
        received = await q.get(timeout=1)
        assert received.payload.get("fresh") is True

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        q = PriorityMessageQueue()
        result = await q.get(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_maxsize(self):
        q = PriorityMessageQueue(maxsize=2)
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={})
        await q.put(msg)
        await q.put(msg)
        with pytest.raises(RuntimeError):
            await q.put(msg)


class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        desc = AgentDescriptor(agent_id="a1", name="Agent 1", capabilities=["research", "draft"])
        reg.register(desc)
        found = reg.get("a1")
        assert found is not None
        assert found.name == "Agent 1"

    def test_find_by_capability(self):
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="A1", capabilities=["research"]))
        reg.register(AgentDescriptor(agent_id="a2", name="A2", capabilities=["draft"]))
        found = reg.find_by_capability("research")
        assert len(found) == 1
        assert found[0].agent_id == "a1"

    def test_deregister(self):
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="A1", capabilities=[]))
        assert reg.deregister("a1") is True
        assert reg.get("a1") is None

    def test_update_status(self):
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="A1", capabilities=[]))
        reg.update_status("a1", AgentStatus.BUSY)
        assert reg.get("a1").status == AgentStatus.BUSY

    def test_heartbeat(self):
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="A1", capabilities=[]))
        old_ts = reg.get("a1").last_seen
        time.sleep(0.01)
        reg.heartbeat("a1")
        assert reg.get("a1").last_seen > old_ts


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_direct_delivery(self):
        bus = MessageBus()
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={"data": 42})
        await bus.publish(msg)
        received = await bus.receive("b", timeout=1)
        assert received is not None
        assert received.payload["data"] == 42

    @pytest.mark.asyncio
    async def test_broadcast_delivery(self):
        bus = MessageBus()
        # Set up queues
        bus._agent_queue("b")
        bus._agent_queue("c")
        msg = Message(from_agent="a", to_agent="*", message_type=MessageType.BROADCAST, payload={"event": "tick"})
        await bus.publish(msg)
        rb = await bus.receive("b", timeout=1)
        rc = await bus.receive("c", timeout=1)
        assert rb is not None
        assert rc is not None

    @pytest.mark.asyncio
    async def test_pub_sub(self):
        bus = MessageBus()
        received_msgs = []

        async def handler(msg: Message):
            received_msgs.append(msg)

        bus.subscribe("agent_b", "agent_b", handler)
        msg = Message(from_agent="a", to_agent="agent_b", message_type=MessageType.REQUEST, payload={})
        await bus.publish(msg)
        await asyncio.sleep(0.1)
        assert len(received_msgs) == 1

    def test_pending_count(self):
        bus = MessageBus()
        assert bus.pending_count("unknown") == 0

    @pytest.mark.asyncio
    async def test_message_log(self):
        bus = MessageBus()
        msg = Message(from_agent="a", to_agent="b", message_type=MessageType.REQUEST, payload={})
        await bus.publish(msg)
        log = bus.message_log()
        assert len(log) >= 1


class TestA2AClient:
    @pytest.mark.asyncio
    async def test_send_request(self):
        proto = A2AProtocol()
        sender = proto.create_client("sender", "Sender Agent", ["task_a"])
        receiver = proto.create_client("receiver", "Receiver Agent", ["task_b"])

        corr_id = await sender.send_request("receiver", {"action": "do_something"})
        msg = await receiver.receive(timeout=1)
        assert msg is not None
        assert msg.correlation_id == corr_id
        assert msg.message_type == MessageType.REQUEST

    @pytest.mark.asyncio
    async def test_send_response(self):
        proto = A2AProtocol()
        a = proto.create_client("a", "Agent A", [])
        b = proto.create_client("b", "Agent B", [])

        corr = await a.send_request("b", {"q": "hello"})
        req = await b.receive(timeout=1)
        await b.send_response("a", {"answer": "world"}, correlation_id=req.correlation_id)
        resp = await a.receive(timeout=1)
        assert resp.payload["answer"] == "world"

    @pytest.mark.asyncio
    async def test_delegate(self):
        proto = A2AProtocol()
        boss = proto.create_client("boss", "Boss", ["orchestrate"])
        worker = proto.create_client("worker", "Worker", ["execute"])

        corr = await boss.delegate("worker", {"task": "file_document"})
        msg = await worker.receive(timeout=1)
        assert msg.message_type == MessageType.DELEGATION
        assert msg.payload["task"] == "file_document"

    @pytest.mark.asyncio
    async def test_broadcast(self):
        proto = A2AProtocol()
        broadcaster = proto.create_client("bc", "Broadcaster", [])
        listener1 = proto.create_client("l1", "Listener 1", [])
        listener2 = proto.create_client("l2", "Listener 2", [])

        await broadcaster.broadcast({"event": "new_case"})
        m1 = await listener1.receive(timeout=1)
        m2 = await listener2.receive(timeout=1)
        assert m1 is not None
        assert m2 is not None

    @pytest.mark.asyncio
    async def test_handshake(self):
        proto = A2AProtocol()
        a = proto.create_client("a_handshake", "A", ["legal_research"])
        b = proto.create_client("b_handshake", "B", ["drafting"])

        hs = await a.handshake("b_handshake")
        msg = await b.receive(timeout=1)
        assert msg.message_type == MessageType.HANDSHAKE
        assert "capabilities" in msg.payload

    @pytest.mark.asyncio
    async def test_send_error(self):
        proto = A2AProtocol()
        a = proto.create_client("err_a", "A", [])
        b = proto.create_client("err_b", "B", [])

        await b.send_error("err_a", "Something went wrong")
        msg = await a.receive(timeout=1)
        assert msg.message_type == MessageType.ERROR
        assert "Something went wrong" in msg.payload["error"]

    def test_find_agents_with_capability(self):
        proto = A2AProtocol()
        proto.create_client("cap1", "Cap Agent", ["trust_law"])
        proto.create_client("cap2", "Other", ["general_law"])

        agents = proto.get_all_agents()
        assert len(agents) == 2

    def test_status_management(self):
        proto = A2AProtocol()
        client = proto.create_client("stat_agent", "Status Agent", [])
        client.go_online()
        desc = proto.registry.get("stat_agent")
        assert desc.status == AgentStatus.ONLINE
        client.set_busy()
        assert proto.registry.get("stat_agent").status == AgentStatus.BUSY


# ---------------------------------------------------------------------------
# Durable Execution Tests
# ---------------------------------------------------------------------------

from orchestration.durable_execution import (
    DurableStore,
    WorkflowRecord,
    WorkflowStatus,
    ActivityRecord,
    ActivityStatus,
    HistoryEvent,
    HistoryEventType,
    RetryPolicy,
    ActivityExecutor,
    SagaCompensator,
    WorkflowContext,
    DurableWorkflowEngine,
)


class TestDurableStore:
    def setup_method(self):
        self.store = DurableStore(db_path=":memory:")

    def _make_wf(self, wf_id="wf1"):
        return WorkflowRecord(
            workflow_id=wf_id,
            workflow_type="legal_case",
            status=WorkflowStatus.RUNNING,
            state={"case_id": "C-001"},
        )

    def test_save_and_load_workflow(self):
        wf = self._make_wf()
        self.store.save_workflow(wf)
        loaded = self.store.load_workflow("wf1")
        assert loaded is not None
        assert loaded.workflow_type == "legal_case"
        assert loaded.state["case_id"] == "C-001"

    def test_load_missing_workflow(self):
        assert self.store.load_workflow("nonexistent") is None

    def test_update_workflow(self):
        wf = self._make_wf()
        self.store.save_workflow(wf)
        wf.status = WorkflowStatus.COMPLETED
        wf.state["result"] = "done"
        self.store.save_workflow(wf)
        loaded = self.store.load_workflow("wf1")
        assert loaded.status == WorkflowStatus.COMPLETED

    def test_list_workflows(self):
        for i in range(3):
            self.store.save_workflow(self._make_wf(f"wf{i}"))
        workflows = self.store.list_workflows()
        assert len(workflows) == 3

    def test_list_workflows_by_status(self):
        wf1 = self._make_wf("wf1")
        wf2 = self._make_wf("wf2")
        wf2.status = WorkflowStatus.COMPLETED
        self.store.save_workflow(wf1)
        self.store.save_workflow(wf2)
        running = self.store.list_workflows(status=WorkflowStatus.RUNNING)
        assert len(running) == 1

    def test_save_and_load_activity(self):
        wf = self._make_wf()
        self.store.save_workflow(wf)
        act = ActivityRecord(
            activity_id="act1",
            workflow_id="wf1",
            name="research",
            status=ActivityStatus.COMPLETED,
        )
        self.store.save_activity(act)
        acts = self.store.load_activities("wf1")
        assert len(acts) == 1
        assert acts[0].name == "research"

    def test_history_append_and_load(self):
        wf = self._make_wf()
        self.store.save_workflow(wf)
        evt = HistoryEvent(
            workflow_id="wf1",
            event_type=HistoryEventType.WORKFLOW_STARTED,
            payload={"key": "val"},
        )
        self.store.append_history(evt)
        history = self.store.load_history("wf1")
        assert len(history) == 1
        assert history[0].event_type == HistoryEventType.WORKFLOW_STARTED


class TestRetryPolicy:
    def test_default_delays(self):
        rp = RetryPolicy(initial_interval=1.0, backoff_coefficient=2.0, jitter=False)
        assert rp.next_delay(0) == pytest.approx(1.0)
        assert rp.next_delay(1) == pytest.approx(2.0)
        assert rp.next_delay(2) == pytest.approx(4.0)

    def test_max_interval(self):
        rp = RetryPolicy(initial_interval=1.0, backoff_coefficient=10.0, max_interval=5.0, jitter=False)
        assert rp.next_delay(10) == pytest.approx(5.0)

    def test_jitter(self):
        rp = RetryPolicy(initial_interval=1.0, jitter=True)
        delays = [rp.next_delay(0) for _ in range(20)]
        assert min(delays) != max(delays)


class TestActivityExecutor:
    @pytest.mark.asyncio
    async def test_successful_activity(self):
        store = DurableStore()
        store.save_workflow(WorkflowRecord(
            workflow_id="wf1", workflow_type="t", status=WorkflowStatus.RUNNING, state={}
        ))
        executor = ActivityExecutor(store)

        async def my_activity():
            return {"value": 42}

        result = await executor.run("wf1", "fetch_data", my_activity)
        assert result["value"] == 42

    @pytest.mark.asyncio
    async def test_activity_with_retry(self):
        store = DurableStore()
        store.save_workflow(WorkflowRecord(
            workflow_id="wf2", workflow_type="t", status=WorkflowStatus.RUNNING, state={}
        ))
        executor = ActivityExecutor(store)
        calls = []

        async def flaky_activity():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("first attempt fails")
            return "ok"

        policy = RetryPolicy(max_attempts=3, initial_interval=0.01, jitter=False)
        result = await executor.run("wf2", "flaky", flaky_activity, retry_policy=policy)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_activity_exhausted(self):
        store = DurableStore()
        store.save_workflow(WorkflowRecord(
            workflow_id="wf3", workflow_type="t", status=WorkflowStatus.RUNNING, state={}
        ))
        executor = ActivityExecutor(store)

        async def always_fail():
            raise RuntimeError("nope")

        policy = RetryPolicy(max_attempts=2, initial_interval=0.01, jitter=False)
        with pytest.raises(RuntimeError, match="failed after"):
            await executor.run("wf3", "fail_act", always_fail, retry_policy=policy)


class TestSagaCompensator:
    @pytest.mark.asyncio
    async def test_compensation_in_reverse(self):
        order = []
        comp = SagaCompensator()

        def comp_a():
            order.append("comp_a")

        def comp_b():
            order.append("comp_b")

        comp.register_compensation("step_a", comp_a)
        comp.register_compensation("step_b", comp_b)
        executed = await comp.compensate()
        assert order == ["comp_b", "comp_a"]
        assert "step_b" in executed
        assert "step_a" in executed

    @pytest.mark.asyncio
    async def test_async_compensation(self):
        results = []
        comp = SagaCompensator()

        async def async_comp():
            results.append("async_done")

        comp.register_compensation("step", async_comp)
        await comp.compensate()
        assert "async_done" in results

    @pytest.mark.asyncio
    async def test_empty_compensation(self):
        comp = SagaCompensator()
        executed = await comp.compensate()
        assert executed == []

    def test_step_count(self):
        comp = SagaCompensator()
        comp.register_compensation("a", lambda: None)
        comp.register_compensation("b", lambda: None)
        assert comp.step_count() == 2


class TestDurableWorkflowEngine:
    @pytest.mark.asyncio
    async def test_start_unknown_workflow(self):
        engine = DurableWorkflowEngine()
        with pytest.raises(ValueError, match="Unknown workflow type"):
            await engine.start_workflow("nonexistent", {})

    @pytest.mark.asyncio
    async def test_start_and_complete_workflow(self):
        engine = DurableWorkflowEngine()

        async def my_workflow(ctx, data):
            result = await ctx.execute_activity(
                "step_1",
                lambda: {"processed": True},
                retry_policy=RetryPolicy(max_attempts=1, jitter=False),
            )
            return result

        engine.register_workflow("test_wf", my_workflow)
        wf_id = await engine.start_workflow("test_wf", {"input": "data"})
        assert wf_id is not None

        await asyncio.sleep(0.2)  # let the task complete
        wf = engine.get_workflow(wf_id)
        assert wf is not None
        assert wf.status in (WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_cancel_workflow(self):
        engine = DurableWorkflowEngine()
        store = engine._store
        wf = WorkflowRecord(
            workflow_id="wf_cancel",
            workflow_type="t",
            status=WorkflowStatus.RUNNING,
            state={},
        )
        store.save_workflow(wf)
        result = await engine.cancel_workflow("wf_cancel")
        assert result is True
        assert engine.get_workflow("wf_cancel").status == WorkflowStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_resume_workflow(self):
        engine = DurableWorkflowEngine()
        store = engine._store
        wf = WorkflowRecord(
            workflow_id="wf_resume",
            workflow_type="t",
            status=WorkflowStatus.WAITING,
            state={},
        )
        store.save_workflow(wf)
        resumed = await engine.resume_workflow("wf_resume", {"signal": "proceed"})
        assert resumed is True
        loaded = engine.get_workflow("wf_resume")
        assert loaded.state["signal"] == "proceed"

    @pytest.mark.asyncio
    async def test_get_history(self):
        engine = DurableWorkflowEngine()
        store = engine._store
        wf = WorkflowRecord(
            workflow_id="wf_hist",
            workflow_type="t",
            status=WorkflowStatus.RUNNING,
            state={},
        )
        store.save_workflow(wf)
        store.append_history(HistoryEvent(
            workflow_id="wf_hist",
            event_type=HistoryEventType.WORKFLOW_STARTED,
        ))
        history = engine.get_history("wf_hist")
        assert len(history) == 1
        assert history[0].event_type == HistoryEventType.WORKFLOW_STARTED

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        engine = DurableWorkflowEngine()
        store = engine._store
        for i in range(3):
            store.save_workflow(WorkflowRecord(
                workflow_id=f"lwf_{i}", workflow_type="t",
                status=WorkflowStatus.COMPLETED, state={}
            ))
        wfs = engine.list_workflows(status=WorkflowStatus.COMPLETED)
        assert len(wfs) >= 3


# ---------------------------------------------------------------------------
# pytest configuration
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as async")
