from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_b2_durability import JarvisActionReceiptRecord
from portal.services.jarvis_action_receipt_b2 import ActionReceipt, verify_receipt


class DurableReceiptRepository:
    """Append-only persistence boundary for finalized B2 receipts."""

    backend = "DURABLE"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def persist(self, receipt: ActionReceipt) -> None:
        if not verify_receipt(receipt):
            raise ValueError("RECEIPT_HASH_INVALID")
        if await self.session.scalar(select(JarvisActionReceiptRecord).where(JarvisActionReceiptRecord.receipt_id == receipt.receipt_id)):
            raise ValueError("RECEIPT_IMMUTABLE")
        self.session.add(JarvisActionReceiptRecord(receipt_id=receipt.receipt_id, tenant_id=receipt.tenant_id, receipt_hash=receipt.receipt_hash, previous_receipt_hash=receipt.previous_receipt_hash, receipt_payload=receipt.to_safe_dict(), finalized_at=datetime.now(UTC)))
        await self.session.flush()

    async def load(self, receipt_id: str, *, tenant_id: str) -> ActionReceipt | None:
        row = await self.session.scalar(select(JarvisActionReceiptRecord).where(JarvisActionReceiptRecord.receipt_id == receipt_id, JarvisActionReceiptRecord.tenant_id == tenant_id))
        return ActionReceipt(**row.receipt_payload) if row else None
