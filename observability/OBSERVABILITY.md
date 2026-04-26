# SintraPrime-Unified — Observability Layer

> Comprehensive debugging and observability tools for the SintraPrime multi-agent parliament system.

---

## Table of Contents

1. [Overview](#overview)
2. [Thought Debugger](#thought-debugger)
3. [Time-Travel Debugger](#time-travel-debugger)
4. [Distributed Tracing](#distributed-tracing)
5. [Metrics Collector](#metrics-collector)
6. [Observability Dashboard API](#observability-dashboard-api)
7. [Running Tests](#running-tests)
8. [Architecture](#architecture)

---

## Overview

The observability layer provides four interoperable tools:

| Module | Purpose |
|---|---|
| `thought_debugger.py` | Capture and replay agent reasoning chains |
| `time_travel.py` | Snapshot state, rewind, diff, and branch |
| `tracer.py` | Distributed tracing across agent calls |
| `metrics.py` | Prometheus-compatible metrics collection |
| `observability_api.py` | FastAPI router exposing all tools over HTTP |

---

## Thought Debugger

### Basic Usage

```python
from observability.thought_debugger import ThoughtDebugger

debugger = ThoughtDebugger()

with debugger.session("legal-review-42") as trace:
    # Record each reasoning step
    step1 = trace.record(
        agent_name="LegalAgent",
        thought="I need to check the governing law clause",
        action="search_clause(type='governing_law')",
        observation="Found: 'This agreement is governed by English law'",
    )

    step2 = trace.record(
        agent_name="LegalAgent",
        thought="The clause is present. Now check for dispute resolution.",
        action="search_clause(type='dispute_resolution')",
        observation="Not found — this is a compliance gap",
        parent_step_id=step1.step_id,  # link to parent thought
    )

# Render as ASCII tree
print(trace.render_tree())

# Export as markdown report
print(trace.to_markdown())

# Export as JSON
print(trace.to_json())
```

### Replaying Thoughts

```python
# Step through reasoning at 0.5s intervals
for step in trace.replay(delay_s=0.5):
    print(f"[{step.agent_name}] {step.thought}")

# Replay from a specific step
for step in trace.replay_from(step2.step_id):
    print(step.action)
```

### Parliament Hooks

The thought debugger integrates with SintraPrime's parliament system via hooks:

```python
from observability.thought_debugger import ParliamentHook

hook = ParliamentHook(parliament_endpoint="http://parliament/api/steps")
trace.register_parliament_hook(hook)

# Every subsequent trace.record() call fires the hook automatically
trace.record("VoteAgent", "Cast vote", "vote(yes)", "Vote recorded")

# Inspect what was received
print(hook.get_agent_summary())
# {'LegalAgent': 2, 'VoteAgent': 1}
```

---

## Time-Travel Debugger

### Snapshotting State

```python
from observability.time_travel import TimeTravelDebugger

ttd = TimeTravelDebugger(db_path="sintra_snapshots.db")
session_id = ttd.start_session("legal-workflow-42")

# Capture state at each decision point
snap1 = ttd.checkpoint(
    session_id,
    agent_name="LegalAgent",
    state={"contract_version": 1, "clauses_reviewed": 0},
    label="before-review",
)

# ... agent processes contract ...

snap2 = ttd.checkpoint(
    session_id,
    agent_name="LegalAgent",
    state={"contract_version": 1, "clauses_reviewed": 12, "gaps": ["dispute_resolution"]},
    label="after-review",
)
```

### Rewinding a Stuck Workflow

Suppose the legal workflow gets stuck after clause 6. Rewind to an earlier snapshot:

```python
# Rewind to before-review state
state = ttd.rewind(snap1.snapshot_id)
print(state)
# {'contract_version': 1, 'clauses_reviewed': 0}

# Re-execute the agent with the rewound state
agent.run(initial_state=state)
```

### Diffing Snapshots

```python
diff = ttd.diff(snap1.snapshot_id, snap2.snapshot_id)
print(f"Changes: {diff['changes_count']}")
for change in diff['changes']:
    print(f"  {change['path']}: {change['old']} → {change['new']}")
```

### Branching for Alternative Decisions

```python
# Branch from snap1 to test a different decision path
branch_snap = ttd.branch(
    from_snapshot_id=snap1.snapshot_id,
    new_state={"contract_version": 2, "clauses_reviewed": 0},
    branch_name="v2-contract-test",
    label="start-v2-branch",
)

# List all branches in this session
print(ttd.list_branches(session_id))
# ['main', 'v2-contract-test']
```

### Auto-Checkpoint Context Manager

```python
state = {"phase": "init"}
with ttd.auto_checkpoint(session_id, "LegalAgent", state, label="clause-review"):
    # Snapshot taken automatically before and after this block
    state["phase"] = "reviewing"
    state["current_clause"] = 3
```

---

## Distributed Tracing

### Basic Tracing

```python
from observability.tracer import Tracer

tracer = Tracer(service_name="LegalAgent")

with tracer.start_trace("review-contract") as (trace, root_span):
    root_span.set_tag("contract_id", "42")
    root_span.set_tag("agent", "LegalAgent")

    with tracer.start_span(trace, "extract-clauses", parent_span_id=root_span.span_id) as span:
        span.set_tag("clause_count", 12)
        span.log("Starting clause extraction", level="info")

    with tracer.start_span(trace, "validate-clauses", parent_span_id=root_span.span_id) as span:
        span.set_tag("gaps_found", 1)
        span.log("Gap: missing dispute_resolution clause", level="warning")
```

### Propagating Trace Context Across Agents

```python
# Agent A — inject context into headers for downstream call
tracer_a = Tracer("AgentA")
with tracer_a.start_trace("cross-agent-workflow") as (trace, root_span):
    headers = tracer_a.inject_headers(trace, root_span)
    # headers = {"x-trace-id": "...", "x-parent-span-id": "..."}

    # Pass headers to Agent B (e.g., via HTTP or message queue)
    response = call_agent_b(payload=data, headers=headers)

# Agent B — extract context from incoming headers
tracer_b = Tracer("AgentB")
ctx = tracer_b.extract_context(incoming_headers)
trace_b = tracer_b.new_trace("agent-b-work", context=ctx)

with tracer_b.start_span(trace_b, "b-operation", parent_span_id=ctx.parent_span_id) as span:
    span.set_tag("agent", "AgentB")
```

### Flame Graph Export

```python
# Export for visualization in Chrome DevTools (chrome://tracing)
flame_json = trace.to_flame_graph_json()
with open("trace.json", "w") as f:
    f.write(flame_json)
# Open chrome://tracing and load trace.json
```

### Aggregation

```python
agg = tracer.aggregate()
print(f"Traces: {agg['trace_count']}")
print(f"Total spans: {agg['total_spans']}")
print(f"Errors: {agg['total_errors']}")
print(f"Avg latency: {agg['avg_span_duration_ms']:.1f}ms")
```

---

## Metrics Collector

### Built-in SintraPrime Metrics

```python
from observability.metrics import SintraMetrics

m = SintraMetrics()

# Record an agent call
m.record_call(duration_ms=123.4, tokens=512, error=False)

# Update individual metrics
m.active_agents.set(3)
m.thought_steps_total.inc()
m.snapshots_total.inc()

# Emit Prometheus-compatible metrics text
print(m.prometheus_output())
```

### Custom Metrics

```python
from observability.metrics import Counter, Gauge, Histogram, MetricsRegistry

registry = MetricsRegistry()

clause_reviews = registry.register(Counter("clause_reviews_total", "Total clauses reviewed"))
review_latency = registry.register(
    Histogram("clause_review_latency_ms", "Time to review each clause",
              buckets=(10, 50, 100, 500, 1000, float("inf")))
)
pending_reviews = registry.register(Gauge("pending_reviews", "Pending clause reviews"))

clause_reviews.inc()
review_latency.observe(87.3)
pending_reviews.set(5)

print(registry.prometheus_text())
```

---

## Observability Dashboard API

### Setup

```python
from observability.observability_api import create_observability_router, create_app

# Standalone dev server
app = create_app()

# Or attach the router to an existing FastAPI app
from fastapi import FastAPI
from observability.observability_api import create_observability_router

app = FastAPI()
router = create_observability_router()
app.include_router(router)
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/observability/traces` | List all traces with summaries |
| GET | `/observability/traces/{trace_id}` | Full trace tree |
| GET | `/observability/traces/{trace_id}/flame` | Chrome flame graph JSON |
| GET | `/observability/thoughts` | List thought sessions |
| GET | `/observability/thoughts/{session_id}` | Thought chain (json/markdown/tree) |
| POST | `/observability/thoughts/record` | Record a thought step |
| GET | `/observability/snapshots` | List all snapshots |
| POST | `/observability/debug/checkpoint` | Create a snapshot |
| POST | `/observability/debug/rewind` | Rewind to a snapshot |
| POST | `/observability/debug/diff` | Diff two snapshots |
| GET | `/observability/metrics` | Prometheus metrics text |
| GET | `/observability/health` | Health check |

### Example API Usage

```bash
# Get a thought chain as a markdown report
curl "http://localhost:8000/observability/thoughts/SESSION_ID?fmt=markdown"

# Rewind to a snapshot
curl -X POST http://localhost:8000/observability/debug/rewind \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id": "SNAP_ID"}'

# Diff two snapshots
curl -X POST http://localhost:8000/observability/debug/diff \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id_a": "SNAP_A", "snapshot_id_b": "SNAP_B"}'

# Prometheus metrics
curl http://localhost:8000/observability/metrics
```

---

## Running Tests

```bash
# From the repository root
cd SintraPrime-Unified
python -m pytest observability/tests/ -v

# With coverage
python -m pytest observability/tests/ -v --tb=short
```

All 80+ tests should pass with zero external dependencies (stdlib + pytest only).

---

## Architecture

```
observability/
├── __init__.py              # Public API exports
├── thought_debugger.py      # ThoughtStep, ThoughtTrace, ThoughtDebugger, ParliamentHook
├── time_travel.py           # Snapshot, SnapshotStore (SQLite), TimeTravelDebugger
├── tracer.py                # Span, Trace, TraceContext, Tracer
├── metrics.py               # Counter, Gauge, Histogram, MetricsRegistry, SintraMetrics
├── observability_api.py     # FastAPI router (optional FastAPI dependency)
├── OBSERVABILITY.md         # This file
└── tests/
    ├── __init__.py
    └── test_observability.py  # 80+ tests
```

### Design Principles

- **Pure Python** — no external observability dependencies (OpenTelemetry, Prometheus client, etc.)
- **SQLite storage** — snapshots persist across process restarts
- **Deep copy semantics** — snapshots never share mutable state with live agents
- **Thread-safe metrics** — all metric writes are protected by locks
- **FastAPI optional** — the API module degrades gracefully if FastAPI is not installed
- **Parliament-ready** — hook system allows zero-code integration with SintraPrime's voting/deliberation layer
