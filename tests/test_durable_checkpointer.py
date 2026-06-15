"""Tests for DurableCheckpointer - minimal version."""
import pytest
import tempfile
from pathlib import Path
from orchestration.durable_checkpointer import DurableCheckpointer, Checkpoint
from orchestration.durable_execution import DurableStore

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test.db")

def test_checkpoint_basic(temp_db):
    store1 = DurableStore(db_path=temp_db)
    cp1 = DurableCheckpointer(store1)
    ckpt = Checkpoint("g1", "r1", "n1", {"x": 1}, {}, 100.0, {})
    cp1.save(ckpt)
    if store1._persistent_conn: store1._persistent_conn.close()
    
    store2 = DurableStore(db_path=temp_db)
    cp2 = DurableCheckpointer(store2)
    loaded = cp2.load("g1", "r1")
    assert loaded.state["x"] == 1
    if store2._persistent_conn: store2._persistent_conn.close()
