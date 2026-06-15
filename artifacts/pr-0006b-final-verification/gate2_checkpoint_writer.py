"""
Gate 2: Checkpoint Writer - Creates checkpoint then reports PID for termination
"""
import os
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestration.durable_execution import DurableStore
from orchestration.durable_checkpointer import DurableCheckpointer, Checkpoint


def main():
    db_path = Path(__file__).parent / "gate2_test.db"
    if db_path.exists():
        db_path.unlink()
    
    # Create DurableStore and DurableCheckpointer
    store = DurableStore(str(db_path))
    checkpointer = DurableCheckpointer(store)
    
    # Create checkpoint using DurableCheckpointer API
    test_checkpoint = Checkpoint(
        graph_id="gate2-test-graph",
        run_id="gate2-run-001",
        node_name="test-node",
        state={"test_key": "test_value", "writer_pid": os.getpid()},
        visited_counts={"test-node": 1},
        timestamp=time.time(),
        metadata={"source": "gate2", "step": 1}
    )
    
    checkpointer.save(test_checkpoint)
    
    # Write PID to file for parent to read
    pid_file = Path(__file__).parent / "gate2_pid.txt"
    pid_file.write_text(str(os.getpid()))
    
    print(f"PID={os.getpid()}", flush=True)
    print(f"Checkpoint written", flush=True)
    print(f"DB path: {db_path}", flush=True)
    
    # Sleep to allow parent to kill this process
    time.sleep(60)
    print("Process completed normally (not terminated)", flush=True)


if __name__ == "__main__":
    main()
