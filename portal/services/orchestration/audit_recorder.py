"""Hash-chained in-memory audit recording for mock orchestration runs."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def append_event(events: list[dict[str, Any]], event_type: str, payload: dict[str, Any], role: str | None = None) -> dict[str, Any]:
    previous_hash = events[-1]["event_hash"] if events else None
    event = {
        "sequence": len(events) + 1,
        "event_type": event_type,
        "actor_role": role,
        "payload": payload,
        "previous_event_hash": previous_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
    event["event_hash"] = _hash_event(event)
    events.append(event)
    return event


def _hash_event(event: dict[str, Any]) -> str:
    canonical = json.dumps({k: v for k, v in event.items() if k != "event_hash"}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
