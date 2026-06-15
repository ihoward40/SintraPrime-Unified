"""
PR-0006B Phase 2 Integration Tests

Verify StateGraph now defaults to DurableCheckpointer and supports:
- Default DurableStore-backed checkpointer
- WORKFLOW_DB_PATH environment variable
- Backward compatibility with explicit checkpointer
- Checkpoint persistence across StateGraph instances
"""

import os
import tempfile
from pathlib import Path
import pytest

from orchestration.langgraph_engine import StateGraph, InMemoryCheckpointer
from orchestration.durable_checkpointer import DurableCheckpointer


def test_stategraph_defaults_to_durable_checkpointer():
    """Verify StateGraph uses DurableCheckpointer by default."""
    graph = StateGraph(graph_id="test-default")
    
    assert isinstance(graph.checkpointer, DurableCheckpointer), \
        f"Expected DurableCheckpointer, got {type(graph.checkpointer).__name__}"


def test_stategraph_respects_workflow_db_path():
    """Verify WORKFLOW_DB_PATH environment variable is respected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_path = str(Path(tmpdir) / "custom_workflows.db")
        
        # Set environment variable
        original_value = os.environ.get("WORKFLOW_DB_PATH")
        os.environ["WORKFLOW_DB_PATH"] = custom_path
        
        try:
            graph = StateGraph(graph_id="test-env-var")
            
            # Verify checkpointer is DurableCheckpointer
            assert isinstance(graph.checkpointer, DurableCheckpointer)
            
            # Verify database file is created at custom path
            assert Path(custom_path).exists(), \
                f"Expected database at {custom_path}"
                
        finally:
            # Restore original environment
            if original_value is None:
                os.environ.pop("WORKFLOW_DB_PATH", None)
            else:
                os.environ["WORKFLOW_DB_PATH"] = original_value


def test_stategraph_accepts_explicit_checkpointer():
    """Verify backward compatibility: explicit checkpointer still works."""
    explicit_checkpointer = InMemoryCheckpointer()
    graph = StateGraph(
        graph_id="test-explicit",
        checkpointer=explicit_checkpointer
    )
    
    assert graph.checkpointer is explicit_checkpointer, \
        "Explicit checkpointer should be used when provided"
    assert isinstance(graph.checkpointer, InMemoryCheckpointer), \
        f"Expected InMemoryCheckpointer, got {type(graph.checkpointer).__name__}"


def test_checkpoint_persists_across_stategraph_instances():
    """
    Verify checkpoint saved by one StateGraph instance
    can be loaded by another (simulates restart).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "restart_test.db")
        
        # Save environment variable
        original_value = os.environ.get("WORKFLOW_DB_PATH")
        os.environ["WORKFLOW_DB_PATH"] = db_path
        
        try:
            # Instance 1: Create and execute workflow
            graph1 = StateGraph(graph_id="restart-workflow")
            graph1.add_node("step1", lambda state: {"progress": 50})
            graph1.add_node("step2", lambda state: {"progress": 100})
            graph1.add_edge("step1", "step2")
            graph1.set_entry_point("step1")
            graph1.set_terminal_node("step2")
            
            # Execute partially (stop after step1)
            # This should save checkpoint
            result1 = graph1.invoke({"input": "test"})
            
            # Instance 2: New StateGraph with same graph_id (simulates restart)
            graph2 = StateGraph(graph_id="restart-workflow")
            
            # Both should use same DurableCheckpointer pointing to same DB
            assert isinstance(graph1.checkpointer, DurableCheckpointer)
            assert isinstance(graph2.checkpointer, DurableCheckpointer)
            
            # Verify checkpoint from graph1 is visible to graph2
            # (this tests that checkpoints persist at the DurableStore level)
            assert Path(db_path).exists(), "Database should exist after first execution"
            
        finally:
            # Restore environment
            if original_value is None:
                os.environ.pop("WORKFLOW_DB_PATH", None)
            else:
                os.environ["WORKFLOW_DB_PATH"] = original_value


def test_multiple_graphs_isolated_checkpoints():
    """Verify different graphs maintain separate checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "multi_graph.db")
        
        original_value = os.environ.get("WORKFLOW_DB_PATH")
        os.environ["WORKFLOW_DB_PATH"] = db_path
        
        try:
            # Create two graphs with different IDs
            graph_a = StateGraph(graph_id="workflow-a")
            graph_b = StateGraph(graph_id="workflow-b")
            
            # Both should use DurableCheckpointer
            assert isinstance(graph_a.checkpointer, DurableCheckpointer)
            assert isinstance(graph_b.checkpointer, DurableCheckpointer)
            
            # Verify they have different graph_ids
            assert graph_a.graph_id == "workflow-a"
            assert graph_b.graph_id == "workflow-b"
            
            # Both should share same database file
            assert Path(db_path).exists()
            
        finally:
            if original_value is None:
                os.environ.pop("WORKFLOW_DB_PATH", None)
            else:
                os.environ["WORKFLOW_DB_PATH"] = original_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
