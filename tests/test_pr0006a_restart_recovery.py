"""
PR-0006A: Restart Recovery Tests
Verify whether workflow state survives process termination.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

# Import both checkpointer types
from orchestration.langgraph_engine import (
    StateGraph,
    GraphState,
    InMemoryCheckpointer,
    Checkpoint,
)
from orchestration.durable_execution import DurableStore, WorkflowRecord, WorkflowStatus


class TestInMemoryCheckpointerRecovery:
    """Test whether InMemoryCheckpointer survives restart"""

    def test_inmemory_checkpoint_lost_on_new_instance(self):
        """EXPECTED FAIL: InMemoryCheckpointer does not persist across instances"""
        
        # Instance 1: Save checkpoint
        cp1 = InMemoryCheckpointer()
        ckpt = Checkpoint(
            graph_id="test-graph",
            run_id="run-001",
            node_name="step-1",
            state={"tradeline_index": 247, "total": 500},
            visited_counts={"step-1": 1},
        )
        cp1.save(ckpt)
        
        # Verify saved in same instance
        loaded = cp1.load_latest("test-graph", "run-001")
        assert loaded is not None
        assert loaded.state["tradeline_index"] == 247
        
        # Instance 2: New checkpointer (simulates restart)
        cp2 = InMemoryCheckpointer()
        recovered = cp2.load_latest("test-graph", "run-001")
        
        # EXPECTED: None - checkpoint was lost
        assert recovered is None, "InMemoryCheckpointer LOST state after restart"


class TestDurableStoreRecovery:
    """Test whether DurableStore survives restart"""

    def test_durable_store_persists_across_instances(self):
        """EXPECTED PASS: DurableStore persists to SQLite file"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Instance 1: Save workflow state
            store1 = DurableStore(db_path=db_path)
            wf = WorkflowRecord(
                workflow_id="credit-audit-001",
                workflow_type="credit_command_center",
                status=WorkflowStatus.RUNNING,
                state={
                    "current_step": "tradeline_analysis",
                    "tradeline_index": 247,
                    "total_tradelines": 500,
                    "violations_found": 18,
                },
            )
            store1.save_workflow(wf)
            
            # Verify saved
            loaded = store1.load_workflow("credit-audit-001")
            assert loaded is not None
            assert loaded.state["tradeline_index"] == 247
            
            # Close connections before creating new instance
            del store1
            
            # Instance 2: New store pointing to same file (simulates restart)
            store2 = DurableStore(db_path=db_path)
            recovered = store2.load_workflow("credit-audit-001")
            
            # EXPECTED: Workflow state recovered
            assert recovered is not None, "DurableStore RECOVERED state after restart"
            assert recovered.state["tradeline_index"] == 247
            assert recovered.state["violations_found"] == 18
            assert recovered.status == WorkflowStatus.RUNNING
            
            # Close before cleanup
            del store2
            
        finally:
            # Small delay for Windows to release file locks
            time.sleep(0.1)
            if os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass  # Ignore cleanup errors


class TestDefaultCheckpointerUsage:
    """Test which checkpointer is actually used by default"""

    def test_stategraph_defaults_to_durable(self):
        """Verify StateGraph now uses DurableCheckpointer by default (PR-0006B)"""
        
        graph = StateGraph(graph_id="test-default")
        
        # After PR-0006B implementation, StateGraph defaults to DurableCheckpointer
        from orchestration.durable_checkpointer import DurableCheckpointer
        assert isinstance(graph.checkpointer, DurableCheckpointer), (
            "StateGraph should default to DurableCheckpointer after PR-0006B"
        )
        
        # Clean up
        if hasattr(graph.checkpointer, 'store'):
            graph.checkpointer.store.close()


def test_workflow_restart_scenario_simplified():
    """
    After PR-0006B: Verify StateGraph checkpoints now survive restart
    """
    
    # Create workflow with default checkpointer (now DurableCheckpointer)
    graph = StateGraph(graph_id="credit-audit-restart")
    
    # Save a checkpoint directly
    checkpoint = Checkpoint(
        graph_id="credit-audit-restart",
        run_id="run-001",
        node_name="tradeline_analysis",
        state={"tradeline_index": 247, "total": 500},
        visited_counts={"tradeline_analysis": 247},
    )
    graph.checkpointer.save(checkpoint)
    
    # Verify saved
    loaded = graph.checkpointer.load("credit-audit-restart", "run-001")
    assert loaded is not None
    assert loaded.state["tradeline_index"] == 247
    
    # Simulate restart: New graph instance
    graph_after_restart = StateGraph(graph_id="credit-audit-restart")
    recovered = graph_after_restart.checkpointer.load("credit-audit-restart", "run-001")
    
    # AFTER PR-0006B: Checkpoint SHOULD persist
    assert recovered is not None, (
        "✅ PR-0006B SUCCESS: Checkpoint should survive restart\n"
        "   Credit audit at tradeline 247/500 can resume from checkpoint"
    )
    assert recovered.state["tradeline_index"] == 247
    assert recovered.node_name == "tradeline_analysis"
    
    # Clean up
    if hasattr(graph.checkpointer, 'store'):
        graph.checkpointer.store.close()
    if hasattr(graph_after_restart.checkpointer, 'store'):
        graph_after_restart.checkpointer.store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
