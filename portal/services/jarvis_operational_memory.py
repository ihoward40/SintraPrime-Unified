"""B2-B10 operational memory: evidence references, never authority."""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


class MemoryClass(enum.StrEnum):
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    FAIL_CLOSED_EVENT = "FAIL_CLOSED_EVENT"
    GOVERNED_ACTION_COMPLETED = "GOVERNED_ACTION_COMPLETED"


class MemoryStatus(enum.StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


_PRIORITY = {
    MemoryClass.ATTENTION_REQUIRED: 3,
    MemoryClass.FAIL_CLOSED_EVENT: 2,
    MemoryClass.GOVERNED_ACTION_COMPLETED: 1,
}


@dataclass(frozen=True)
class OperationalMemoryEvent:
    memory_event_id: str
    tenant_id: str
    mission_id: str
    action_id: str
    operation_id: str
    receipt_id: str | None
    receipt_hash: str | None
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    event_class: MemoryClass
    reason_code: str
    summary: str
    created_at: str
    acknowledged_at: str | None
    resolved_at: str | None
    dedup_key: str
    status: MemoryStatus = MemoryStatus.OPEN

    def as_authority(self) -> None:
        raise PermissionError("MEMORY_IS_NOT_AUTHORITY")

    def to_safe_dict(self) -> dict:
        return self.__dict__.copy()


class OperationalMemory:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], OperationalMemoryEvent] = {}

    def record_operational_event(self, *, tenant_id: str, mission_id: str, action_id: str, operation_id: str, receipt_id: str | None, receipt_hash: str | None, capability_id: str, capability_version: str, capability_contract_hash: str, event_class: MemoryClass, reason_code: str, summary: str, dedup_key: str) -> OperationalMemoryEvent:
        key = (tenant_id, dedup_key)
        existing = self._events.get(key)
        if existing is not None:
            return existing
        event = OperationalMemoryEvent(str(uuid.uuid4()), tenant_id, mission_id, action_id, operation_id, receipt_id, receipt_hash, capability_id, capability_version, capability_contract_hash, event_class, reason_code, summary, datetime.now(UTC).isoformat(), None, None, dedup_key)
        self._events[key] = event
        return event

    def acknowledge_attention(self, *, tenant_id: str, memory_event_id: str) -> OperationalMemoryEvent:
        event = self._find(tenant_id, memory_event_id)
        return self._replace(event, status=MemoryStatus.ACKNOWLEDGED, acknowledged_at=datetime.now(UTC).isoformat())

    def resolve_attention(self, *, tenant_id: str, memory_event_id: str) -> OperationalMemoryEvent:
        event = self._find(tenant_id, memory_event_id)
        return self._replace(event, status=MemoryStatus.RESOLVED, resolved_at=datetime.now(UTC).isoformat())

    def get_for_tenant(self, *, tenant_id: str) -> list[OperationalMemoryEvent]:
        return [event for (event_tenant, _), event in self._events.items() if event_tenant == tenant_id]

    def _find(self, tenant_id: str, memory_event_id: str) -> OperationalMemoryEvent:
        for (event_tenant, _), event in self._events.items():
            if event_tenant == tenant_id and event.memory_event_id == memory_event_id:
                return event
        raise PermissionError("MEMORY_NOT_FOUND_IN_TENANT")

    def _replace(self, event: OperationalMemoryEvent, **changes) -> OperationalMemoryEvent:
        updated = OperationalMemoryEvent(**{**event.__dict__, **changes})
        self._events[(updated.tenant_id, updated.dedup_key)] = updated
        return updated


def memory_priority(event_class: MemoryClass) -> int:
    return _PRIORITY[event_class]
