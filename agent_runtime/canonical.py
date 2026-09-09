"""Canonical deterministic hashing (Wave 3, §1 Checkpoint 2).

One trusted primitive for the runtime: canonical_hash(value).

Properties certified (§1):
- semantically identical objects → identical hash (dict order irrelevant);
- enums serialize by stable canonical value (their .value);
- datetimes normalize to canonical ISO-8601 UTC (authority-bearing type);
- tuples/lists canonicalized intentionally; sets sorted deterministically;
- transient runtime fields excluded by callers, not by heuristics;
- unserializable structures fail explicitly (never silently stringified).

Canonical form: sorted-key JSON with separators (",", ":"), UTF-8, SHA-256.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CanonicalizationError(TypeError):
    """Unsupported structure — fail explicitly, never silently stringify."""


def _reject(obj: Any) -> None:
    raise CanonicalizationError(f"unserializable within set element: {type(obj).__name__}")


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        # §1: canonical ISO-8601 UTC — datetimes are authority-bearing and
        # must serialize deterministically (tz-aware normalized to UTC).
        if value.tzinfo is None:
            raise CanonicalizationError(
                "naive datetime has no canonical form; attach tzinfo (fail-closed)"
            )
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Enum):
        return value.value  # stable canonical value for enums
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, frozenset, set)):
        items = [_canonicalize(v) for v in value]
        if isinstance(value, (frozenset, set)):
            items.sort(key=lambda v: json.dumps(v, sort_keys=True, default=_reject))
        return items
    if hasattr(value, "model_dump"):
        # pydantic v2: canonicalize the model dict (mode="json" for dates/etc.)
        return _canonicalize(value.model_dump(mode="json"))
    raise CanonicalizationError(
        f"type {type(value).__name__} has no canonical serialization; "
        "convert explicitly (fail-closed, never silently stringified)"
    )


def canonical_json(value: Any) -> str:
    """Deterministic canonical JSON string (sorted keys, tight separators)."""
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_hash(value: Any) -> str:
    """SHA-256 hex digest of the canonical JSON form."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
