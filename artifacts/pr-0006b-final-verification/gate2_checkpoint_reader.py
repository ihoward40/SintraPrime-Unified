"""
Gate 2: Checkpoint Reader - Recovers checkpoint in fresh process
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestration.durable_execution import DurableStore
from orchestration.durable_checkpointer import DurableCheckpointer


def main():
    db_path = Path(__file__).parent / "gate2_test.db"
    
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", flush=True)
        sys.exit(1)
    
    # Create DurableStore and DurableCheckpointer
    store = DurableStore(str(db_path))
    checkpointer = DurableCheckpointer(store)
    
    # Recover checkpoint using same graph_id and run_id
    loaded = checkpointer.load("gate2-test-graph", "gate2-run-001")
    
    if loaded is None:
        print("ERROR: No checkpoint found", flush=True)
        sys.exit(1)
    
    # Validate recovered checkpoint
    assert loaded.node_name == "test-node", f"Expected node test-node, got {loaded.node_name}"
    assert loaded.state["test_key"] == "test_value", "State mismatch"
    assert "writer_pid" in loaded.state, "Writer PID not in state"
    assert loaded.metadata["source"] == "gate2", f"Expected source gate2, got {loaded.metadata['source']}"
    assert loaded.metadata["step"] == 1, f"Expected step 1, got {loaded.metadata['step']}"
    assert loaded.visited_counts["test-node"] == 1, "Visited counts mismatch"
    
    writer_pid = loaded.state["writer_pid"]
    
    print(f"SUCCESS: Checkpoint recovered in separate process", flush=True)
    print(f"Graph ID: {loaded.graph_id}", flush=True)
    print(f"Run ID: {loaded.run_id}", flush=True)
    print(f"Node: {loaded.node_name}", flush=True)
    print(f"Writer PID: {writer_pid}", flush=True)
    print(f"Metadata: {loaded.metadata}", flush=True)
    print(f"RECOVERY_VERIFIED=True", flush=True)


if __name__ == "__main__":
    main()
