"""
Canonical event serialization for Observatory hash chaining.

All hash-chain computation must go through this module. No router, service,
test, or adapter may independently recreate hashing logic.

The canonical form is:
1. JSON-serialized with sorted keys (deterministic key order)
2. Unicode normalized to NFC (py3 str is already NFC, but explicit is better)
3. datetime values in ISO 8601 with timezone (UTC suffix "Z" for UTC)
4. UUID values as lowercase hyphenated strings
5. booleans as true/false (JSON native)
6. null values as null (JSON native)
7. floating-point values as exact decimal representations to avoid
   platform-dependent float issues
8. Decimal values as string representations
9. Nested dicts and lists recursively canonicalized

The canonical bytes are UTF-8 encoded JSON.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID


# Sentinel for fields that should be excluded entirely rather than set to null.
_EXCLUDE = object()


def _normalize_value(value: Any) -> Any:
    """Recursively normalize a value for canonical serialization."""
    if value is None:
        return None
    if isinstance(value, bool):
        # bool must be checked before int because bool is a subclass of int
        return value
    if isinstance(value, int):
        # Python ints are arbitrary precision; represent as-is
        return value
    if isinstance(value, float):
        # Represent floats as exact decimal strings to avoid platform-dependent
        # float representation. This ensures the same hash across process restarts.
        # We use repr() which gives the shortest representation that round-trips.
        # For truly decimal values, callers should use Decimal.
        return repr(value)
    if isinstance(value, Decimal):
        # Decimal values are normalized and represented as strings
        # to preserve exact precision across systems.
        return str(value.normalize())
    if isinstance(value, UUID):
        return str(value).lower()
    if isinstance(value, datetime):
        # Ensure timezone-aware. Naive datetimes are assumed UTC.
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        # Always convert to UTC
        value = value.astimezone(UTC)
        # Format as ISO 8601 with "Z" suffix for UTC
        # This is the canonical timestamp format.
        iso = value.strftime("%Y-%m-%dT%H:%M:%S")
        # Include microseconds if present
        if value.microsecond:
            # Use up to 6 decimal places, strip trailing zeros
            us = f"{value.microsecond:06d}".rstrip("0")
            iso += f".{us}"
        iso += "Z"
        return iso
    if isinstance(value, str):
        # Unicode NFC normalization ensures equivalent strings produce
        # the same canonical form regardless of composition.
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        # Dicts: recurse with sorted keys
        return {_normalize_value(k): _normalize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        # Lists/tuples: recurse element-wise
        return [_normalize_value(item) for item in value]
    if isinstance(value, bytes):
        # bytes: decode as UTF-8 string
        return value.decode("utf-8")
    # Fallback: try JSON-serializable representation
    return value


def canonical_event_bytes(payload: Mapping[str, Any]) -> bytes:
    """Convert an event payload to canonical UTF-8 bytes for hashing.

    This is the single authoritative serialization function for the
    Observatory hash chain. All hash computation must use this function.

    Args:
        payload: A mapping of event fields. Keys must be strings.

    Returns:
        UTF-8 encoded JSON bytes with deterministic key ordering and
        normalized values.

    Raises:
        TypeError: If the payload contains values that cannot be
            canonically serialized (e.g., sets, custom objects).
    """
    normalized = _normalize_value(payload)
    # sort_keys=True ensures deterministic key ordering regardless of
    # insertion order or dict implementation.
    # separators=(',', ':') produces compact JSON without whitespace.
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_event_hash(payload: Mapping[str, Any]) -> str:
    """Compute the SHA-256 hash of a canonically serialized event payload.

    This is a convenience wrapper around canonical_event_bytes for
    direct hash computation.

    Args:
        payload: A mapping of event fields.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    import hashlib
    return hashlib.sha256(canonical_event_bytes(payload)).hexdigest()