import pytest

from portal.services.jarvis_b2_runtime import create_b2_runtime, protected_state_backends


def test_canonical_runtime_requires_durable_session():
    with pytest.raises(RuntimeError, match="B2_DURABILITY_DATABASE_REQUIRED"):
        create_b2_runtime(None)


def test_all_protected_state_defaults_are_durable():
    assert protected_state_backends() == {
        "lease": "DURABLE",
        "credential_replay": "DURABLE",
        "operation_reconciliation": "DURABLE",
        "receipt_persistence": "DURABLE",
        "operational_memory": "DURABLE",
    }
