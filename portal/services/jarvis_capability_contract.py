"""JARVIS-001-B2-B1 immutable capability contract kernel."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

CONTRACT_SCHEMA_VERSION = "1"
CANONICALIZATION_VERSION = "1"
SUPPORTED_CONTRACT_SCHEMA_VERSIONS = frozenset({"1"})
SUPPORTED_CANONICALIZATION_VERSIONS = frozenset({"1"})

_IDENTIFIER_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_WILDCARD_RE = re.compile(r"[*?]")
_SECRET_NAME_RE = re.compile(
    r"(?:api[_-]?key|token|password|secret|authorization|bearer|private[_-]?key|credential)",
    re.IGNORECASE,
)
_SECRET_VALUE_MARKERS = ("ghp_", "ghs_", "gho_", "github_pat_", "sk-", "redacted:")

_AUTHORITATIVE_FIELDS = frozenset(
    {
        "capability_id",
        "capability_version",
        "allowed_operations",
        "allowed_targets",
        "risk",
        "consequence",
        "authority",
        "credential",
        "executor_id",
        "adapter_id",
        "verification",
        "idempotency",
        "reconciliation",
        "rollback",
        "lease",
        "revocation",
        "receipt",
        "memory",
        "brief",
        "contract_schema_version",
        "canonicalization_version",
    }
)
_REQUIRED_FIELDS = _AUTHORITATIVE_FIELDS - {"contract_schema_version", "canonicalization_version"}


def _reject(message: str) -> None:
    raise ValueError(message)


def _validate_identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        _reject(f"invalid lowercase identifier for {name}")
    return value


def _validate_collection(name: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, frozenset)):
        _reject(f"{name} must be a non-empty collection")
    if not value:
        _reject(f"{name} cannot be empty")
    members = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            _reject(f"{name} contains null or blank entry")
        if _WILDCARD_RE.search(item):
            _reject(f"{name} contains wildcard entry")
        if item != item.strip():
            _reject(f"{name} contains ambiguous whitespace")
        if item in members:
            _reject(f"{name} contains duplicate entry")
        members.append(item)
    return tuple(sorted(members))


def _contains_secret(field_name: str, value: Any) -> bool:
    if _SECRET_NAME_RE.search(field_name):
        return field_name not in {"credential"}
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in _SECRET_VALUE_MARKERS):
            return True
        if re.search(r"[a-zA-Z0-9_-]{32,}", value):
            return True
    return False


def canonical_contract_hash(contract: CapabilityContract) -> str:
    payload = {
        field: getattr(contract, field)
        for field in sorted(_AUTHORITATIVE_FIELDS)
    }
    payload["allowed_operations"] = list(contract.allowed_operations)
    payload["allowed_targets"] = list(contract.allowed_targets)
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    capability_version: str
    allowed_operations: tuple[str, ...]
    allowed_targets: tuple[str, ...]
    risk: str
    consequence: str
    authority: str
    credential: str
    executor_id: str
    adapter_id: str
    verification: str
    idempotency: str
    reconciliation: str
    rollback: str
    lease: str
    revocation: str
    receipt: str
    memory: str
    brief: str
    contract_schema_version: str = CONTRACT_SCHEMA_VERSION
    canonicalization_version: str = CANONICALIZATION_VERSION

    def __post_init__(self) -> None:
        fields = set(self.__dict__)
        unknown = fields - _AUTHORITATIVE_FIELDS
        missing = _REQUIRED_FIELDS - fields
        if unknown:
            _reject(f"unknown authoritative fields: {sorted(unknown)}")
        if missing:
            _reject(f"missing required fields: {sorted(missing)}")
        if self.contract_schema_version not in SUPPORTED_CONTRACT_SCHEMA_VERSIONS:
            _reject("unsupported contract schema version")
        if self.canonicalization_version not in SUPPORTED_CANONICALIZATION_VERSIONS:
            _reject("unsupported canonicalization version")
        _validate_identifier("capability_id", self.capability_id)
        _validate_identifier("executor_id", self.executor_id)
        _validate_identifier("adapter_id", self.adapter_id)
        object.__setattr__(self, "allowed_operations", _validate_collection("allowed_operations", self.allowed_operations))
        object.__setattr__(self, "allowed_targets", _validate_collection("allowed_targets", self.allowed_targets))
        for field, value in self.__dict__.items():
            if _contains_secret(field, value):
                _reject(f"secret-like material is not allowed in field {field}")
        for field in _REQUIRED_FIELDS - {"allowed_operations", "allowed_targets", "capability_id", "capability_version", "executor_id", "adapter_id"}:
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                _reject(f"required field {field} is empty or invalid")

    @property
    def contract_hash(self) -> str:
        return canonical_contract_hash(self)
