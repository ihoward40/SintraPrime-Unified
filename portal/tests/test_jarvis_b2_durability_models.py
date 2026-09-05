"""JARVIS B2 durability migration model smoke tests."""
from portal.models.jarvis_b2_durability import (
    JarvisActionReceiptRecord,
    JarvisAuthorityLeaseRecord,
    JarvisCredentialStateRecord,
    JarvisOperationalMemoryRecord,
    JarvisOperationRecord,
)


def test_durable_models_are_registered_with_unique_boundaries():
    tables = {
        JarvisAuthorityLeaseRecord.__tablename__, JarvisOperationRecord.__tablename__,
        JarvisActionReceiptRecord.__tablename__, JarvisOperationalMemoryRecord.__tablename__,
        JarvisCredentialStateRecord.__tablename__,
    }
    assert tables == {
        "jarvis_authority_leases", "jarvis_operations", "jarvis_action_receipts",
        "jarvis_operational_memory", "jarvis_credential_state",
    }
    assert JarvisOperationRecord.__table__.c.idempotency_key.unique
    assert JarvisActionReceiptRecord.__table__.c.receipt_hash.unique
    assert JarvisCredentialStateRecord.__table__.c.nonce_hash.unique
