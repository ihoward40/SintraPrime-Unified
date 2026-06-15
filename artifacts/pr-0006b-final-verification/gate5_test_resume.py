"""
Gate 5: Test StateGraph resume with DurableCheckpointer
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestration.langgraph_engine import StateGraph


async def test_resume():
    """Test StateGraph.run() with resume_from_checkpoint=True"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "resume_test.db")
        os.environ["WORKFLOW_DB_PATH"] = db_path
        
        try:
            # Create graph with simple node
            graph = StateGraph(graph_id="resume-test")
            graph.add_node("step1", lambda state: {"progress": 50})
            graph.add_node("step2", lambda state: {"progress": 100})
            graph.set_entry_point("step1")
            graph.add_edge("step1", "step2")
            graph.add_terminal_nodes("step2")
            
            # First run - should save checkpoints
            result1 = await graph.run(run_id="test-run-1", initial_state={"start": True})
            print(f"First run completed: {result1.final_state}")
            
            # Close and create new graph instance
            if hasattr(graph.checkpointer, 'store'):
                graph.checkpointer.store.close()
            
            graph2 = StateGraph(graph_id="resume-test")
            graph2.add_node("step1", lambda state: {"progress": 50})
            graph2.add_node("step2", lambda state: {"progress": 100})
            graph2.set_entry_point("step1")
            graph2.add_edge("step1", "step2")
            graph2.add_terminal_nodes("step2")
            
            # Try to resume - this will call load_latest()
            print("Attempting resume from checkpoint...")
            result2 = await graph2.run(
                run_id="test-run-1",
                initial_state={"start": True},
                resume_from_checkpoint=True
            )
            print(f"Resume run completed: {result2.final_state}")
            
            print("SUCCESS: StateGraph resume worked with DurableCheckpointer")
            return True
            
        except AttributeError as e:
            if "load_latest" in str(e):
                print(f"FAILURE: DurableCheckpointer missing load_latest() method")
                print(f"Error: {e}")
                return False
            raise
        finally:
            if 'graph' in locals() and hasattr(graph.checkpointer, 'store'):
                graph.checkpointer.store.close()
            if 'graph2' in locals() and hasattr(graph2.checkpointer, 'store'):
                graph2.checkpointer.store.close()
            os.environ.pop("WORKFLOW_DB_PATH", None)


if __name__ == "__main__":
    success = asyncio.run(test_resume())
    sys.exit(0 if success else 1)
