"""GOD-2 capability admission: classify, constrain, and fail closed.

This module deliberately admits no capability by default. A registered
capability is only executable after an explicit admission state, authority
intersection, resource scope, precondition, and approval check all pass.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class EffectClass(StrEnum):
    E0 = "EXTERNAL_READ_ONLY"
    E1 = "EXTERNAL_DRAFT_ONLY"
    E2 = "EXTERNAL_REVERSIBLE_LOW_RISK"
    E3 = "EXTERNAL_IRREVERSIBLE"
    E4 = "FINANCIAL"
    E5 = "LEGAL_REGULATORY_SUBMISSION"
    E6 = "CREDENTIAL_AUTH_MUTATION"
    E7 = "DEPLOYMENT_INFRASTRUCTURE"
    E8 = "SECURITY_PRIVILEGE_MUTATION"


class AdmissionState(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    SHADOW_ONLY = "SHADOW_ONLY"
    ADMITTED = "ADMITTED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class AdmissionDeniedError(PermissionError):
    """Every failed admission check is an intentional denial."""


@dataclass(frozen=True)
class CapabilityAdmission:
    capability_id: str
    tool_id: str
    operation: str
    effect_class: EffectClass
    admission_state: AdmissionState = AdmissionState.UNREVIEWED
    authorized_environments: tuple[str, ...] = ("local",)
    resource_scope: tuple[str, ...] = ()
    approval_policy: str = "REQUIRED"
    rollback_policy: str = "NONE"
    idempotency_policy: str = "REQUIRED"
    verification_policy: str = "REQUIRED"
    owner: str = ""
    reviewed_at: str = ""
    expires_at: str = ""
    revocation_reason: str = ""
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdmissionDecision:
    decision_id: str
    capability_id: str
    effect_class: str
    resource: str
    status: str
    reason: str
    checked_at: float
    evidence_ref: str = ""


class CapabilityAdmissionRegistry:
    """First-class capability registry with explicit, narrow admission."""

    def __init__(self, entries: tuple[CapabilityAdmission, ...] = ()):
        self._entries: dict[str, CapabilityAdmission] = {}
        for entry in entries:
            self.register(entry)

    @classmethod
    def from_json(cls, path: str | Path) -> "CapabilityAdmissionRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(tuple(CapabilityAdmission(
            capability_id=item["capability_id"], tool_id=item["tool_id"], operation=item["operation"],
            effect_class=EffectClass(item["effect_class"]), admission_state=AdmissionState(item.get("admission_state", "UNREVIEWED")),
            authorized_environments=tuple(item.get("authorized_environments", ["local"])), resource_scope=tuple(item.get("resource_scope", [])),
            approval_policy=item.get("approval_policy", "REQUIRED"), rollback_policy=item.get("rollback_policy", "NONE"),
            idempotency_policy=item.get("idempotency_policy", "REQUIRED"), verification_policy=item.get("verification_policy", "REQUIRED"),
            owner=item.get("owner", ""), reviewed_at=item.get("reviewed_at", ""), expires_at=item.get("expires_at", ""),
            revocation_reason=item.get("revocation_reason", ""), evidence_refs=tuple(item.get("evidence_refs", [])),
        ) for item in data["capabilities"]))

    def register(self, entry: CapabilityAdmission) -> None:
        if entry.capability_id in self._entries:
            raise ValueError(f"duplicate capability: {entry.capability_id}")
        if entry.effect_class in {EffectClass.E3, EffectClass.E4, EffectClass.E5, EffectClass.E6, EffectClass.E7, EffectClass.E8} and entry.admission_state == AdmissionState.ADMITTED:
            raise ValueError("E3-E8 cannot be admitted in GOD-2")
        self._entries[entry.capability_id] = entry

    def resolve(self, capability_id: str) -> CapabilityAdmission:
        try:
            return self._entries[capability_id]
        except KeyError as exc:
            raise AdmissionDeniedError(f"UNREVIEWED_CAPABILITY: {capability_id}") from exc

    def list(self) -> tuple[CapabilityAdmission, ...]:
        return tuple(self._entries.values())

    def revoke(self, capability_id: str, reason: str) -> None:
        entry = self.resolve(capability_id)
        self._entries[capability_id] = CapabilityAdmission(**{**entry.__dict__, "admission_state": AdmissionState.REVOKED, "revocation_reason": reason})

    def decide(self, *, capability_id: str, agent_authorized: bool, mission_authorized: bool, resource: str, environment: str, approval_satisfied: bool, preconditions_pass: bool, effect_class: EffectClass | None = None, evidence_ref: str = "") -> AdmissionDecision:
        entry = self.resolve(capability_id)
        requested = effect_class or entry.effect_class
        reason = "admitted"
        ok = True
        if requested != entry.effect_class: reason = "STATIC_EFFECT_CLASS_MISMATCH"; ok = False
        elif entry.admission_state != AdmissionState.ADMITTED: reason = f"CAPABILITY_NOT_ADMITTED:{entry.admission_state.value}"; ok = False
        elif environment not in entry.authorized_environments: reason = "ENVIRONMENT_NOT_AUTHORIZED"; ok = False
        elif entry.resource_scope and not any(resource == scope or resource.startswith(scope.rstrip("*")) for scope in entry.resource_scope): reason = "RESOURCE_SCOPE_DENIED"; ok = False
        elif not mission_authorized: reason = "MISSION_NOT_AUTHORIZED"; ok = False
        elif not agent_authorized: reason = "AGENT_NOT_AUTHORIZED"; ok = False
        elif not preconditions_pass: reason = "PRECONDITIONS_FAILED"; ok = False
        elif entry.approval_policy == "REQUIRED" and not approval_satisfied: reason = "APPROVAL_REQUIRED"; ok = False
        return AdmissionDecision(uuid.uuid4().hex, capability_id, requested.value, resource, "ADMITTED" if ok else "DENIED", reason, time.time(), evidence_ref)

    def require(self, **kwargs: Any) -> AdmissionDecision:
        decision = self.decide(**kwargs)
        if decision.status != "ADMITTED":
            raise AdmissionDeniedError(decision.reason)
        return decision


def arguments_hash(arguments: Any) -> str:
    return hashlib.sha256(json.dumps(arguments, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
