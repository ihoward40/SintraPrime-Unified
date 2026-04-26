# SintraPrime Workflow Builder

> Visual, drag-and-drop legal workflow builder with a web-based terminal UI for SintraPrime-Unified.

---

## Overview

The Workflow Builder provides a complete system for designing, saving, running, and monitoring legal workflows through both a graphical interface and a web-based terminal.

### Architecture

```
workflow_builder/
├── workflow_engine.py      # Core DAG engine, node types, templates  (~450 lines)
├── workflow_schema.py      # React Flow / LangFlow JSON schema        (~250 lines)
├── web_tui.py              # WebSocket terminal server (VT100/ANSI)   (~380 lines)
├── workflow_api.py         # FastAPI router + WebSocket endpoint       (~280 lines)
├── static/
│   └── index.html          # Self-contained visual editor             (~400 lines)
├── tests/
│   └── test_workflow_builder.py  # 70+ pytest tests
└── WORKFLOW_BUILDER.md     # This file
```

---

## Components

### 1. Workflow Engine (`workflow_engine.py`)

The core engine manages workflow graphs as directed acyclic graphs (DAGs).

**Node Types:**

| Type | Icon | Description |
|---|---|---|
| `START` | ▶ | Entry point of a workflow |
| `END` | ⏹ | Terminal point of a workflow |
| `ACTION` | ⚡ | A discrete task or step |
| `DECISION` | ◆ | Conditional branching |
| `PARALLEL` | ⫶ | Executes multiple branches concurrently |
| `WAIT` | ⏳ | Pause until condition or timeout |
| `AGENT_CALL` | 🤖 | Invoke an AI agent |
| `HUMAN_REVIEW` | 👤 | Requires human sign-off |

**Edge Conditions:** `ALWAYS`, `ON_YES`, `ON_NO`, `ON_SUCCESS`, `ON_FAILURE`, `CONDITIONAL`

**Key classes:**
- `WorkflowNode` — a single node in the workflow
- `WorkflowEdge` — directed connection between nodes
- `WorkflowGraph` — the full DAG with validation, cycle detection, topological sort
- `WorkflowSerializer` — JSON save/load
- `WorkflowTemplateRegistry` — 21 built-in legal templates

**Usage:**
```python
from workflow_builder.workflow_engine import create_workflow, NodeType, WorkflowNode, WorkflowEdge

wf = create_workflow("Trust Creation", "Handles full trust document workflow")
start = WorkflowNode.create(NodeType.START, "Client Intake")
action = WorkflowNode.create(NodeType.ACTION, "Draft Documents")
end = WorkflowNode.create(NodeType.END, "Complete")
wf.add_node(start)
wf.add_node(action)
wf.add_node(end)
wf.add_edge(WorkflowEdge.create(start.id, action.id))
wf.add_edge(WorkflowEdge.create(action.id, end.id))

errors = wf.validate()
assert errors == []
```

### 2. Workflow Schema (`workflow_schema.py`)

Handles JSON interchange with visual editors.

**React Flow / LangFlow Compatible:**
```python
from workflow_builder.workflow_schema import ReactFlowConverter, export_workflow_to_react_flow

# Export to React Flow JSON
rf_json = export_workflow_to_react_flow(wf)

# Import back
from workflow_builder.workflow_schema import import_workflow_from_react_flow
restored_wf = import_workflow_from_react_flow(rf_json)

# Generate executable Python code
from workflow_builder.workflow_schema import WorkflowCodeGenerator
code = WorkflowCodeGenerator.generate(wf)
```

**Node JSON format:**
```json
{
  "id": "node_abc123",
  "type": "ACTION",
  "position": {"x": 200.0, "y": 150.0},
  "data": {
    "label": "Draft Trust Documents",
    "description": "AI drafts trust document templates",
    "config": {},
    "inputs": [],
    "outputs": []
  }
}
```

### 3. Web TUI (`web_tui.py`)

A WebSocket-backed terminal server with full VT100/ANSI support.

**Features:**
- Full color terminal (256-color ANSI)
- Tab completion for all commands
- Command history (↑/↓ arrows)
- Concurrent session management
- xterm.js compatible

**Commands:**
```
help                    Show help
workflow list           List all saved workflows
workflow get <id>       Show workflow details
workflow run <id>       Execute a workflow
workflow status <id>    Check execution status
workflow templates      List built-in templates
agent list              List available agents
agent status <id>       Check agent status
logs [--follow]         View system logs
status                  System health overview
version                 Show version info
echo <text>             Echo text
clear                   Clear screen
exit                    Disconnect
```

**Running the TUI server:**
```python
from workflow_builder.web_tui import create_tui_server

server = create_tui_server(host="0.0.0.0", port=8000)
```

Connect from the browser via xterm.js or the built-in UI tab.

### 4. Workflow API (`workflow_api.py`)

FastAPI router that mounts under `/workflows`.

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/workflows` | List all workflows |
| `POST` | `/workflows` | Create workflow from JSON |
| `GET` | `/workflows/templates` | List built-in templates |
| `GET` | `/workflows/{id}` | Get workflow definition |
| `PUT` | `/workflows/{id}` | Update workflow |
| `DELETE` | `/workflows/{id}` | Delete workflow |
| `POST` | `/workflows/{id}/run` | Execute workflow |
| `GET` | `/workflows/{id}/status` | Execution status |
| `GET` | `/workflows/{id}/export` | Export to React Flow JSON |
| `POST` | `/workflows/import` | Import from React Flow JSON |
| `WebSocket` | `/workflows/tui` | Web terminal connection |

**Mounting in your FastAPI app:**
```python
from fastapi import FastAPI
from workflow_builder.workflow_api import router

app = FastAPI()
app.include_router(router)
```

### 5. Visual Editor (`static/index.html`)

Self-contained HTML — no build step required. Serve it from any static file server.

**Features:**
- 🎨 Drag-and-drop node palette (8 node types)
- 🔗 Connect Mode for drawing edges
- 📋 21 built-in template cards with tag filtering
- 💻 Embedded terminal (xterm.js) with WebSocket connect
- 🔍 Node properties panel (label, description, timeout, retry)
- ⊞ Auto-layout and fit-to-screen
- ✓ Client-side DAG validation
- 💾 Save/load JSON, export Python code
- 🗑 Context menu (right-click on canvas)

**Serve it:**
```bash
cd workflow_builder/static
python -m http.server 3000
# Open http://localhost:3000
```

---

## Built-in Templates (21)

| Template | Tags |
|---|---|
| Trust Creation | trust, estate |
| Estate Planning | estate, planning |
| Debt Negotiation | debt, financial |
| Business Formation | corporate, formation |
| Court Filing | court, litigation |
| Contract Review | contract, review |
| Bankruptcy Filing | bankruptcy, financial |
| Real Estate Closing | real-estate |
| Immigration Application | immigration, visa |
| Employment Dispute | employment, litigation |
| IP Filing | ip, patent |
| Divorce Proceedings | family-law, divorce |
| Personal Injury Claim | personal-injury, litigation |
| Criminal Defense | criminal, defense |
| Power of Attorney | estate, poa |
| Landlord-Tenant Dispute | landlord-tenant |
| Non-Profit Formation | nonprofit, tax |
| Guardianship Petition | family-law, guardianship |
| Tax Dispute | tax, irs |
| M&A | corporate, ma |
| Compliance Audit | compliance, audit |

---

## Running Tests

```bash
cd /path/to/SintraPrime-Unified
pip install pytest pytest-asyncio fastapi httpx

# Run all tests
python -m pytest workflow_builder/tests/ -v

# Run specific test class
python -m pytest workflow_builder/tests/test_workflow_builder.py::TestWorkflowGraph -v

# Run with coverage
pip install pytest-cov
python -m pytest workflow_builder/tests/ --cov=workflow_builder --cov-report=html
```

---

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn websockets pytest pytest-asyncio

# Start the API server
uvicorn main:app --reload --port 8000

# Open the visual editor
open http://localhost:8000/static/index.html

# Connect the terminal at ws://localhost:8000/workflows/tui
```

---

## JSON Workflow Format

```json
{
  "workflow_id": "wf_trust_001",
  "name": "Trust Creation",
  "description": "End-to-end trust document workflow",
  "version": "1.0.0",
  "tags": ["trust", "estate"],
  "author": "SintraPrime",
  "nodes": [
    {
      "id": "node_start",
      "node_type": "START",
      "label": "Client Intake",
      "description": "Collect client information",
      "position": {"x": 100.0, "y": 200.0},
      "config": {},
      "timeout_seconds": null,
      "retry_count": 0
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "source_id": "node_start",
      "target_id": "node_action",
      "condition": "always",
      "label": ""
    }
  ]
}
```

---

## License

Part of SintraPrime-Unified. All rights reserved.
