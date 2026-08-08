"""Dead-letter queue and poison-event quarantine (§22-23, §140)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DeadLetterEvent:
    """A failed event must never simply disappear (§22)."""

    event_id: str
    consumer_id: str
    tenant_id: str
    channel_id: str
    failure_class: str
    last_error: str = ""
    failure_count: int = 1
    retry_eligible: bool = True
    max_retries: int = 3
    first_failed: str = field(default_factory=_now)
    last_failed: str = field(default_factory=_now)
    quarantined: bool = False
    quarantine_reason: str = ""
    event_payload: dict = field(default_factory=dict)

    @property
    def exhausted(self) -> bool:
        return self.failure_count >= self.max_retries


@dataclass
class PoisonEvent:
    """QUARANTINED_EVENT (§23). No endless restart."""

    event_id: str
    consumer_id: str
    reason: str
    quarantine_ts: str = field(default_factory=_now)
    security_receipt_id: str = ""


class DeadLetterQueue:
    """Persists failures; retries bounded; escalates to poison quarantine."""

    def __init__(self, store: CollaborationStore, *, default_max_retries: int = 3):
        self.store = store
        self.default_max_retries = default_max_retries
        self._poison: dict[str, PoisonEvent] = {}

    def record_failure(
        self,
        *,
        event_id: str,
        consumer_id: str,
        tenant_id: str,
        channel_id: str,
        failure_class: str,
        error: str = "",
        event_payload: dict | None = None,
    ) -> DeadLetterEvent:
        existing = self.store.load("dead_letters", event_id, DeadLetterEvent)
        if existing is not None:
            existing.failure_count += 1
            existing.last_error = error
            existing.last_failed = _now()
            existing.retry_eligible = not existing.exhausted
            if existing.exhausted:
                existing.quarantined = True
                existing.quarantine_reason = f"retry_exhausted ({existing.failure_count} failures)"
            self.store.save("dead_letters", event_id, existing)
            if existing.exhausted:
                self._quarantine_poison(existing, reason=existing.quarantine_reason)
            return existing

        entry = DeadLetterEvent(
            event_id=event_id,
            consumer_id=consumer_id,
            tenant_id=tenant_id,
            channel_id=channel_id,
            failure_class=failure_class,
            last_error=error,
            failure_count=1,
            retry_eligible=True,
            max_retries=self.default_max_retries,
            event_payload=event_payload or {},
        )
        self.store.save("dead_letters", event_id, entry)
        return entry

    def mark_quarantined(self, event_id: str, *, reason: str = "poison_event") -> DeadLetterEvent:
        entry = self.store.load("dead_letters", event_id, DeadLetterEvent)
        if entry is None:
            entry = DeadLetterEvent(
                event_id=event_id,
                consumer_id="unknown",
                tenant_id="",
                channel_id="",
                failure_class="poison",
                last_error="quarantined without prior failure record",
                failure_count=1,
                retry_eligible=False,
            )
        entry.quarantined = True
        entry.retry_eligible = False
        entry.quarantine_reason = reason
        self.store.save("dead_letters", event_id, entry)
        self._quarantine_poison(entry, reason=reason)
        return entry

    def _quarantine_poison(self, entry: DeadLetterEvent, *, reason: str) -> PoisonEvent:
        poison = PoisonEvent(
            event_id=entry.event_id,
            consumer_id=entry.consumer_id,
            reason=reason,
            security_receipt_id=f"sec_{entry.event_id}",
        )
        self._poison[entry.event_id] = poison
        return poison

    def get(self, event_id: str) -> DeadLetterEvent | None:
        return self.store.load("dead_letters", event_id, DeadLetterEvent)

    def list_all(self) -> list[DeadLetterEvent]:
        return self.store.load_many("dead_letters", DeadLetterEvent)

    def list_quarantined(self) -> list[PoisonEvent]:
        return list(self._poison.values())

    def is_poison(self, event_id: str) -> bool:
        return event_id in self._poison

    def clear(self, event_id: str) -> None:
        self.store.delete("dead_letters", event_id)
        self._poison.pop(event_id, None)
