"""LangGraph-compatible checkpointer adapter for DurableStore.

This module provides a bridge between StateGraph's checkpoint interface
and DurableStore's workflow persistence API, enabling file-backed workflow
state that survives process restarts.

Based on PR-0006A findings proving InMemoryCheckpointer loses state on restart.
"""

import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from .durable_execution import DurableStore, WorkflowRecord, WorkflowStatus


@dataclass
class Checkpoint:
    """Checkpoint data structure matching LangGraph expectations.
    
    Attributes:
        graph_id: Unique identifier for the workflow graph type
        run_id: Unique identifier for this specific workflow execution
        node_name: Current node in the workflow graph
        state: Current workflow state (arbitrary JSON-serializable dict)
        visited_counts: Track how many times each node has been visited
        timestamp: Unix timestamp when checkpoint was created
        metadata: Additional context (client_id, user_id, etc.)
    """
    graph_id: str
    run_id: str
    node_name: str
    state: Dict[str, Any]
    visited_counts: Dict[str, int]
    timestamp: float
    metadata: Dict[str, Any]


class DurableCheckpointer:
    """LangGraph-compatible checkpointer backed by DurableStore.
    
    Provides file-based persistence for StateGraph workflow checkpoints,
    enabling restart recovery and long-running workflow resumption.
    
    Example:
        >>> from orchestration.durable_execution import DurableStore
        >>> from orchestration.durable_checkpointer import DurableCheckpointer
        >>> 
        >>> store = DurableStore(db_path="workflows.db")
        >>> checkpointer = DurableCheckpointer(store)
        >>> 
        >>> # Save checkpoint
        >>> checkpoint = Checkpoint(
        ...     graph_id="credit-audit",
        ...     run_id="run_abc123",
        ...     node_name="analyze_tradelines",
        ...     state={"tradeline_index": 247},
        ...     visited_counts={"analyze_tradelines": 1},
        ...     timestamp=time.time(),
        ...     metadata={"client_id": "C-0001"}
        ... )
        >>> checkpointer.save(checkpoint)
        >>> 
        >>> # Later (even after process restart):
        >>> loaded = checkpointer.load("credit-audit", "run_abc123")
        >>> assert loaded.state["tradeline_index"] == 247
    
    Note:
        This replaces InMemoryCheckpointer as the default for StateGraph,
        providing durable persistence without requiring PostgreSQL.
    """
    
    def __init__(self, durable_store: DurableStore):
        """Initialize checkpointer with DurableStore backend.
        
        Args:
            durable_store: DurableStore instance for persistence
        """
        self.store = durable_store
    
    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to durable storage.
        
        Args:
            checkpoint: Checkpoint to persist
            
        Note:
            Creates or updates workflow record in DurableStore.
            Workflow ID is composite: {graph_id}:{run_id}
        """
        # Composite workflow ID for uniqueness
        workflow_id = f"{checkpoint.graph_id}:{checkpoint.run_id}"
        
        # Map checkpoint data to WorkflowRecord schema
        record = WorkflowRecord(
            workflow_id=workflow_id,
            workflow_type=checkpoint.graph_id,
            status=WorkflowStatus.RUNNING,  # Use enum, not string
            state={
                "node_name": checkpoint.node_name,
                "state": checkpoint.state,
                "visited_counts": checkpoint.visited_counts,
            },
            metadata=checkpoint.metadata,
        )
        
        # Persist to DurableStore
        self.store.save_workflow(record)
    
    def load(self, graph_id: str, run_id: str) -> Optional[Checkpoint]:
        """Load most recent checkpoint for given workflow run.
        
        Args:
            graph_id: Workflow graph identifier
            run_id: Specific execution run identifier
            
        Returns:
            Checkpoint if found, None otherwise
            
        Example:
            >>> checkpoint = checkpointer.load("credit-audit", "run_123")
            >>> if checkpoint:
            ...     print(f"Resume from node: {checkpoint.node_name}")
        """
        workflow_id = f"{graph_id}:{run_id}"
        
        # Retrieve workflow record from DurableStore
        record = self.store.load_workflow(workflow_id)
        if not record:
            return None
        
        # State and metadata are already dicts from WorkflowRecord
        state_data = record.state
        metadata = record.metadata
        
        # Reconstruct Checkpoint from WorkflowRecord
        return Checkpoint(
            graph_id=graph_id,
            run_id=run_id,
            node_name=state_data.get("node_name", ""),
            state=state_data.get("state", {}),
            visited_counts=state_data.get("visited_counts", {}),
            timestamp=record.updated_at,
            metadata=metadata,
        )
    
    def list_checkpoints(self, graph_id: str, run_id: str) -> List[Checkpoint]:
        """List all checkpoints for a workflow run (newest first).
        
        Args:
            graph_id: Workflow graph identifier
            run_id: Specific execution run identifier
            
        Returns:
            List of checkpoints (currently only latest checkpoint)
            
        Note:
            DurableStore currently keeps latest state only.
            Future enhancement: Keep checkpoint history in separate table.
        """
        checkpoint = self.load(graph_id, run_id)
        return [checkpoint] if checkpoint else []
    
    def delete(self, graph_id: str, run_id: str) -> bool:
        """Delete checkpoint for given workflow run.
        
        Args:
            graph_id: Workflow graph identifier
            run_id: Specific execution run identifier
            
        Returns:
            True if checkpoint was deleted, False if not found
        """
        workflow_id = f"{graph_id}:{run_id}"
        
        # Check if exists
        record = self.store.load_workflow(workflow_id)
        if not record:
            return False
        
        # Delete from DurableStore
        # Note: DurableStore may not have explicit delete method yet
        # This is a placeholder for future implementation
        # For now, mark as cancelled to hide from active workflows
        record.status = WorkflowStatus.CANCELLED
        record.completed_at = time.time()
        self.store.save_workflow(record)
        return True
    
    def mark_completed(self, graph_id: str, run_id: str) -> bool:
        """Mark workflow as completed (checkpoint no longer needed for resumption).
        
        Args:
            graph_id: Workflow graph identifier
            run_id: Specific execution run identifier
            
        Returns:
            True if marked completed, False if not found
        """
        workflow_id = f"{graph_id}:{run_id}"
        
        record = self.store.load_workflow(workflow_id)
        if not record:
            return False
        
        # Update status to completed
        record.status = WorkflowStatus.COMPLETED
        record.completed_at = time.time()
        self.store.save_workflow(record)
        
        return True
