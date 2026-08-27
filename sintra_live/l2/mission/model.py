"""Immutable canonical value objects for the L2-I1 durable mission aggregate."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .state import MissionState

AGGREGATE_SCHEMA_VERSION = "sp-live-001-l2-i1-mission-v1"
EVENT_SCHEMA_VERSION = "sp-live-001-l2-i1-event-v1"
AGGREGATE_HASH_DOMAIN = b"SP-LIVE-001:L2:I1:AGGREGATE:v1\0"
EVENT_HASH_DOMAIN = b"SP-LIVE-001:L2:I1:EVENT:v1\0"
TRANSITION_REQUEST_HASH_DOMAIN = b"SP-LIVE-001:L2:I1:TRANSITION-REQUEST:v1\0"
GENESIS_PREVIOUS_EVENT_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        raise SchemaError("floats are prohibited in hashed I1 records")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Enum):
        return _normalize(value.value)
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Mapping):
        normalized: Dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SchemaError("JSON object keys must be strings")
            nkey = unicodedata.normalize("NFC", key)
            if nkey in normalized:
                raise SchemaError("duplicate key after Unicode normalization")
            normalized[nkey] = _normalize(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise SchemaError("sets are prohibited; use canonical sorted tuples")
    raise SchemaError(f"unsupported canonical type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_domain(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + canonical_bytes(value)).hexdigest()


def strict_json_loads(raw: bytes) -> Dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SchemaError("document is not UTF-8") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SchemaError("UTF-8 BOM is prohibited")

    def pairs(items: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in items:
            normalized = unicodedata.normalize("NFC", key)
            if normalized in result:
                raise SchemaError(f"duplicate JSON key: {normalized}")
            result[normalized] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_float=lambda _: (_ for _ in ()).throw(SchemaError("floats prohibited")),
            parse_constant=lambda _: (_ for _ in ()).throw(SchemaError("non-finite numbers prohibited")),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SchemaError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise SchemaError("top-level mission document must be an object")
    _normalize(value)
    return value


def _require_exact_fields(data: Mapping[str, Any], expected: Iterable[str], context: str) -> None:
    expected_set = set(expected)
    actual = set(data)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        unknown = sorted(actual - expected_set)
        raise SchemaError(f"{context} fields mismatch; missing={missing}, unknown={unknown}")


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise SchemaError(f"invalid {name}")
    if ".." in value or "/" in value or "\\" in value or "\x00" in value:
        raise SchemaError(f"unsafe {name}")
    return unicodedata.normalize("NFC", value)


def _hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise SchemaError(f"invalid {name}")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise SchemaError(f"invalid {name}; canonical UTC microsecond Z format required")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise SchemaError(f"invalid {name}") from exc
    return value


def _canonical_string_tuple(values: Any, name: str, *, allow_empty: bool = False) -> Tuple[str, ...]:
    if not isinstance(values, list):
        raise SchemaError(f"{name} must be an array")
    normalized = tuple(unicodedata.normalize("NFC", item) for item in values if isinstance(item, str))
    if len(normalized) != len(values) or (not allow_empty and not normalized):
        raise SchemaError(f"invalid {name}")
    expected = tuple(sorted(set(normalized), key=lambda item: item.encode("utf-8")))
    if normalized != expected:
        raise SchemaError(f"{name} must be duplicate-free and UTF-8 lexicographically sorted")
    return normalized


@dataclass(frozen=True)
class MissionIdentity:
    program_id: str
    gate_id: str
    mission_id: str
    request_id: str
    request_sha256: str
    principal_identity_reference: str
    mission_scope_sha256: str
    authority_snapshot_reference: str

    def __post_init__(self) -> None:
        for name in ("program_id", "gate_id", "mission_id", "request_id", "principal_identity_reference", "authority_snapshot_reference"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        object.__setattr__(self, "request_sha256", _hash(self.request_sha256, "request_sha256"))
        object.__setattr__(self, "mission_scope_sha256", _hash(self.mission_scope_sha256, "mission_scope_sha256"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MissionIdentity":
        _require_exact_fields(data, (f.name for f in fields(cls)), "identity")
        return cls(**data)


@dataclass(frozen=True)
class MissionScope:
    purpose: str
    allowed_operations: Tuple[str, ...]
    prohibited_operations: Tuple[str, ...]
    consequence_ceiling: str
    budget_ceilings: Tuple[Tuple[str, int], ...]
    side_effect_budget: int
    required_evidence_types: Tuple[str, ...]
    expiry: str
    cancellation_authority: str

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise SchemaError("purpose is required")
        object.__setattr__(self, "purpose", unicodedata.normalize("NFC", self.purpose))
        for attr in ("allowed_operations", "prohibited_operations", "required_evidence_types"):
            value = list(getattr(self, attr))
            object.__setattr__(self, attr, _canonical_string_tuple(value, attr))
        if not isinstance(self.consequence_ceiling, str) or not self.consequence_ceiling:
            raise SchemaError("consequence_ceiling is required")
        if isinstance(self.side_effect_budget, bool) or self.side_effect_budget != 0:
            raise SchemaError("I1 side_effect_budget must be exactly zero")
        budgets = tuple(self.budget_ceilings)
        if not budgets:
            raise SchemaError("budget_ceilings required")
        normalized_budgets = []
        for item in budgets:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise SchemaError("budget entry must be [name, integer]")
            key, value = item
            key = _identifier(key, "budget name")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchemaError("budget values must be non-negative integers")
            normalized_budgets.append((key, value))
        if tuple(normalized_budgets) != tuple(sorted(set(normalized_budgets), key=lambda item: item[0].encode("utf-8"))):
            raise SchemaError("budget_ceilings must be uniquely sorted")
        object.__setattr__(self, "budget_ceilings", tuple(normalized_budgets))
        object.__setattr__(self, "expiry", _timestamp(self.expiry, "expiry"))
        object.__setattr__(self, "cancellation_authority", _identifier(self.cancellation_authority, "cancellation_authority"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "purpose": self.purpose,
            "allowed_operations": list(self.allowed_operations),
            "prohibited_operations": list(self.prohibited_operations),
            "consequence_ceiling": self.consequence_ceiling,
            "budget_ceilings": [[key, value] for key, value in self.budget_ceilings],
            "side_effect_budget": self.side_effect_budget,
            "required_evidence_types": list(self.required_evidence_types),
            "expiry": self.expiry,
            "cancellation_authority": self.cancellation_authority,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MissionScope":
        _require_exact_fields(data, (f.name for f in fields(cls)), "scope")
        values = dict(data)
        values["allowed_operations"] = tuple(values["allowed_operations"])
        values["prohibited_operations"] = tuple(values["prohibited_operations"])
        values["budget_ceilings"] = tuple(tuple(item) for item in values["budget_ceilings"])
        values["required_evidence_types"] = tuple(values["required_evidence_types"])
        return cls(**values)


@dataclass(frozen=True)
class TransitionRequest:
    mission_id: str
    idempotency_key: str
    expected_version: int
    expected_state: MissionState
    expected_previous_event_sha256: str
    to_state: MissionState
    reason: str
    evidence_sha256: str
    actor_reference: str
    cancellation_authority_reference: Optional[str] = None
    transition_request_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mission_id", _identifier(self.mission_id, "mission_id"))
        object.__setattr__(self, "idempotency_key", _identifier(self.idempotency_key, "idempotency_key"))
        if isinstance(self.expected_version, bool) or not isinstance(self.expected_version, int) or self.expected_version < 0:
            raise SchemaError("expected_version is required and must be non-negative")
        if not isinstance(self.expected_state, MissionState) or not isinstance(self.to_state, MissionState):
            raise SchemaError("expected_state and to_state must be MissionState")
        object.__setattr__(self, "expected_previous_event_sha256", _hash(self.expected_previous_event_sha256, "expected_previous_event_sha256"))
        object.__setattr__(self, "evidence_sha256", _hash(self.evidence_sha256, "evidence_sha256"))
        object.__setattr__(self, "actor_reference", _identifier(self.actor_reference, "actor_reference"))
        if not isinstance(self.reason, str) or not self.reason:
            raise SchemaError("transition reason required")
        object.__setattr__(self, "reason", unicodedata.normalize("NFC", self.reason))
        if self.cancellation_authority_reference is not None:
            object.__setattr__(self, "cancellation_authority_reference", _identifier(self.cancellation_authority_reference, "cancellation_authority_reference"))
        digest = sha256_domain(TRANSITION_REQUEST_HASH_DOMAIN, self.to_dict(include_hash=False))
        if self.transition_request_sha256 and self.transition_request_sha256 != digest:
            raise IntegrityError("transition request hash mismatch")
        object.__setattr__(self, "transition_request_sha256", digest)

    def to_dict(self, *, include_hash: bool = True) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "mission_id": self.mission_id,
            "idempotency_key": self.idempotency_key,
            "expected_version": self.expected_version,
            "expected_state": self.expected_state.value,
            "expected_previous_event_sha256": self.expected_previous_event_sha256,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "evidence_sha256": self.evidence_sha256,
            "actor_reference": self.actor_reference,
            "cancellation_authority_reference": self.cancellation_authority_reference,
        }
        if include_hash:
            result["transition_request_sha256"] = self.transition_request_sha256
        return result


@dataclass(frozen=True)
class MissionEvent:
    schema_version: str
    event_index: int
    mission_id: str
    idempotency_key: str
    transition_request_sha256: str
    from_state: MissionState
    to_state: MissionState
    committed_at: str
    reason: str
    evidence_sha256: str
    actor_reference: str
    previous_event_sha256: str
    event_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != EVENT_SCHEMA_VERSION:
            raise SchemaError("invalid event schema version")
        if isinstance(self.event_index, bool) or not isinstance(self.event_index, int) or self.event_index < 1:
            raise SchemaError("event_index must be positive")
        object.__setattr__(self, "mission_id", _identifier(self.mission_id, "mission_id"))
        object.__setattr__(self, "idempotency_key", _identifier(self.idempotency_key, "idempotency_key"))
        object.__setattr__(self, "transition_request_sha256", _hash(self.transition_request_sha256, "transition_request_sha256"))
        object.__setattr__(self, "committed_at", _timestamp(self.committed_at, "committed_at"))
        object.__setattr__(self, "evidence_sha256", _hash(self.evidence_sha256, "evidence_sha256"))
        object.__setattr__(self, "actor_reference", _identifier(self.actor_reference, "actor_reference"))
        object.__setattr__(self, "previous_event_sha256", _hash(self.previous_event_sha256, "previous_event_sha256"))
        digest = sha256_domain(EVENT_HASH_DOMAIN, self.to_dict(include_hash=False))
        if self.event_sha256 and self.event_sha256 != digest:
            raise IntegrityError("event hash mismatch")
        object.__setattr__(self, "event_sha256", digest)

    def to_dict(self, *, include_hash: bool = True) -> Dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "event_index": self.event_index,
            "mission_id": self.mission_id,
            "idempotency_key": self.idempotency_key,
            "transition_request_sha256": self.transition_request_sha256,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "committed_at": self.committed_at,
            "reason": self.reason,
            "evidence_sha256": self.evidence_sha256,
            "actor_reference": self.actor_reference,
            "previous_event_sha256": self.previous_event_sha256,
        }
        if include_hash:
            result["event_sha256"] = self.event_sha256
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MissionEvent":
        _require_exact_fields(data, (f.name for f in fields(cls)), "event")
        values = dict(data)
        try:
            values["from_state"] = MissionState(values["from_state"])
            values["to_state"] = MissionState(values["to_state"])
        except ValueError as exc:
            raise SchemaError("unknown event state") from exc
        return cls(**values)


@dataclass(frozen=True)
class MissionAggregate:
    schema_version: str
    identity: MissionIdentity
    scope: MissionScope
    created_at: str
    current_state: MissionState
    version: int
    previous_event_sha256: str
    events: Tuple[MissionEvent, ...]
    idempotency_index: Tuple[Tuple[str, str, int], ...]
    terminal: bool
    cancelled: bool
    aggregate_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != AGGREGATE_SCHEMA_VERSION:
            raise SchemaError("invalid aggregate schema version")
        object.__setattr__(self, "created_at", _timestamp(self.created_at, "created_at"))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 0:
            raise SchemaError("invalid aggregate version")
        object.__setattr__(self, "previous_event_sha256", _hash(self.previous_event_sha256, "previous_event_sha256"))
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "idempotency_index", tuple(tuple(item) for item in self.idempotency_index))
        digest = sha256_domain(AGGREGATE_HASH_DOMAIN, self.to_dict(include_hash=False))
        if self.aggregate_sha256 and self.aggregate_sha256 != digest:
            raise IntegrityError("aggregate hash mismatch")
        object.__setattr__(self, "aggregate_sha256", digest)

    @classmethod
    def genesis(cls, identity: MissionIdentity, scope: MissionScope, created_at: str) -> "MissionAggregate":
        return cls(
            schema_version=AGGREGATE_SCHEMA_VERSION,
            identity=identity,
            scope=scope,
            created_at=created_at,
            current_state=MissionState.RECEIVED,
            version=0,
            previous_event_sha256=GENESIS_PREVIOUS_EVENT_SHA256,
            events=(),
            idempotency_index=(),
            terminal=False,
            cancelled=False,
        )

    def to_dict(self, *, include_hash: bool = True) -> Dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "scope": self.scope.to_dict(),
            "created_at": self.created_at,
            "current_state": self.current_state.value,
            "version": self.version,
            "previous_event_sha256": self.previous_event_sha256,
            "events": [event.to_dict() for event in self.events],
            "idempotency_index": [[key, request_hash, event_index] for key, request_hash, event_index in self.idempotency_index],
            "terminal": self.terminal,
            "cancelled": self.cancelled,
        }
        if include_hash:
            result["aggregate_sha256"] = self.aggregate_sha256
        return result

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MissionAggregate":
        _require_exact_fields(data, (f.name for f in fields(cls)), "aggregate")
        values = dict(data)
        values["identity"] = MissionIdentity.from_dict(values["identity"])
        values["scope"] = MissionScope.from_dict(values["scope"])
        try:
            values["current_state"] = MissionState(values["current_state"])
        except ValueError as exc:
            raise SchemaError("unknown aggregate state") from exc
        values["events"] = tuple(MissionEvent.from_dict(item) for item in values["events"])
        values["idempotency_index"] = tuple(tuple(item) for item in values["idempotency_index"])
        aggregate = cls(**values)
        aggregate.verify_integrity()
        return aggregate

    @classmethod
    def from_bytes(cls, raw: bytes) -> "MissionAggregate":
        data = strict_json_loads(raw)
        aggregate = cls.from_dict(data)
        if aggregate.canonical_bytes() != raw:
            raise SchemaError("stored mission document is not canonical JSON")
        return aggregate

    def verify_integrity(self) -> None:
        if self.scope.side_effect_budget != 0:
            raise IntegrityError("side effect budget changed")
        if self.version != len(self.events):
            raise IntegrityError("aggregate version does not equal event count")
        previous = GENESIS_PREVIOUS_EVENT_SHA256
        rebuilt = []
        state = MissionState.RECEIVED
        for expected_index, event in enumerate(self.events, start=1):
            if event.event_index != expected_index:
                raise IntegrityError("event index gap or reordering")
            if event.mission_id != self.identity.mission_id:
                raise IntegrityError("event mission identity mismatch")
            if event.previous_event_sha256 != previous:
                raise IntegrityError("event chain gap")
            if event.from_state != state:
                raise IntegrityError("event state linkage mismatch")
            # Reconstructing verifies the event's supplied hash.
            MissionEvent.from_dict(event.to_dict())
            previous = event.event_sha256
            state = event.to_state
            rebuilt.append((event.idempotency_key, event.transition_request_sha256, event.event_index))
        if self.previous_event_sha256 != previous:
            raise IntegrityError("aggregate chain head mismatch")
        if self.current_state != state:
            raise IntegrityError("aggregate state mismatch")
        if tuple(rebuilt) != self.idempotency_index:
            raise IntegrityError("idempotency index mismatch")
        if self.cancelled != (self.current_state is MissionState.CANCELLED):
            raise IntegrityError("cancelled marker mismatch")
        from .state import is_terminal
        if self.terminal != is_terminal(self.current_state):
            raise IntegrityError("terminal marker mismatch")
        expected = sha256_domain(AGGREGATE_HASH_DOMAIN, self.to_dict(include_hash=False))
        if expected != self.aggregate_sha256:
            raise IntegrityError("aggregate hash mismatch")

    def replay_event(self, key: str) -> Optional[MissionEvent]:
        for event in self.events:
            if event.idempotency_key == key:
                return event
        return None

    def immutable_fingerprint(self) -> bytes:
        return canonical_bytes({
            "identity": self.identity.to_dict(),
            "scope": self.scope.to_dict(),
            "created_at": self.created_at,
        })
