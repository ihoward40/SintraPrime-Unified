import pytest

from portal.services.jarvis_legacy_containment import (
    LEGACY_CONTAINMENT_MAP,
    LegacyDisposition,
    deny_legacy_mutation,
)
from portal.services.jarvis_operational_memory import (
    MemoryClass,
    MemoryStatus,
    OperationalMemory,
    memory_priority,
)


def event(memory, **kwargs):
    values = {
        "tenant_id": "tenant-a", "mission_id": "mission", "action_id": "action",
        "operation_id": "operation", "receipt_id": "receipt", "receipt_hash": "hash",
        "capability_id": "cap", "capability_version": "1", "capability_contract_hash": "contract",
        "event_class": MemoryClass.ATTENTION_REQUIRED, "reason_code": "SIDE_EFFECT_UNKNOWN",
        "summary": "unknown", "dedup_key": "action:unknown",
    }
    values.update(kwargs)
    return memory.record_operational_event(**values)


def test_attention_deduplicates_and_lifecycle_persists():
    memory = OperationalMemory()
    first = event(memory)
    second = event(memory)
    assert first.memory_event_id == second.memory_event_id
    acknowledged = memory.acknowledge_attention(tenant_id="tenant-a", memory_event_id=first.memory_event_id)
    resolved = memory.resolve_attention(tenant_id="tenant-a", memory_event_id=first.memory_event_id)
    assert acknowledged.status == MemoryStatus.ACKNOWLEDGED
    assert resolved.status == MemoryStatus.RESOLVED


def test_memory_is_not_authority_and_tenant_isolation_holds():
    memory = OperationalMemory()
    item = event(memory)
    with pytest.raises(PermissionError):
        item.as_authority()
    with pytest.raises(PermissionError):
        memory.acknowledge_attention(tenant_id="tenant-b", memory_event_id=item.memory_event_id)


def test_priority_order():
    assert memory_priority(MemoryClass.ATTENTION_REQUIRED) > memory_priority(MemoryClass.FAIL_CLOSED_EVENT) > memory_priority(MemoryClass.GOVERNED_ACTION_COMPLETED)


def test_legacy_mutation_inventory_is_machine_readable_and_denies_quarantine():
    assert LEGACY_CONTAINMENT_MAP
    quarantined = next(item for item in LEGACY_CONTAINMENT_MAP if item.disposition == LegacyDisposition.QUARANTINE)
    with pytest.raises(PermissionError):
        deny_legacy_mutation(surface=quarantined)
    assert any(item.disposition == LegacyDisposition.NOT_PRESENT for item in LEGACY_CONTAINMENT_MAP)
