# PR-0006B: Wire DurableStore as Default Checkpointer

**Status:** Ready for Implementation  
**Based on:** PR-0006A Evidence-Based Findings  
**Risk Level:** LOW (single file change, backward compatible)  
**Estimated Effort:** 1-2 days  

---

## Objective

Enable workflow state persistence and restart recovery by wiring `DurableStore` into `StateGraph` as the default checkpointer.

---

## Success Criteria

### Must Have
- [ ] StateGraph defaults to DurableStore-backed checkpointer
- [ ] WORKFLOW_DB_PATH environment variable supported
- [ ] Backward compatibility: explicit checkpointer injection still works
- [ ] Integration test proves restart recovery (not just unit tests)
- [ ] All existing StateGraph tests pass
- [ ] Documentation updated

### Should Have
- [ ] Example showing how to override with custom checkpointer
- [ ] Migration guide for existing deployments
- [ ] Performance comparison: InMemory vs DurableStore

### Could Have
- [ ] PostgreSQL backend option for DurableStore
- [ ] Checkpoint cleanup/retention policy
- [ ] Monitoring/metrics for checkpoint operations

---

## Implementation Plan

### Phase 1: Create DurableStore Adapter (2-3 hours)

**File:** `orchestration/durable_checkpointer.py`

Create adapter class that bridges DurableStore's workflow persistence API to StateGraph's checkpoint interface.

```python
"""LangGraph-compatible checkpointer adapter for DurableStore."""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from .durable_execution import DurableStore, WorkflowRecord


@dataclass
class Checkpoint:
    """Checkpoint data structure matching LangGraph expectations."""
    graph_id: str
    run_id: str
    node_name: str
    state: Dict[str, Any]
    visited_counts: Dict[str, int]
    timestamp: float
    metadata: Dict[str, Any]


class DurableCheckpointer:
    """
    LangGraph-compatible checkpointer backed by DurableStore.
    
    Provides file-based persistence for StateGraph workflow checkpoints,
    enabling restart recovery and long-running workflow resumption.
    """
    
    def __init__(self, durable_store: DurableStore):
        self.store = durable_store
    
    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to durable storage."""
        # Map checkpoint to WorkflowRecord
        workflow_id = f"{checkpoint.graph_id}:{checkpoint.run_id}"
        
        record = WorkflowRecord(
            workflow_id=workflow_id,
            workflow_type=checkpoint.graph_id,
            status="running",
            state=json.dumps({
                "node_name": checkpoint.node_name,
                "state": checkpoint.state,
                "visited_counts": checkpoint.visited_counts,
            }),
            metadata=json.dumps(checkpoint.metadata),
        )
        
        self.store.save_workflow(record)
    
    def load(self, graph_id: str, run_id: str) -> Optional[Checkpoint]:
        """Load most recent checkpoint for given workflow run."""
        workflow_id = f"{graph_id}:{run_id}"
        
        record = self.store.get_workflow(workflow_id)
        if not record:
            return None
        
        state_data = json.loads(record.state)
        
        return Checkpoint(
            graph_id=graph_id,
            run_id=run_id,
            node_name=state_data["node_name"],
            state=state_data["state"],
            visited_counts=state_data["visited_counts"],
            timestamp=record.updated_at,
            metadata=json.loads(record.metadata),
        )
    
    def list_checkpoints(self, graph_id: str, run_id: str) -> list[Checkpoint]:
        """List all checkpoints for a workflow run (newest first)."""
        workflow_id = f"{graph_id}:{run_id}"
        
        # DurableStore currently keeps latest state only
        # Could extend to keep checkpoint history in separate table
        checkpoint = self.load(graph_id, run_id)
        return [checkpoint] if checkpoint else []
```

**Tests:** `tests/test_durable_checkpointer.py`

```python
"""Tests for DurableCheckpointer adapter."""

import pytest
import tempfile
from pathlib import Path
from orchestration.durable_checkpointer import DurableCheckpointer, Checkpoint
from orchestration.durable_execution import DurableStore


def test_checkpoint_save_and_load():
    """Verify checkpoint can be saved and loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_checkpoints.db"
        store = DurableStore(db_path=str(db_path))
        checkpointer = DurableCheckpointer(store)
        
        # Create checkpoint
        checkpoint = Checkpoint(
            graph_id="credit-audit",
            run_id="run_abc123",
            node_name="analyze_tradelines",
            state={"tradeline_index": 247, "violations_found": 12},
            visited_counts={"analyze_tradelines": 1},
            timestamp=1234567890.0,
            metadata={"client_id": "C-0001"},
        )
        
        # Save
        checkpointer.save(checkpoint)
        
        # Load in new checkpointer instance (simulates restart)
        store2 = DurableStore(db_path=str(db_path))
        checkpointer2 = DurableCheckpointer(store2)
        
        loaded = checkpointer2.load("credit-audit", "run_abc123")
        
        assert loaded is not None
        assert loaded.graph_id == "credit-audit"
        assert loaded.run_id == "run_abc123"
        assert loaded.node_name == "analyze_tradelines"
        assert loaded.state["tradeline_index"] == 247
        assert loaded.state["violations_found"] == 12


def test_checkpoint_not_found():
    """Verify load returns None for nonexistent checkpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_checkpoints.db"
        store = DurableStore(db_path=str(db_path))
        checkpointer = DurableCheckpointer(store)
        
        loaded = checkpointer.load("nonexistent-graph", "nonexistent-run")
        
        assert loaded is None


def test_checkpoint_update():
    """Verify checkpoint can be updated with new state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_checkpoints.db"
        store = DurableStore(db_path=str(db_path))
        checkpointer = DurableCheckpointer(store)
        
        # Save initial checkpoint
        checkpoint1 = Checkpoint(
            graph_id="workflow-1",
            run_id="run-1",
            node_name="step-1",
            state={"progress": 50},
            visited_counts={"step-1": 1},
            timestamp=1000.0,
            metadata={},
        )
        checkpointer.save(checkpoint1)
        
        # Update checkpoint
        checkpoint2 = Checkpoint(
            graph_id="workflow-1",
            run_id="run-1",
            node_name="step-2",
            state={"progress": 100},
            visited_counts={"step-1": 1, "step-2": 1},
            timestamp=2000.0,
            metadata={},
        )
        checkpointer.save(checkpoint2)
        
        # Load should return latest state
        loaded = checkpointer.load("workflow-1", "run-1")
        
        assert loaded.node_name == "step-2"
        assert loaded.state["progress"] == 100
```

---

### Phase 2: Update StateGraph Default (1 hour)

**File:** `orchestration/langgraph_engine.py`

**Changes:**

1. Import DurableCheckpointer
2. Remove InMemoryCheckpointer type hint
3. Default to DurableStore-backed checkpointer
4. Support WORKFLOW_DB_PATH environment variable

```python
import os
from .durable_execution import DurableStore
from .durable_checkpointer import DurableCheckpointer


class StateGraph:
    def __init__(
        self,
        graph_id: Optional[str] = None,
        checkpointer = None,  # Removed type hint to support both types
        max_cycles: int = MAX_CYCLE_LIMIT,
    ) -> None:
        self.graph_id = graph_id or f"graph_{uuid.uuid4().hex[:8]}"
        
        # Default to DurableStore-backed persistence
        if checkpointer is None:
            db_path = os.environ.get("WORKFLOW_DB_PATH", "workflows.db")
            durable_store = DurableStore(db_path=db_path)
            checkpointer = DurableCheckpointer(durable_store)
        
        self.checkpointer = checkpointer
        # ... rest of __init__
```

**Backward Compatibility:**
- Explicit `checkpointer` parameter still works
- Existing code injecting InMemoryCheckpointer continues working
- New code gets durable persistence by default

---

### Phase 3: Integration Tests (3-4 hours)

**File:** `tests/e2e/test_restart_recovery.py`

Create **process-level** restart simulation (not just unit test).

```python
"""End-to-end restart recovery tests."""

import subprocess
import tempfile
import json
from pathlib import Path
import pytest


def test_workflow_survives_process_restart():
    """
    Verify workflow state persists across actual process restart.
    
    Simulates:
    1. Start workflow, execute partway through
    2. Kill process (simulating crash)
    3. Restart process
    4. Verify workflow resumes from checkpoint
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "restart_test.db"
        
        # Phase 1: Create workflow and execute partially
        script1 = f"""
import sys
import os
os.environ["WORKFLOW_DB_PATH"] = "{db_path}"

from orchestration.langgraph_engine import StateGraph

# Create workflow
graph = StateGraph(graph_id="restart-test")

# Add nodes
graph.add_node("step-1", lambda state: {{"progress": 33}})
graph.add_node("step-2", lambda state: {{"progress": 66}})
graph.add_node("step-3", lambda state: {{"progress": 100}})

# Execute partway (stop after step-1)
result = graph.execute({{"input": "test"}}, stop_at="step-2")

# Write result to file for verification
with open("{tmpdir}/phase1_result.json", "w") as f:
    json.dump(result, f)

sys.exit(0)
"""
        
        # Run phase 1
        result1 = subprocess.run(
            ["python", "-c", script1],
            capture_output=True,
            text=True,
        )
        assert result1.returncode == 0, f"Phase 1 failed: {result1.stderr}"
        
        # Verify checkpoint was saved
        assert db_path.exists(), "Workflow database not created"
        
        # Phase 2: Restart and resume
        script2 = f"""
import sys
import os
import json
os.environ["WORKFLOW_DB_PATH"] = "{db_path}"

from orchestration.langgraph_engine import StateGraph

# Recreate graph (simulates process restart)
graph = StateGraph(graph_id="restart-test")

# Graph should load checkpoint and resume
result = graph.resume()

# Verify resumed state
with open("{tmpdir}/phase2_result.json", "w") as f:
    json.dump(result, f)

# Verify progress was preserved
assert result["progress"] in [33, 66, 100], f"Unexpected progress: {{result}}"

sys.exit(0)
"""
        
        # Run phase 2 (different process)
        result2 = subprocess.run(
            ["python", "-c", script2],
            capture_output=True,
            text=True,
        )
        assert result2.returncode == 0, f"Phase 2 failed: {result2.stderr}"
        
        # Verify results
        phase1_result = json.loads((Path(tmpdir) / "phase1_result.json").read_text())
        phase2_result = json.loads((Path(tmpdir) / "phase2_result.json").read_text())
        
        # Workflow should have preserved state
        assert phase2_result["progress"] >= phase1_result["progress"]


def test_multiple_workflows_isolated():
    """Verify multiple workflows maintain separate checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "multi_workflow.db"
        os.environ["WORKFLOW_DB_PATH"] = str(db_path)
        
        from orchestration.langgraph_engine import StateGraph
        
        # Create two separate workflows
        graph1 = StateGraph(graph_id="workflow-a")
        graph2 = StateGraph(graph_id="workflow-b")
        
        # Execute both partway
        # ... (test logic)
        
        # Verify checkpoints are isolated
        # ... (verification logic)
```

---

### Phase 4: Documentation (1 hour)

**Update:** `docs/architecture/workflow-persistence.md`

```markdown
# Workflow Persistence

## Overview

SintraPrime-Unified workflows use **DurableStore** for persistent checkpointing,
enabling restart recovery and long-running workflow resumption.

## Default Behavior

As of PR-0006B, `StateGraph` defaults to file-backed persistence:

```python
from orchestration.langgraph_engine import StateGraph

# Automatically uses DurableStore with workflows.db
graph = StateGraph(graph_id="my-workflow")
```

## Configuration

Set `WORKFLOW_DB_PATH` environment variable to customize database location:

```bash
export WORKFLOW_DB_PATH=/var/lib/sintra/workflows.db
```

## Restart Recovery

Workflows automatically save checkpoints at each node execution.

If the process crashes:

1. Checkpoint remains in workflows.db
2. On restart, create StateGraph with same graph_id
3. Call `graph.resume()` to continue from last checkpoint

```python
# After crash/restart
graph = StateGraph(graph_id="original-workflow-id")
result = graph.resume()  # Continues from last checkpoint
```

## Custom Checkpointer

For advanced use cases, inject custom checkpointer:

```python
from orchestration.langgraph_engine import StateGraph, InMemoryCheckpointer

# Explicitly use in-memory (not recommended for production)
graph = StateGraph(
    graph_id="ephemeral-workflow",
    checkpointer=InMemoryCheckpointer()  # State lost on restart
)
```

## Migration from InMemoryCheckpointer

Existing code using explicit `InMemoryCheckpointer()` continues working.

To enable persistence, remove the explicit checkpointer:

**Before:**
```python
graph = StateGraph(checkpointer=InMemoryCheckpointer())
```

**After:**
```python
graph = StateGraph()  # Uses DurableStore by default
```

## Production Deployment

For production:

1. Set `WORKFLOW_DB_PATH` to persistent volume
2. Configure backup/restore for workflows.db
3. Monitor checkpoint save frequency
4. Set retention policy for completed workflows

Example Docker Compose:

```yaml
services:
  orchestrator:
    environment:
      WORKFLOW_DB_PATH: /data/workflows.db
    volumes:
      - workflow-data:/data
```

## Future: PostgreSQL Backend

Future enhancement will support PostgreSQL:

```python
# Future API (not yet implemented)
from orchestration.durable_checkpointer import PostgresCheckpointer

graph = StateGraph(
    checkpointer=PostgresCheckpointer(connection_pool=pg_pool)
)
```
```

---

## Testing Strategy

### Unit Tests
- [ ] DurableCheckpointer save/load
- [ ] DurableCheckpointer handles missing checkpoints
- [ ] DurableCheckpointer updates existing checkpoints
- [ ] StateGraph uses DurableStore by default
- [ ] StateGraph respects WORKFLOW_DB_PATH environment variable
- [ ] StateGraph accepts explicit checkpointer override

### Integration Tests
- [ ] Workflow state survives process restart (subprocess test)
- [ ] Multiple workflows maintain isolated checkpoints
- [ ] Large state objects checkpoint correctly
- [ ] Checkpoint timestamps are accurate
- [ ] Resume from checkpoint continues execution

### Regression Tests
- [ ] Existing StateGraph tests pass (no breaking changes)
- [ ] Credit Command Center workflows continue working
- [ ] Evidence Command Center workflows continue working

---

## Hard Constraints

### MUST NOT
- ❌ Modify portal.messages schema
- ❌ Break existing StateGraph API
- ❌ Require PostgreSQL for basic operation
- ❌ Lose backward compatibility with explicit checkpointers

### MUST
- ✅ Default to DurableStore-backed persistence
- ✅ Support WORKFLOW_DB_PATH environment variable
- ✅ Maintain backward compatibility
- ✅ Pass all existing tests
- ✅ Add integration test proving restart recovery

---

## Rollout Plan

### Phase 1: Development (This PR)
- Implement DurableCheckpointer adapter
- Wire into StateGraph as default
- Add tests
- Update documentation

### Phase 2: Staging Validation
- Deploy to staging environment
- Run smoke tests
- Monitor checkpoint save frequency
- Verify database growth is reasonable

### Phase 3: Production Deployment
- Set WORKFLOW_DB_PATH to persistent volume
- Configure backups
- Deploy with feature flag (if needed)
- Monitor for 48 hours

### Phase 4: Cleanup
- Remove InMemoryCheckpointer from default code paths
- Add deprecation notice for explicit InMemoryCheckpointer usage
- Create migration guide for teams using InMemoryCheckpointer

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Performance regression | Benchmark checkpoint save time, add metrics |
| Database file growth | Monitor size, add cleanup policy for completed workflows |
| Breaking existing workflows | Maintain backward compatibility, add regression tests |
| Lost checkpoints | Add database backup strategy, test recovery |

---

## Success Metrics

### Technical
- All tests pass (unit + integration + regression)
- Restart recovery test passes
- Zero breaking changes to existing API
- Documentation complete

### Operational
- Workflow restart recovery works in staging
- Database growth is predictable
- No performance degradation
- Monitoring shows checkpoint saves succeeding

---

## Timeline

**Day 1:**
- Morning: Implement DurableCheckpointer adapter
- Afternoon: Add unit tests, verify adapter works

**Day 2:**
- Morning: Wire into StateGraph, update defaults
- Afternoon: Add integration tests (restart recovery)

**Day 3 (if needed):**
- Morning: Update documentation
- Afternoon: Code review, final testing

**Total Estimate:** 1-2 days

---

## Commit Strategy

1. `feat(orchestration): add DurableCheckpointer adapter`
   - Create orchestration/durable_checkpointer.py
   - Add tests/test_durable_checkpointer.py

2. `feat(orchestration): wire DurableStore as default StateGraph checkpointer`
   - Modify orchestration/langgraph_engine.py
   - Add WORKFLOW_DB_PATH support

3. `test(e2e): add restart recovery integration tests`
   - Create tests/e2e/test_restart_recovery.py

4. `docs(architecture): document workflow persistence and restart recovery`
   - Update docs/architecture/workflow-persistence.md

---

## Approval Checklist

Before merging PR-0006B:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All regression tests pass (existing StateGraph tests)
- [ ] Restart recovery test proves checkpoint survival
- [ ] Documentation updated
- [ ] Code review approved
- [ ] No breaking changes to existing API
- [ ] WORKFLOW_DB_PATH environment variable works
- [ ] Backward compatibility verified (explicit checkpointer still works)

---

## Related PRs

- **PR-0006A:** Event Stream Feasibility Review (Evidence)
- **PR-0006C (Future):** PostgreSQL backend for DurableStore
- **PR-0006D (Future):** Checkpoint cleanup/retention policies
- **PR-0006E (Future):** Workflow monitoring and metrics

---

**Status:** Ready for implementation  
**Blocked by:** None  
**Blocks:** Evidence Command Center production deployment  
