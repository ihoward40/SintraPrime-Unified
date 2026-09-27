"""
Event Canonicalization — Frozen Hash and Timestamp Rules for the Observatory Ledger.

This module is the SOLE source of truth for:
- Canonical timestamp serialization
- Payload serialization
- Hash computation (v1 and v2)
- Hash verification
- Hash-version dispatch

ORM models, services, migrations, verification jobs, adapters, and tests
MUST import from this module rather than reimplementing hash logic.

Rules (FROZEN — do not modify):
- v1 hash input:  event_type|mission_id|agent_id|previous_hash|timestamp|payload
- v2 hash input:  run_id|sequence|event_type|mission_id|agent_id|previous_hash|timestamp|payload
- Timestamp format:  ISO-8601 with explicit +00:00 suffix (never 'Z')
- Naive timestamps:  treated as UTC for backward compatibility
- Payload:  Python dict repr (deterministic key order not guaranteed —
  all payloads stored via EventService use canonical_event_bytes for ordering)
- Sequence zero:  NOT valid for persisted events (CHECK: sequence >= 1).
  The serialization helper formats 0 as "0" deterministically, but
  EventService must reject sequence=0 at ingestion time.

New event ingestion rule:
  Naive timestamps MUST be rejected or explicitly normalized before
  persistence.  The verifier may continue treating legacy naive timestamps
  as UTC for deterministic compatibility.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timezone
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# Canonical Timestamp
# ═══════════════════════════════════════════════════════════════════════════════

def canonical_timestamp(dt: datetime) -> str:
    """Produce a canonical ISO-8601 timestamp string for hash computation.

    Rules:
    - Always produces timezone-aware output with '+00:00' suffix.
    - Naive datetimes are assumed UTC and get +00:00 attached.
    - Aware non-UTC datetimes are converted to UTC via astimezone.
    - The format '+00:00' is used exclusively, never 'Z'.

    Examples that must produce identical output:
        canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        canonical_timestamp(datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone(-4)))
        canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0))  # naive → assumed UTC

    All three yield: '2026-07-15T12:00:00+00:00'
    """
    if dt.tzinfo is None:
        # Naive datetime: assume UTC and attach timezone
        dt = dt.replace(tzinfo=UTC)
    else:
        # Convert to UTC regardless of source timezone
        dt = dt.astimezone(UTC)
    return dt.isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Hash Computation — v1 (Legacy, FROZEN)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_hash_v1(
    event_type: str,
    payload: dict[str, Any],
    previous_hash: str | None,
    timestamp: str,
    mission_id: str | None = None,
    agent_id: str | None = None,
) -> str:
    """Compute SHA-256 event hash using v1 formula (legacy).

    v1 hash input:  event_type|mission_id|agent_id|previous_hash|timestamp|payload
    Does NOT include run_id or sequence.

    This function is FROZEN. Do not modify.
    """
    data = (
        f"{event_type}|{mission_id or ''}|{agent_id or ''}|"
        f"{previous_hash or ''}|{timestamp}|{payload}"
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# Hash Computation — v2 (Run-Scoped, FROZEN)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_hash_v2(
    event_type: str,
    payload: dict[str, Any],
    previous_hash: str | None,
    timestamp: str,
    mission_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    sequence: int | None = None,
) -> str:
    """Compute SHA-256 event hash using v2 formula (run-scoped).

    v2 hash input:  run_id|sequence|event_type|mission_id|agent_id|previous_hash|timestamp|payload
    Includes run_id and sequence so that events in different runs with
    identical payloads produce different hashes, and sequence-number
    tampering is detectable.

    This function is FROZEN. Do not modify.
    """
    seq_str = str(sequence) if sequence is not None else ''
    data = (
        f"{run_id or ''}|{seq_str}|{event_type}|"
        f"{mission_id or ''}|{agent_id or ''}|{previous_hash or ''}|"
        f"{timestamp}|{payload}"
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# Hash Version Dispatch
# ═══════════════════════════════════════════════════════════════════════════════

def compute_hash(
    event_type: str,
    payload: dict[str, Any],
    previous_hash: str | None,
    timestamp: str,
    mission_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    sequence: int | None = None,
    hash_version: int = 2,
) -> str:
    """Dispatch to the correct hash formula based on hash_version.

    hash_version controls computation of the current event hash:
      1 → compute_hash_v1 (legacy, no run_id/sequence)
      2 → compute_hash_v2 (run-scoped, includes run_id/sequence)

    Any unknown version raises ValueError.
    """
    if hash_version == 1:
        return compute_hash_v1(
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
            timestamp=timestamp,
            mission_id=mission_id,
            agent_id=agent_id,
        )
    elif hash_version == 2:
        return compute_hash_v2(
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
            timestamp=timestamp,
            mission_id=mission_id,
            agent_id=agent_id,
            run_id=run_id,
            sequence=sequence,
        )
    else:
        raise ValueError(
            f"Unsupported hash_version {hash_version} for event "
            f"run_id={run_id} sequence={sequence}. "
            f"Supported versions: 1 (legacy), 2 (run-scoped)."
        )


def verify_event_hash(
    event_type: str,
    payload: dict[str, Any],
    previous_hash: str | None,
    timestamp: str,
    stored_hash: str,
    mission_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    sequence: int | None = None,
    hash_version: int = 2,
) -> bool:
    """Verify an event's stored hash against the expected computation.

    Dispatches to the correct formula based on hash_version.
    Unknown hash_version always returns False (fail closed).
    """
    try:
        expected = compute_hash(
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
            timestamp=timestamp,
            mission_id=mission_id,
            agent_id=agent_id,
            run_id=run_id,
            sequence=sequence,
            hash_version=hash_version,
        )
    except ValueError:
        return False
    return expected == stored_hash