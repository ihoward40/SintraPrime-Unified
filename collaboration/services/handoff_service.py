"""HandoffService — structured agent-to-agent handoff (§XXVIII-XXIX)."""

from __future__ import annotations

from collaboration.models import AgentHandoff
from collaboration.models.enums import HandoffStatus
from collaboration.receipts import CollaborationReceiptStore, HandoffReceipt
from collaboration.services.store import CollaborationStore


class HandoffService:
    def __init__(
        self, store: CollaborationStore, receipts: CollaborationReceiptStore | None = None
    ):
        self.store = store
        self.receipts = receipts

    def create(
        self,
        *,
        handoff_id: str,
        source_agent: str,
        target_agent: str,
        channel_id: str,
        tenant_id: str,
        task: str = "",
        input_artifacts: list[str] | None = None,
        expected_output_schema: str = "",
        correlation_id: str = "",
    ) -> AgentHandoff:
        h = AgentHandoff(
            handoff_id=handoff_id,
            source_agent=source_agent,
            target_agent=target_agent,
            channel_id=channel_id,
            tenant_id=tenant_id,
            task=task,
            input_artifacts=input_artifacts or [],
            expected_output_schema=expected_output_schema,
            correlation_id=correlation_id,
        )
        self.store.save("handoffs", h.handoff_id, h)
        if self.receipts:
            self.receipts.record_handoff(
                HandoffReceipt(
                    receipt_id=f"hrec_{h.handoff_id}",
                    handoff_id=h.handoff_id,
                    source_agent=h.source_agent,
                    target_agent=h.target_agent,
                    channel_id=h.channel_id,
                    tenant_id=h.tenant_id,
                    task=h.task,
                    status=h.status.value,
                )
            )
        return h

    def accept(self, handoff_id: str) -> AgentHandoff | None:
        h = self.store.load("handoffs", handoff_id, AgentHandoff)
        if h is None:
            return None
        h.status = HandoffStatus.ACCEPTED
        self.store.save("handoffs", h.handoff_id, h)
        return h

    def complete(self, handoff_id: str, artifacts: list[str] | None = None) -> AgentHandoff | None:
        h = self.store.load("handoffs", handoff_id, AgentHandoff)
        if h is None:
            return None
        h.status = HandoffStatus.COMPLETED
        h.result_artifacts = artifacts or []
        self.store.save("handoffs", h.handoff_id, h)
        return h

    def fail(self, handoff_id: str, reason: str = "") -> AgentHandoff | None:
        h = self.store.load("handoffs", handoff_id, AgentHandoff)
        if h is None:
            return None
        h.status = HandoffStatus.FAILED
        if reason:
            h.metadata["failure_reason"] = reason
        self.store.save("handoffs", h.handoff_id, h)
        return h

    def get(self, handoff_id: str) -> AgentHandoff | None:
        return self.store.load("handoffs", handoff_id, AgentHandoff)

    def list_by_channel(self, channel_id: str) -> list[AgentHandoff]:
        return [
            h for h in self.store.load_many("handoffs", AgentHandoff) if h.channel_id == channel_id
        ]
