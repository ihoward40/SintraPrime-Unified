"""Pydantic contracts for the Hermes Quicksilver adapter.

Increment One uses these models for deterministic, fail-closed mapping from
SintraPrime specialists to Hermes profiles and for redacted audit events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskCeiling(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    PENDING = "pending"
    TIMEOUT = "timeout"
    ERROR = "error"


class HermesProfileDescriptor(BaseModel):
    """Read-only metadata for a Hermes profile."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    display_name: str
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    model: str | None = None
    provider: str | None = None
    source_path: str | None = None


class SpecialistProfileMapping(BaseModel):
    """SintraPrime-owned contract linking a specialist to a Hermes profile."""

    model_config = ConfigDict(frozen=True)

    specialist_id: str = Field(..., min_length=1, max_length=128)
    hermes_profile_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    display_name: str = Field(..., min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    allowed_tool_classes: list[str] = Field(default_factory=list)
    prohibited_tool_classes: list[str] = Field(default_factory=list)
    risk_ceiling: RiskCeiling = RiskCeiling.LOW
    tenant_scope: list[str] = Field(default_factory=list)
    enabled: bool = False
    minimum_hermes_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+")
    maximum_hermes_version: str | None = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    metadata_version: str = "1.0.0"

    @model_validator(mode="after")
    def validate_tool_class_disjoint(self) -> SpecialistProfileMapping:
        allowed = set(self.allowed_tool_classes)
        prohibited = set(self.prohibited_tool_classes)
        overlap = allowed & prohibited
        if overlap:
            raise ValueError(f"tool classes overlap: {sorted(overlap)}")
        if not self.tenant_scope:
            raise ValueError("tenant_scope must contain at least one tenant UUID")
        return self


class DelegationRequest(BaseModel):
    """A request to perform a read-only Hermes operation through the adapter."""

    model_config = ConfigDict(frozen=True)

    operation: str
    specialist_id: str
    tenant_id: str
    actor_id: str
    case_id: str | None = None
    correlation_id: str = Field(default_factory=lambda: _utc_now_iso())
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ResolvedMapping(BaseModel):
    """Outcome of resolving a specialist + tenant to a Hermes profile."""

    model_config = ConfigDict(frozen=True)

    specialist_id: str
    tenant_id: str
    hermes_profile_id: str
    hermes_profile: HermesProfileDescriptor | None = None
    decision: Decision
    reason_code: str | None = None
    duration_ms: int = 0


class HardDenyResult(BaseModel):
    """Outcome of hard-deny evaluation."""

    model_config = ConfigDict(frozen=True)

    denied: bool
    reason_code: str | None = None
    matched_rules: list[str] = Field(default_factory=list)


class DelegationResult(BaseModel):
    """Outcome of a read-only delegation attempt."""

    model_config = ConfigDict(frozen=True)

    operation: str
    decision: Decision
    reason_code: str | None = None
    data: dict[str, Any] | None = None
    duration_ms: int = 0


class HermesDelegationAuditEvent(BaseModel):
    """Redacted audit event emitted for every delegation attempt."""

    model_config = ConfigDict(frozen=True)

    event_type: str
    event_version: str = "1.0.0"
    occurred_at: str = Field(default_factory=lambda: _utc_now_iso())
    tenant_id: str
    actor_id: str
    case_id: str | None = None
    correlation_id: str
    session_id: str | None = None
    specialist_id: str
    hermes_profile_id: str | None = None
    operation: str
    decision: Decision
    policy_reason_code: str | None = None
    approval_reference: str | None = None
    result_status: str | None = None
    error_class: str | None = None
    duration_ms: int = 0
    source_version: str
    redaction_version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        # Deterministic serialization: no secrets, no raw payloads.
        return self.model_dump(exclude_none=False)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
