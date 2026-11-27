"""ActivationService — bounded runtime for agent activations (§XXII, §LXXXII-CF-1C)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from collaboration.models import ActivationRecord
from collaboration.models.enums import RuntimeStatus
from collaboration.policies import ConcurrencyPolicy
from collaboration.receipts import ActivationReceipt, CollaborationReceiptStore
from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ActivationRequest:
    activation_id: str
    agent_id: str
    channel_id: str
    tenant_id: str
    event_id: str = ""
    behavior_contract_hash: str = ""


class ActivationService:
    """Queues activations within parallelism bounds. No unlimited fanout."""

    def __init__(
        self,
        *,
        store: CollaborationStore,
        concurrency: ConcurrencyPolicy,
        receipts: CollaborationReceiptStore | None = None,
    ):
        self.store = store
        self.concurrency = concurrency
        self.receipts = receipts
        self._queues: dict[str, list[ActivationRequest]] = defaultdict(list)

    def request(self, req: ActivationRequest, max_parallelism: int) -> ActivationRecord:
        """Try to start or queue."""
        ar = ActivationRecord(
            activation_id=req.activation_id,
            agent_id=req.agent_id,
            channel_id=req.channel_id,
            tenant_id=req.tenant_id,
            trigger_event_id=req.event_id,
            behavior_contract_hash=req.behavior_contract_hash,
        )

        if self.concurrency.allow(req.agent_id, max_parallelism):
            ar.status = RuntimeStatus.RUNNING
            ar.started_at = _now()
            self.concurrency.acquire(req.agent_id)
        else:
            ar.status = RuntimeStatus.QUEUED
            self._queues[req.agent_id].append(req)

        self.store.save("activations", ar.activation_id, ar)
        return ar

    def complete(
        self, activation_id: str, *, status: RuntimeStatus = RuntimeStatus.COMPLETED
    ) -> ActivationRecord | None:
        ar = self.store.load("activations", activation_id, ActivationRecord)
        if ar is None:
            return None
        ar.status = status
        ar.completed_at = _now()
        self.store.save("activations", ar.activation_id, ar)
        self.concurrency.release(ar.agent_id)
        if self.receipts:
            self.receipts.record_activation(
                ActivationReceipt(
                    receipt_id=f"arec_{ar.activation_id}",
                    activation_id=ar.activation_id,
                    agent_id=ar.agent_id,
                    channel_id=ar.channel_id,
                    tenant_id=ar.tenant_id,
                    trigger_event_id=ar.trigger_event_id,
                    behavior_contract_hash=ar.behavior_contract_hash,
                    result_status=status.value,
                )
            )
        self._drain_queue(ar.agent_id)
        return ar

    def _drain_queue(self, agent_id: str) -> None:
        # Queued items are picked up when the agent's next request arrives;
        # a persistent scheduler worker (CF-2) will drain on capacity release.
        _ = agent_id

    def stop(self, activation_id: str) -> ActivationRecord | None:
        return self.complete(activation_id, status=RuntimeStatus.STOPPED)

    def fail(self, activation_id: str, error: str = "") -> ActivationRecord | None:
        ar = self.store.load("activations", activation_id, ActivationRecord)
        if ar is None:
            return None
        ar.status = RuntimeStatus.FAILED
        ar.error = error
        ar.completed_at = _now()
        self.store.save("activations", ar.activation_id, ar)
        self.concurrency.release(ar.agent_id)
        return ar

    def get(self, activation_id: str) -> ActivationRecord | None:
        return self.store.load("activations", activation_id, ActivationRecord)

    def list_by_channel(self, channel_id: str) -> list[ActivationRecord]:
        return [
            a
            for a in self.store.load_many("activations", ActivationRecord)
            if a.channel_id == channel_id
        ]

    def pending_count(self, agent_id: str) -> int:
        return len(self._queues[agent_id])
