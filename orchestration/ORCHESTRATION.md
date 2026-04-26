# SintraPrime-Unified Orchestration Layer

Multi-agent orchestration framework combining LangGraph-style stateful graphs,
A2A (Agent-to-Agent) messaging, and Temporal-inspired durable execution for
legal workflow automation.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  SintraPrime-Unified Orchestration                   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Orchestration API  (FastAPI)                │    │
│  │  POST /workflows/start    GET /workflows/{id}/status         │    │
│  │  POST /workflows/{id}/resume  GET /workflows/{id}/history    │    │
│  │  GET /agents/registry     POST /agents/message               │    │
│  │  POST /workflows/langgraph/run   GET /health                 │    │
│  └────────────┬──────────────────────┬───────────────┬──────────┘    │
│               │                      │               │               │
│  ┌────────────▼──────┐  ┌────────────▼─────┐  ┌────▼─────────────┐ │
│  │  LangGraph Engine │  │  A2A Protocol    │  │ Durable Execution│ │
│  │                   │  │                  │  │                  │ │
│  │  StateGraph       │  │  MessageBus      │  │  WorkflowEngine  │ │
│  │  ├─ Node          │  │  ├─ PubSub       │  │  ├─ SQLite Store │ │
│  │  ├─ Edge          │  │  ├─ PriorityQ    │  │  ├─ Checkpoints  │ │
│  │  ├─ ConditEdge    │  │  └─ DirectMsg    │  │  ├─ Retries      │ │
│  │  ├─ Checkpointer  │  │                  │  │  ├─ History/Log  │ │
│  │  └─ CompiledGraph │  │  AgentRegistry   │  │  └─ Saga/Rollbk  │ │
│  │                   │  │  ├─ Register     │  │                  │ │
│  │  Legal Workflow:  │  │  ├─ Discover     │  │  Activities:     │ │
│  │  intake           │  │  └─ Capability   │  │  ├─ Schedule     │ │
│  │  → research       │  │                  │  │  ├─ Execute      │ │
│  │  → [trust|general]│  │  A2AClient       │  │  ├─ Retry(exp)   │ │
│  │  → draft          │  │  ├─ Handshake    │  │  └─ Compensate   │ │
│  │  → review         │  │  ├─ Request/Resp │  │                  │ │
│  │  → file           │  │  ├─ Delegate     │  │  RetryPolicy     │ │
│  └───────────────────┘  │  └─ Broadcast    │  │  SagaCompensator │ │
│                         └──────────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. LangGraph Engine (`langgraph_engine.py`)

A `StateGraph` implementation compatible with LangGraph's mental model.

**Key Classes:**
- `GraphState` — dict-like state container with history and rollback
- `Node` — async/sync callable wrapper with retry and timeout
- `Edge` — directed connection between nodes
- `ConditionalEdge` — state-based routing
- `InMemoryCheckpointer` — saves `Checkpoint` after each node
- `StateGraph` — build, validate, and run directed graphs
- `CompiledGraph` — validated, ready-to-run graph

**Built-in Legal Workflow Nodes:**

| Node | Description |
|------|-------------|
| `intake` | Validate and ingest case information |
| `research` | Find relevant law and precedents |
| `trust_branch` | Trust/estate/probate-specific processing |
| `general_legal` | General legal matter handling |
| `draft` | Prepare legal documents |
| `review` | Attorney review and approval |
| `file` | File documents with court/registry |

**Usage:**

```python
from orchestration.langgraph_engine import create_legal_graph

graph = create_legal_graph()
state = await graph.invoke({
    "case_id": "C-2024-001",
    "practice_area": "trust",
})
print(state["filing_reference"])  # e.g. REF-A3F9C2B1
```

**Custom Graph:**

```python
from orchestration.langgraph_engine import StateGraph

g = StateGraph()

async def intake(state):
    return {"validated": True}

async def process(state):
    return {"result": "processed"}

g.add_node("intake", intake)
g.add_node("process", process)
g.add_edge("intake", "process")
g.set_entry_point("intake")
g.set_finish_point("process")

compiled = g.compile()
result = await compiled.invoke({"case_id": "C-001"})
```

---

### 2. A2A Protocol (`a2a_protocol.py`)

Standardized message envelope and in-memory message bus for agent coordination.

**Message Envelope:**

```json
{
  "message_id": "abc123",
  "from_agent": "research_agent",
  "to_agent": "drafting_agent",
  "message_type": "DELEGATION",
  "payload": {"task": "draft_trust_document", "case_id": "C-001"},
  "correlation_id": "xyz789",
  "timestamp": 1714123456.789,
  "priority": 2,
  "ttl": 300,
  "headers": {}
}
```

**Message Types:** `REQUEST`, `RESPONSE`, `BROADCAST`, `DELEGATION`, `RESULT`, `ERROR`, `HEARTBEAT`, `HANDSHAKE`, `CAPABILITY_ADV`

**Priority Levels:** `CRITICAL (3) > HIGH (2) > NORMAL (1) > LOW (0)`

**Usage:**

```python
from orchestration.a2a_protocol import A2AProtocol

proto = A2AProtocol()

orchestrator = proto.create_client("orchestrator", "Orchestrator", ["orchestrate"])
researcher = proto.create_client("researcher", "Research Agent", ["legal_research"])

# Delegate a task
corr_id = await orchestrator.delegate("researcher", {
    "task": "research_trust_law",
    "jurisdiction": "CA",
})

# Researcher picks up the task
msg = await researcher.receive(timeout=5.0)
print(f"Got task: {msg.payload['task']}")

# Respond
await researcher.send_response("orchestrator", {"research": "..."}, msg.correlation_id)
```

---

### 3. Durable Execution (`durable_execution.py`)

Temporal-inspired workflow persistence for long-running legal cases.

**Features:**
- **SQLite-backed state** — workflows survive process restarts
- **Resume** — continue interrupted cases with `engine.resume_workflow(id, signal)`
- **Retries** — exponential backoff with jitter per activity
- **Audit log** — every state change is recorded in history
- **Saga compensation** — automatic rollback on failure

**Usage:**

```python
from orchestration.durable_execution import DurableWorkflowEngine, RetryPolicy

engine = DurableWorkflowEngine(db_path="/data/sintra_workflows.db")

async def legal_case_workflow(ctx, data):
    # Each activity is retried independently
    research = await ctx.execute_activity(
        "legal_research",
        perform_research,
        args=(data["case_id"],),
        retry_policy=RetryPolicy(max_attempts=5, initial_interval=2.0),
        compensation_func=undo_research,  # called on failure
    )
    document = await ctx.execute_activity(
        "draft_document",
        create_document,
        args=(research,),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    return document

engine.register_workflow("legal_case", legal_case_workflow)

# Start (survives restart)
wf_id = await engine.start_workflow("legal_case", {"case_id": "C-2024-042"})

# Check progress (even weeks later)
wf = engine.get_workflow(wf_id)
print(f"Status: {wf.status}")

# View full audit trail
history = engine.get_history(wf_id)
for event in history:
    print(f"  [{event.event_type}] {event.activity_name} at {event.timestamp}")
```

---

### 4. Orchestration API (`orchestration_api.py`)

FastAPI router exposing all orchestration capabilities.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orchestration/workflows/start` | Start a durable workflow |
| GET | `/orchestration/workflows/{id}/status` | Get workflow status |
| POST | `/orchestration/workflows/{id}/resume` | Resume/signal a workflow |
| GET | `/orchestration/workflows/{id}/history` | Full audit history |
| GET | `/orchestration/agents/registry` | List all registered agents |
| POST | `/orchestration/agents/message` | Send an A2A message |
| POST | `/orchestration/workflows/langgraph/run` | Run LangGraph legal workflow |
| GET | `/orchestration/health` | Health check |

**Quick start:**

```python
from orchestration.orchestration_api import create_app

app = create_app()
# uvicorn orchestration.orchestration_api:app --reload
```

---

## Comparison to LangGraph and Temporal

| Feature | LangGraph | Temporal | SintraPrime-Unified |
|---------|-----------|---------|---------------------|
| Stateful graph | ✅ Native | ❌ | ✅ StateGraph |
| Conditional routing | ✅ | ❌ | ✅ ConditionalEdge |
| Checkpointing | ✅ | ✅ | ✅ In-memory + SQLite |
| Durable execution | ❌ | ✅ Native | ✅ DurableWorkflowEngine |
| Multi-agent comms | ❌ | ❌ | ✅ A2A Protocol |
| Priority messaging | ❌ | ❌ | ✅ CRITICAL/HIGH/NORMAL/LOW |
| Saga/compensation | ❌ | ✅ | ✅ SagaCompensator |
| Legal workflow builtins | ❌ | ❌ | ✅ intake→research→draft→review→file |
| REST API | ❌ | ✅ | ✅ FastAPI router |
| Pure Python | ✅ | ❌ | ✅ No external services |

---

## Running Tests

```bash
cd /path/to/SintraPrime-Unified
pip install pytest pytest-asyncio
python -m pytest orchestration/tests/ -v
```

Expected: **85+ tests passing**.

---

## Project Structure

```
orchestration/
├── __init__.py
├── langgraph_engine.py      # StateGraph + legal workflow nodes
├── a2a_protocol.py          # A2A messaging + agent registry
├── durable_execution.py     # SQLite-backed durable workflows
├── orchestration_api.py     # FastAPI REST endpoints
├── ORCHESTRATION.md         # This document
└── tests/
    ├── __init__.py
    └── test_orchestration.py  # 85+ tests
```
