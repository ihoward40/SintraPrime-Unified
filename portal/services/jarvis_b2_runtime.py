from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from portal.services.jarvis_durable_credentials import DurableCredentialBroker
from portal.services.jarvis_durable_lease import DurableAuthorityLeaseStore
from portal.services.jarvis_durable_memory import DurableOperationalMemory
from portal.services.jarvis_durable_operations import DurableReconciler
from portal.services.jarvis_durable_receipts import DurableReceiptRepository


class B2DurableRuntime:
    """Fail-closed factory: every protected mutable state service is durable."""

    backend = "DURABLE"

    def __init__(self, session: AsyncSession | None):
        if session is None:
            raise RuntimeError("B2_DURABILITY_DATABASE_REQUIRED")
        self.session = session
        self.lease = DurableAuthorityLeaseStore(session)
        self.credentials = DurableCredentialBroker(session)
        self.operations = DurableReconciler(session)
        self.receipts = DurableReceiptRepository(session)
        self.memory = DurableOperationalMemory(session)


def create_b2_runtime(session: AsyncSession | None) -> B2DurableRuntime:
    return B2DurableRuntime(session)


def protected_state_backends() -> dict[str, str]:
    return {
        "lease": "DURABLE",
        "credential_replay": "DURABLE",
        "operation_reconciliation": "DURABLE",
        "receipt_persistence": "DURABLE",
        "operational_memory": "DURABLE",
    }
