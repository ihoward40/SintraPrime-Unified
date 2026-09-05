from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_b2_durability import JarvisOperationalMemoryRecord
from portal.services.jarvis_operational_memory import (
    MemoryClass,
    MemoryStatus,
    OperationalMemoryEvent,
)


class DurableOperationalMemory:
    """Canonical runtime operational memory; persistence is mandatory."""

    backend = "DURABLE"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_operational_event(self, **values) -> OperationalMemoryEvent:
        row = await self.session.scalar(select(JarvisOperationalMemoryRecord).where(JarvisOperationalMemoryRecord.tenant_id == values["tenant_id"], JarvisOperationalMemoryRecord.dedup_key == values["dedup_key"]))
        if row is None:
            moment = datetime.now(UTC)
            event_class = values["event_class"]
            row = JarvisOperationalMemoryRecord(
                memory_event_id=__import__("uuid").uuid4().hex,
                **{key: value for key, value in values.items() if key != "event_class"},
                event_class=event_class.value,
                status=MemoryStatus.OPEN.value,
                created_at=moment,
                updated_at=moment,
            )
            self.session.add(row)
            await self.session.flush()
        return self._value(row)

    async def acknowledge_attention(self, *, tenant_id: str, memory_event_id: str) -> OperationalMemoryEvent:
        return await self._transition(tenant_id, memory_event_id, MemoryStatus.ACKNOWLEDGED, "acknowledged_at")

    async def resolve_attention(self, *, tenant_id: str, memory_event_id: str) -> OperationalMemoryEvent:
        return await self._transition(tenant_id, memory_event_id, MemoryStatus.RESOLVED, "resolved_at")

    async def get_for_tenant(self, *, tenant_id: str) -> list[OperationalMemoryEvent]:
        rows = (await self.session.scalars(select(JarvisOperationalMemoryRecord).where(JarvisOperationalMemoryRecord.tenant_id == tenant_id))).all()
        return [self._value(row) for row in rows]

    async def _transition(self, tenant_id, memory_event_id, status, timestamp_field):
        now = datetime.now(UTC)
        values = {"status": status.value, timestamp_field: now, "updated_at": now}
        row = await self.session.scalar(select(JarvisOperationalMemoryRecord).where(JarvisOperationalMemoryRecord.tenant_id == tenant_id, JarvisOperationalMemoryRecord.memory_event_id == memory_event_id))
        if row is None:
            raise PermissionError("MEMORY_NOT_FOUND_IN_TENANT")
        for field, value in values.items():
            setattr(row, field, value)
        await self.session.flush()
        return self._value(row)

    @staticmethod
    def _value(row):
        return OperationalMemoryEvent(memory_event_id=row.memory_event_id, tenant_id=row.tenant_id, mission_id=row.mission_id, action_id=row.action_id, operation_id=row.operation_id, receipt_id=row.receipt_id, receipt_hash=row.receipt_hash, capability_id=row.capability_id, capability_version=row.capability_version, capability_contract_hash=row.capability_contract_hash, event_class=MemoryClass(row.event_class), reason_code=row.reason_code, summary=row.summary, created_at=row.created_at.isoformat(), acknowledged_at=row.acknowledged_at.isoformat() if row.acknowledged_at else None, resolved_at=row.resolved_at.isoformat() if row.resolved_at else None, dedup_key=row.dedup_key, status=MemoryStatus(row.status))
