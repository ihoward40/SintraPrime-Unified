"""Structural guard: protected B2 mutable state has durable repository seams."""
from pathlib import Path

PROTECTED = {
    "lease": "portal/services/jarvis_durable_lease.py",
    "credential": "portal/services/jarvis_durable_credentials.py",
    "operation": "portal/services/jarvis_durable_operations.py",
    "receipt": "portal/services/jarvis_durable_receipts.py",
    "memory": "portal/services/jarvis_durable_memory.py",
}


def test_protected_state_has_durable_repository_boundary():
    for path in PROTECTED.values():
        assert Path(path).exists(), path
    assert "class durableauthorityleasestore" in Path(PROTECTED["lease"]).read_text().lower()
