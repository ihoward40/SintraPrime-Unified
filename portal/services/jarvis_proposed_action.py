"""JARVIS-001-B1 canonical mission-bound ProposedAction (B1-1).

Frozen proposal object with deterministic canonical params hash.
Tenant-, mission-, and request-bound. Action types are allowlisted
(B1: github.issue.add_label only). Extra fields are forbidden.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .jarvis_action_taxonomy import ActionFailure

ALLOWED_ACTION_TYPES = frozenset({"github.issue.add_label"})

_RISK_CLASSES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
_CONSEQUENCE_CLASSES = frozenset({"REVERSIBLE", "PARTIALLY_REVERSIBLE", "IRREVERSIBLE"})
_MAX_PARAMS_BYTES = 8 * 1024


def canonical_params_hash(parameters: dict) -> str:
    """Deterministic SHA-256 over the canonical JSON of the parameters."""
    payload = json.dumps(parameters, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deterministic_action_id(mission_id=None, action_type=None, parameters=None, **kw) -> str:
    """action_id is derived from mission + type + params (no hidden entropy)."""
    payload = "\n".join([mission_id, action_type, canonical_params_hash(parameters)])
    return hashlib.sha256(payload.encode()).hexdigest()


def new_proposed_action(
    *,
    action_type: str,
    mission_id: str,
    request_id: str,
    tenant_id: str,
    proposed_by: str,
    parameters: dict,
    evidence_refs: tuple | list = (),
    reasoning_refs: tuple | list = (),
    risk_class: str = "LOW",
    consequence_class: str = "REVERSIBLE",
) -> ProposedAction:
    """Server-side constructor: validates, hashes, and freezes the proposal."""
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ActionFailure("ACTION_TYPE_NOT_ALLOWLISTED")
    allowed_keys = {"target_system", "target_resource", "operation", "label"}
    if isinstance(parameters, dict) and set(parameters) - allowed_keys:
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    if not isinstance(parameters, dict) or not parameters:
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    target_system = parameters.get("target_system")
    target_resource = parameters.get("target_resource")
    if target_system != "github" or not isinstance(target_resource, str) or not target_resource:
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    if parameters.get("operation") != "add_label":
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    label_value = parameters.get("label")
    if not isinstance(label_value, str) or not label_value.strip():
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    params_hash = canonical_params_hash(parameters)
    action_id = deterministic_action_id(
        mission_id=mission_id, action_type=action_type, parameters=parameters
    )
    return ProposedAction(
        action_id=action_id,
        mission_id=mission_id,
        request_id=str(request_id),
        tenant_id=str(tenant_id),
        action_type=action_type,
        target_system=target_system,
        target_resource=str(target_resource),
        operation=str(parameters.get("operation")),
        parameters=dict(parameters),
        params_hash=params_hash,
        risk_class=risk_class,
        consequence_class=consequence_class,
        authority_required=True,
        approval_required=True,
        proposed_by=str(proposed_by),
        created_at=datetime.now(UTC).isoformat(),
        evidence_refs=tuple(str(x) for x in evidence_refs),
        reasoning_refs=tuple(str(x) for x in reasoning_refs),
    )


@dataclass(frozen=True)
class ProposedAction:
    """Frozen proposal. Construct via new_proposed_action() only."""

    action_id: str
    mission_id: str
    request_id: str
    tenant_id: str
    action_type: str
    target_system: str
    target_resource: str
    operation: str
    parameters: dict
    params_hash: str
    risk_class: str
    consequence_class: str
    authority_required: bool
    approval_required: bool
    proposed_by: str
    created_at: str
    evidence_refs: tuple
    reasoning_refs: tuple

    def __post_init__(self) -> None:
        if self.action_type not in ALLOWED_ACTION_TYPES:
            raise ActionFailure("ACTION_TYPE_NOT_ALLOWLISTED")
        if self.target_system != "github" or self.operation != "add_label":
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if not self.authority_required or not self.approval_required:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if self.risk_class not in _RISK_CLASSES or self.consequence_class not in _CONSEQUENCE_CLASSES:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if self.params_hash != canonical_params_hash(self.parameters):
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if not self.tenant_id or not self.mission_id or not self.request_id:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if not self.proposed_by:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        if len(json.dumps(self.parameters, default=str).encode()) > _MAX_PARAMS_BYTES:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
