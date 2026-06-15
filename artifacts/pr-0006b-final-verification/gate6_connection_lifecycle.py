"""
Gate 6: SQLite connection lifecycle and file lock test
"""
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestration.durable_execution import DurableStore
from orchestration.durable_checkpointer import DurableCheckpointer, Checkpoint


def test_connection_lifecycle():
    """Test SQLite connection management and cleanup"""
    
    print("=== GATE 6: SQLITE CONNECTION LIFECYCLE ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lifecycle_test.db"
        
        # Test 1: Explicit close
        print("[1] Testing explicit close()...")
        store1 = DurableStore(str(db_path))
        checkpointer1 = DurableCheckpointer(store1)
        
        # Save checkpoint
        cp1 = Checkpoint(
            graph_id="test1",
            run_id="r1",
            node_name="n1",
            state={"data": 1},
            visited_counts={"n1": 1},
            timestamp=time.time(),
            metadata={}
        )
        checkpointer1.save(cp1)
        
        # Explicit close
        store1.close()
        print("✓ store.close() completed")
        
        # Verify database file exists and is not locked
        assert db_path.exists(), "Database file should exist"
        print(f"✓ Database file exists: {db_path}")
        
        # Test 2: Can reopen after close
        print("\n[2] Testing reopen after close...")
        store2 = DurableStore(str(db_path))
        checkpointer2 = DurableCheckpointer(store2)
        
        # Load checkpoint
        loaded = checkpointer2.load("test1", "r1")
        assert loaded is not None, "Should load checkpoint after reopen"
        assert loaded.state["data"] == 1, "Data should match"
        print("✓ Checkpoint loaded after reopen")
        
        store2.close()
        
        # Test 3: Context manager
        print("\n[3] Testing context manager...")
        with DurableStore(str(db_path)) as store3:
            checkpointer3 = DurableCheckpointer(store3)
            cp3 = Checkpoint(
                graph_id="test3",
                run_id="r3",
                node_name="n3",
                state={"data": 3},
                visited_counts={"n3": 1},
                timestamp=time.time(),
                metadata={}
            )
            checkpointer3.save(cp3)
            print("✓ Checkpoint saved in context manager")
        # Context manager should auto-close
        print("✓ Context manager auto-closed")
        
        # Verify can still access after context manager
        store4 = DurableStore(str(db_path))
        checkpointer4 = DurableCheckpointer(store4)
        loaded3 = checkpointer4.load("test3", "r3")
        assert loaded3 is not None, "Should load after context manager"
        assert loaded3.state["data"] == 3, "Data should match"
        print("✓ Data persisted after context manager close")
        store4.close()
        
        # Test 4: Multiple sequential connections (no lock conflicts)
        print("\n[4] Testing multiple sequential connections...")
        for i in range(5):
            with DurableStore(str(db_path)) as store:
                cp = DurableCheckpointer(store)
                loaded = cp.load("test1", "r1")
                assert loaded is not None, f"Iteration {i}: Should load checkpoint"
        print("✓ 5 sequential connections succeeded (no file locks)")
        
        # Test 5: Verify WAL mode cleanup
        print("\n[5] Checking WAL mode artifacts...")
        wal_file = Path(str(db_path) + "-wal")
        shm_file = Path(str(db_path) + "-shm")
        
        # After proper close, WAL files may or may not exist (SQLite manages this)
        # but the database should be accessible
        print(f"  WAL file exists: {wal_file.exists()}")
        print(f"  SHM file exists: {shm_file.exists()}")
        
        # Final verification: can still access database
        final_store = DurableStore(str(db_path))
        final_cp = DurableCheckpointer(final_store)
        final_loaded = final_cp.load("test1", "r1")
        assert final_loaded is not None, "Final access should work"
        final_store.close()
        print("✓ Database accessible after WAL operations")
        
    print("\n[6] All connection lifecycle tests passed")
    print("✓ Explicit close() works")
    print("✓ Reopen after close works")
    print("✓ Context manager cleanup works")
    print("✓ No file lock conflicts")
    print("✓ WAL mode managed properly")
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection_lifecycle()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
