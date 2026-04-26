"""
Comprehensive test suite for the SintraPrime-Unified observability layer.
Run with: python -m pytest observability/tests/ -v
"""

from __future__ import annotations

import json
import sys
import time
import os

# Make the observability package importable when running from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from observability.thought_debugger import (
    ThoughtDebugger,
    ThoughtStep,
    ThoughtStatus,
    ThoughtTrace,
    ParliamentHook,
)
from observability.time_travel import (
    TimeTravelDebugger,
    Snapshot,
    SnapshotStore,
    diff_snapshots,
)
from observability.tracer import (
    Span,
    SpanStatus,
    Trace,
    TraceContext,
    Tracer,
)
from observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    SintraMetrics,
)


# ===========================================================================
# ThoughtStep tests
# ===========================================================================

class TestThoughtStep:
    def test_create_basic(self):
        step = ThoughtStep.create("AgentA", "thinking", "search(q)", "results")
        assert step.agent_name == "AgentA"
        assert step.thought == "thinking"
        assert step.action == "search(q)"
        assert step.observation == "results"
        assert step.step_id
        assert step.timestamp > 0

    def test_step_id_unique(self):
        s1 = ThoughtStep.create("A", "t", "a", "o")
        s2 = ThoughtStep.create("A", "t", "a", "o")
        assert s1.step_id != s2.step_id

    def test_to_dict_has_required_fields(self):
        step = ThoughtStep.create("AgentB", "plan", "act", "obs")
        d = step.to_dict()
        for key in ("step_id", "agent_name", "thought", "action", "observation", "timestamp"):
            assert key in d

    def test_to_dict_includes_iso_timestamp(self):
        step = ThoughtStep.create("A", "t", "a", "o")
        d = step.to_dict()
        assert "timestamp_iso" in d
        assert "T" in d["timestamp_iso"]  # ISO format

    def test_roundtrip_dict(self):
        step = ThoughtStep.create("AgentC", "reason", "do_thing()", "done", tags=["legal"])
        d = step.to_dict()
        step2 = ThoughtStep.from_dict(d)
        assert step2.step_id == step.step_id
        assert step2.agent_name == step.agent_name
        assert step2.tags == step.tags

    def test_status_default(self):
        step = ThoughtStep.create("A", "t", "a", "o")
        assert step.status == ThoughtStatus.COMPLETE

    def test_with_metadata(self):
        step = ThoughtStep.create("A", "t", "a", "o", metadata={"priority": 1})
        assert step.metadata["priority"] == 1

    def test_with_parent(self):
        parent = ThoughtStep.create("A", "parent", "act", "obs")
        child = ThoughtStep.create("A", "child", "act2", "obs2", parent_step_id=parent.step_id)
        assert child.parent_step_id == parent.step_id


# ===========================================================================
# ThoughtTrace tests
# ===========================================================================

class TestThoughtTrace:
    def _make_trace(self) -> ThoughtTrace:
        trace = ThoughtTrace(session_name="test-session")
        trace.record("AgentA", "think1", "act1", "obs1")
        trace.record("AgentB", "think2", "act2", "obs2")
        return trace

    def test_trace_creation(self):
        trace = ThoughtTrace()
        assert trace.session_id
        assert len(trace) == 0

    def test_record_adds_step(self):
        trace = ThoughtTrace()
        step = trace.record("A", "t", "a", "o")
        assert len(trace) == 1
        assert trace.get_step(step.step_id) is step

    def test_steps_for_agent(self):
        trace = self._make_trace()
        a_steps = trace.steps_for_agent("AgentA")
        assert len(a_steps) == 1
        assert a_steps[0].agent_name == "AgentA"

    def test_root_steps(self):
        trace = ThoughtTrace()
        s1 = trace.record("A", "t", "a", "o")
        s2 = trace.record("B", "t2", "a2", "o2", parent_step_id=s1.step_id)
        roots = trace.root_steps()
        assert len(roots) == 1
        assert roots[0].step_id == s1.step_id

    def test_children_of(self):
        trace = ThoughtTrace()
        parent = trace.record("A", "parent", "a", "o")
        child = trace.record("A", "child", "a2", "o2", parent_step_id=parent.step_id)
        children = trace.children_of(parent.step_id)
        assert len(children) == 1
        assert children[0].step_id == child.step_id

    def test_render_tree_returns_string(self):
        trace = self._make_trace()
        tree = trace.render_tree()
        assert isinstance(tree, str)
        assert "AgentA" in tree
        assert "AgentB" in tree

    def test_render_tree_contains_session_info(self):
        trace = ThoughtTrace(session_name="my-session")
        trace.record("A", "thought", "action", "obs")
        tree = trace.render_tree()
        assert "my-session" in tree

    def test_replay_yields_all_steps(self):
        trace = self._make_trace()
        replayed = list(trace.replay())
        assert len(replayed) == 2

    def test_replay_from_specific_step(self):
        trace = ThoughtTrace()
        s1 = trace.record("A", "t1", "a1", "o1")
        time.sleep(0.01)
        s2 = trace.record("A", "t2", "a2", "o2")
        replayed = list(trace.replay_from(s2.step_id))
        assert len(replayed) == 1
        assert replayed[0].step_id == s2.step_id

    def test_to_json_roundtrip(self):
        trace = self._make_trace()
        json_str = trace.to_json()
        trace2 = ThoughtTrace.from_json(json_str)
        assert trace2.session_id == trace.session_id
        assert len(trace2) == len(trace)

    def test_to_markdown_contains_headings(self):
        trace = self._make_trace()
        md = trace.to_markdown()
        assert "# Thought Trace" in md
        assert "## Step 1" in md
        assert "## Step 2" in md

    def test_to_markdown_contains_thought_text(self):
        trace = ThoughtTrace()
        trace.record("A", "I should search the database", "db.query()", "results")
        md = trace.to_markdown()
        assert "I should search the database" in md

    def test_parliament_hook_fires(self):
        trace = ThoughtTrace()
        hook = ParliamentHook()
        trace.register_parliament_hook(hook)
        trace.record("A", "t", "a", "o")
        assert len(hook.received) == 1

    def test_parliament_hook_summary(self):
        trace = ThoughtTrace()
        hook = ParliamentHook()
        trace.register_parliament_hook(hook)
        trace.record("AgentA", "t", "a", "o")
        trace.record("AgentA", "t2", "a2", "o2")
        trace.record("AgentB", "t3", "a3", "o3")
        summary = hook.get_agent_summary()
        assert summary["AgentA"] == 2
        assert summary["AgentB"] == 1


# ===========================================================================
# ThoughtDebugger tests
# ===========================================================================

class TestThoughtDebugger:
    def test_create_trace(self):
        dbg = ThoughtDebugger()
        trace = dbg.create_trace("test")
        assert trace.session_name == "test"
        assert dbg.get_trace(trace.session_id) is trace

    def test_all_traces(self):
        dbg = ThoughtDebugger()
        dbg.create_trace("a")
        dbg.create_trace("b")
        assert len(dbg.all_traces()) == 2

    def test_remove_trace(self):
        dbg = ThoughtDebugger()
        trace = dbg.create_trace("x")
        dbg.remove_trace(trace.session_id)
        assert dbg.get_trace(trace.session_id) is None

    def test_session_context_manager(self):
        dbg = ThoughtDebugger()
        with dbg.session("ctx-test") as trace:
            trace.record("A", "t", "a", "o")
        assert len(trace) == 1


# ===========================================================================
# Snapshot & SnapshotStore tests
# ===========================================================================

class TestSnapshot:
    def test_create(self):
        snap = Snapshot.create("sess1", "AgentA", {"key": "val"}, label="test")
        assert snap.session_id == "sess1"
        assert snap.agent_name == "AgentA"
        assert snap.state == {"key": "val"}
        assert snap.label == "test"

    def test_state_is_deep_copied(self):
        state = {"nested": {"x": 1}}
        snap = Snapshot.create("s", "A", state)
        state["nested"]["x"] = 99
        assert snap.state["nested"]["x"] == 1  # original unchanged

    def test_to_dict_roundtrip(self):
        snap = Snapshot.create("s", "A", {"a": 1}, tags=["t1"])
        d = snap.to_dict()
        snap2 = Snapshot.from_dict(d)
        assert snap2.snapshot_id == snap.snapshot_id
        assert snap2.tags == snap.tags


class TestSnapshotStore:
    def _store(self) -> SnapshotStore:
        return SnapshotStore(db_path=":memory:")

    def test_save_and_get(self):
        store = self._store()
        snap = Snapshot.create("s", "A", {"x": 1})
        store.save(snap)
        retrieved = store.get(snap.snapshot_id)
        assert retrieved is not None
        assert retrieved.snapshot_id == snap.snapshot_id
        assert retrieved.state == {"x": 1}

    def test_list_for_session(self):
        store = self._store()
        for i in range(3):
            store.save(Snapshot.create("sess", "A", {"i": i}))
        snaps = store.list_for_session("sess")
        assert len(snaps) == 3

    def test_list_for_branch(self):
        store = self._store()
        s1 = Snapshot.create("sess", "A", {}, branch_name="main")
        s2 = Snapshot.create("sess", "A", {}, branch_name="alt")
        store.save(s1)
        store.save(s2)
        main = store.list_for_branch("main")
        alt = store.list_for_branch("alt")
        assert len(main) == 1
        assert len(alt) == 1

    def test_delete(self):
        store = self._store()
        snap = Snapshot.create("s", "A", {})
        store.save(snap)
        store.delete(snap.snapshot_id)
        assert store.get(snap.snapshot_id) is None

    def test_count(self):
        store = self._store()
        for _ in range(5):
            store.save(Snapshot.create("s", "A", {}))
        assert store.count() == 5

    def test_list_all(self):
        store = self._store()
        for _ in range(10):
            store.save(Snapshot.create("s", "A", {}))
        all_snaps = store.list_all(limit=5)
        assert len(all_snaps) == 5


# ===========================================================================
# diff_snapshots tests
# ===========================================================================

class TestDiffSnapshots:
    def test_no_diff(self):
        s1 = Snapshot.create("s", "A", {"x": 1})
        s2 = Snapshot.create("s", "A", {"x": 1})
        result = diff_snapshots(s1, s2)
        assert result["changes_count"] == 0

    def test_changed_value(self):
        s1 = Snapshot.create("s", "A", {"x": 1})
        s2 = Snapshot.create("s", "A", {"x": 2})
        result = diff_snapshots(s1, s2)
        assert result["changes_count"] == 1
        assert result["changes"][0]["kind"] == "changed"

    def test_added_key(self):
        s1 = Snapshot.create("s", "A", {})
        s2 = Snapshot.create("s", "A", {"new_key": "val"})
        result = diff_snapshots(s1, s2)
        assert result["summary"]["added"] == 1

    def test_removed_key(self):
        s1 = Snapshot.create("s", "A", {"old_key": "v"})
        s2 = Snapshot.create("s", "A", {})
        result = diff_snapshots(s1, s2)
        assert result["summary"]["removed"] == 1

    def test_nested_diff(self):
        s1 = Snapshot.create("s", "A", {"meta": {"version": 1}})
        s2 = Snapshot.create("s", "A", {"meta": {"version": 2}})
        result = diff_snapshots(s1, s2)
        assert result["changes_count"] == 1
        assert "meta.version" in result["changes"][0]["path"]


# ===========================================================================
# TimeTravelDebugger tests
# ===========================================================================

class TestTimeTravelDebugger:
    def _ttd(self) -> TimeTravelDebugger:
        return TimeTravelDebugger(db_path=":memory:")

    def test_start_session(self):
        ttd = self._ttd()
        sid = ttd.start_session("workflow-1")
        assert sid
        info = ttd.session_info(sid)
        assert info["name"] == "workflow-1"

    def test_checkpoint_creates_snapshot(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        snap = ttd.checkpoint(sid, "AgentA", {"step": 1}, label="step1")
        assert snap.snapshot_id
        assert snap.session_id == sid

    def test_rewind_returns_state(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        snap = ttd.checkpoint(sid, "A", {"data": "original"})
        state = ttd.rewind(snap.snapshot_id)
        assert state == {"data": "original"}

    def test_rewind_deep_copies(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        snap = ttd.checkpoint(sid, "A", {"nested": {"v": 1}})
        state = ttd.rewind(snap.snapshot_id)
        state["nested"]["v"] = 99
        state2 = ttd.rewind(snap.snapshot_id)
        assert state2["nested"]["v"] == 1

    def test_rewind_missing_raises(self):
        ttd = self._ttd()
        with pytest.raises(KeyError):
            ttd.rewind("nonexistent-id")

    def test_diff(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        s1 = ttd.checkpoint(sid, "A", {"v": 1})
        s2 = ttd.checkpoint(sid, "A", {"v": 2})
        diff = ttd.diff(s1.snapshot_id, s2.snapshot_id)
        assert diff["changes_count"] == 1

    def test_branch_creates_new_snapshot(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        s1 = ttd.checkpoint(sid, "A", {"path": "main"})
        branch_snap = ttd.branch(s1.snapshot_id, {"path": "alt"}, "alternative")
        assert branch_snap.branch_name == "alternative"
        assert branch_snap.parent_snapshot_id == s1.snapshot_id

    def test_list_branches(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        s1 = ttd.checkpoint(sid, "A", {})
        ttd.branch(s1.snapshot_id, {}, "branch-x")
        branches = ttd.list_branches(sid)
        assert "main" in branches
        assert "branch-x" in branches

    def test_history(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        for i in range(4):
            ttd.checkpoint(sid, "A", {"i": i})
        h = ttd.history(sid)
        assert len(h) == 4

    def test_rewind_callback_fires(self):
        ttd = self._ttd()
        fired = []
        ttd.register_rewind_callback(lambda snap: fired.append(snap.snapshot_id))
        sid = ttd.start_session()
        snap = ttd.checkpoint(sid, "A", {})
        ttd.rewind(snap.snapshot_id)
        assert len(fired) == 1

    def test_auto_checkpoint_context_manager(self):
        ttd = self._ttd()
        sid = ttd.start_session()
        state = {"phase": "init"}
        with ttd.auto_checkpoint(sid, "A", state, label="test"):
            state["phase"] = "running"
        h = ttd.history(sid)
        assert len(h) == 2
        labels = [s.label for s in h]
        assert any("before" in l for l in labels)
        assert any("after" in l for l in labels)

    def test_list_all_snapshots(self):
        ttd = self._ttd()
        for i in range(5):
            sid = ttd.start_session()
            ttd.checkpoint(sid, "A", {"i": i})
        all_snaps = ttd.list_all_snapshots()
        assert len(all_snaps) == 5


# ===========================================================================
# Tracer / Span tests
# ===========================================================================

class TestSpan:
    def test_finish_sets_end(self):
        span = Span("t1", "s1", "my-span", start=time.time())
        assert span.end is None
        span.finish()
        assert span.end is not None

    def test_duration_ms(self):
        start = time.time()
        span = Span("t1", "s1", "span", start=start, end=start + 0.5)
        assert abs(span.duration_ms - 500.0) < 1.0

    def test_set_tag(self):
        span = Span("t1", "s1", "span", start=time.time())
        span.set_tag("env", "test")
        assert span.tags["env"] == "test"

    def test_set_tags(self):
        span = Span("t1", "s1", "span", start=time.time())
        span.set_tags({"a": 1, "b": 2})
        assert span.tags["a"] == 1

    def test_log(self):
        span = Span("t1", "s1", "span", start=time.time())
        span.log("hello", level="debug", extra="data")
        assert len(span.logs) == 1
        assert span.logs[0]["message"] == "hello"
        assert span.logs[0]["level"] == "debug"

    def test_finish_with_error(self):
        span = Span("t1", "s1", "span", start=time.time())
        span.finish_with_error("oops")
        assert span.status == SpanStatus.ERROR
        assert span.status_message == "oops"

    def test_to_dict_roundtrip(self):
        span = Span("t1", "s1", "span", start=time.time())
        span.set_tag("x", 42)
        span.finish()
        d = span.to_dict()
        span2 = Span.from_dict(d)
        assert span2.span_id == span.span_id
        assert span2.tags["x"] == 42


class TestTrace:
    def test_add_and_get_span(self):
        trace = Trace()
        span = Span(trace.trace_id, "s1", "root", time.time())
        trace.add_span(span)
        assert trace.get_span("s1") is span

    def test_root_span(self):
        trace = Trace()
        root = Span(trace.trace_id, "r", "root", time.time())
        child = Span(trace.trace_id, "c", "child", time.time(), parent_span_id="r")
        trace.add_span(root)
        trace.add_span(child)
        assert trace.root_span() is root

    def test_children_of(self):
        trace = Trace()
        parent = Span(trace.trace_id, "p", "parent", time.time())
        child = Span(trace.trace_id, "c", "child", time.time(), parent_span_id="p")
        trace.add_span(parent)
        trace.add_span(child)
        children = trace.children_of("p")
        assert len(children) == 1

    def test_summary(self):
        trace = Trace(name="my-trace")
        span = Span(trace.trace_id, "s", "op", time.time())
        span.finish()
        trace.add_span(span)
        s = trace.summary()
        assert s["trace_id"] == trace.trace_id
        assert s["span_count"] == 1

    def test_error_spans(self):
        trace = Trace()
        span = Span(trace.trace_id, "s", "op", time.time())
        span.finish_with_error("boom")
        trace.add_span(span)
        assert len(trace.error_spans()) == 1

    def test_flame_graph_export(self):
        trace = Trace()
        span = Span(trace.trace_id, "s", "op", start=time.time(), end=time.time() + 0.1)
        trace.add_span(span)
        fg = trace.to_flame_graph()
        assert "traceEvents" in fg
        assert len(fg["traceEvents"]) == 1

    def test_to_json_roundtrip(self):
        trace = Trace(name="rt")
        span = Span(trace.trace_id, "s", "op", time.time())
        span.finish()
        trace.add_span(span)
        j = trace.to_json()
        trace2 = Trace.from_dict(json.loads(j))
        assert trace2.trace_id == trace.trace_id


class TestTraceContext:
    def test_to_and_from_headers(self):
        ctx = TraceContext(trace_id="abc-123", parent_span_id="span-456", baggage={"k": "v"})
        headers = ctx.to_headers()
        ctx2 = TraceContext.from_headers(headers)
        assert ctx2.trace_id == "abc-123"
        assert ctx2.parent_span_id == "span-456"
        assert ctx2.baggage["k"] == "v"

    def test_child_context(self):
        ctx = TraceContext(trace_id="t1", parent_span_id="p1")
        child = ctx.child_context("c1")
        assert child.trace_id == "t1"
        assert child.parent_span_id == "c1"


class TestTracer:
    def test_new_trace(self):
        tracer = Tracer("svc")
        trace = tracer.new_trace("test-trace")
        assert trace.trace_id
        assert tracer.get_trace(trace.trace_id) is trace

    def test_create_span(self):
        tracer = Tracer("svc")
        trace = tracer.new_trace()
        span = tracer.create_span(trace, "my-op")
        assert span.name == "my-op"
        assert span.tags["service"] == "svc"

    def test_start_span_context_manager_ok(self):
        tracer = Tracer("svc")
        trace = tracer.new_trace()
        with tracer.start_span(trace, "op") as span:
            span.set_tag("k", "v")
        assert span.status == SpanStatus.OK
        assert span.is_finished

    def test_start_span_context_manager_error(self):
        tracer = Tracer("svc")
        trace = tracer.new_trace()
        with pytest.raises(ValueError):
            with tracer.start_span(trace, "op") as span:
                raise ValueError("test error")
        assert span.status == SpanStatus.ERROR

    def test_start_trace_context_manager(self):
        tracer = Tracer("svc")
        with tracer.start_trace("workflow") as (trace, root_span):
            root_span.set_tag("wf", "legal")
        assert root_span.is_finished

    def test_aggregate(self):
        tracer = Tracer("svc")
        with tracer.start_trace("t1") as (trace, root):
            pass
        agg = tracer.aggregate()
        assert agg["trace_count"] == 1
        assert agg["service"] == "svc"

    def test_inject_and_extract_headers(self):
        tracer = Tracer("svc")
        trace = tracer.new_trace()
        span = tracer.create_span(trace, "op")
        headers = tracer.inject_headers(trace, span)
        ctx = tracer.extract_context(headers)
        assert ctx.trace_id == trace.trace_id
        assert ctx.parent_span_id == span.span_id


# ===========================================================================
# Metrics tests
# ===========================================================================

class TestCounter:
    def test_initial_value(self):
        c = Counter("my_counter")
        assert c.value == 0.0

    def test_inc(self):
        c = Counter("c")
        c.inc()
        c.inc(4)
        assert c.value == 5.0

    def test_negative_raises(self):
        c = Counter("c")
        with pytest.raises(ValueError):
            c.inc(-1)

    def test_reset(self):
        c = Counter("c")
        c.inc(10)
        c.reset()
        assert c.value == 0.0

    def test_prometheus_text(self):
        c = Counter("req_total", "Total requests")
        c.inc(7)
        text = c.prometheus_text()
        assert "# HELP req_total Total requests" in text
        assert "# TYPE req_total counter" in text
        assert "req_total 7.0" in text


class TestGauge:
    def test_set(self):
        g = Gauge("g")
        g.set(42.0)
        assert g.value == 42.0

    def test_inc_dec(self):
        g = Gauge("g")
        g.inc(5)
        g.dec(2)
        assert g.value == 3.0

    def test_prometheus_text(self):
        g = Gauge("active_agents", "Active agents")
        g.set(3)
        text = g.prometheus_text()
        assert "# TYPE active_agents gauge" in text
        assert "active_agents 3" in text


class TestHistogram:
    def test_observe(self):
        h = Histogram("latency", buckets=(1.0, 5.0, 10.0, float("inf")))
        h.observe(0.5)
        h.observe(3.0)
        h.observe(7.0)
        assert h.count == 3
        assert h.sum == pytest.approx(10.5)

    def test_bucket_counts(self):
        h = Histogram("h", buckets=(1.0, 5.0, float("inf")))
        h.observe(0.5)   # <= 1
        h.observe(3.0)   # <= 5
        h.observe(8.0)   # <= inf
        text = h.prometheus_text()
        assert 'le="1.0"' in text
        assert 'le="+Inf"' in text

    def test_percentile(self):
        h = Histogram("h", buckets=(10.0, 50.0, 100.0, float("inf")))
        for v in range(1, 101):
            h.observe(v)
        p50 = h.percentile(50)
        assert p50 is not None

    def test_prometheus_text_format(self):
        h = Histogram("rq_dur", "Request duration")
        h.observe(1.5)
        text = h.prometheus_text()
        assert "rq_dur_sum" in text
        assert "rq_dur_count" in text
        assert "rq_dur_bucket" in text


class TestMetricsRegistry:
    def test_register_and_get(self):
        reg = MetricsRegistry()
        c = Counter("my_c")
        reg.register(c)
        assert reg.get("my_c") is c

    def test_all_metrics(self):
        reg = MetricsRegistry()
        reg.register(Counter("c1"))
        reg.register(Gauge("g1"))
        assert len(reg.all_metrics()) == 2

    def test_prometheus_text_combines_metrics(self):
        reg = MetricsRegistry()
        reg.register(Counter("c1", "counter one"))
        reg.register(Gauge("g1", "gauge one"))
        text = reg.prometheus_text()
        assert "c1" in text
        assert "g1" in text


class TestSintraMetrics:
    def test_initialization(self):
        m = SintraMetrics()
        assert m.agent_calls_total.value == 0
        assert m.token_usage.value == 0

    def test_record_call(self):
        m = SintraMetrics()
        m.record_call(duration_ms=42.0, tokens=100, error=False)
        assert m.agent_calls_total.value == 1
        assert m.token_usage.value == 100
        assert m.agent_errors_total.value == 0

    def test_record_call_error(self):
        m = SintraMetrics()
        m.record_call(duration_ms=10.0, error=True)
        assert m.agent_errors_total.value == 1

    def test_error_rate(self):
        m = SintraMetrics()
        m.record_call(50.0)
        m.record_call(50.0, error=True)
        assert m.error_rate.value == pytest.approx(0.5)

    def test_prometheus_output_not_empty(self):
        m = SintraMetrics()
        m.record_call(10.0)
        output = m.prometheus_output()
        assert "agent_calls_total" in output
        assert "agent_latency_ms" in output

    def test_thought_steps_counter(self):
        m = SintraMetrics()
        m.thought_steps_total.inc()
        m.thought_steps_total.inc()
        assert m.thought_steps_total.value == 2

    def test_snapshots_counter(self):
        m = SintraMetrics()
        m.snapshots_total.inc(5)
        assert m.snapshots_total.value == 5
