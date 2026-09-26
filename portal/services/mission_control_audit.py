"""Mission Control audit integration (SP-GOD0-MISSION-CONTROL-001 Phase 14).

Every Mission Control mutation (approval decisions, evidence requests,
cancellations) must itself produce an audit event. Mission Control is part
of the evidence chain, not exempt from it.

This module adapts governance.AuditTrail to Mission Control actions and
adds the principal_actor / previous_state / new_state fields the directive
requires. It never mutates runtime authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timezone


@dataclass(frozen=True)
class MissionControlAuditEvent:
    principal_actor: str
    action: str                 # APPROVE | DENY | REQUEST_MORE_EVIDENCE | CANCEL_MISSION
    target: str
    mission_id: str
    timestamp: datetime
    previous_state: str
    new_state: str
    authority_basis: str        # the registered authority/envelope origin
    receipt: str | None = None  # resulting approval/receipt id, if any


def record_mission_control_action(
    audit_trail,  # governance.AuditTrail (duck-typed; kept injectable for tests)
    *,
    principal_actor: str,
    action: str,
    target: str,
    mission_id: str,
    previous_state: str,
    new_state: str,
    authority_basis: str,
    receipt: str | None = None,
    now: datetime | None = None,
) -> MissionControlAuditEvent:
    """Record a Mission Control control-plane action in the audit trail.

    The returned event is the canonical record; callers must not construct
    their own divergent audit rows for the same action.
    """
    event = MissionControlAuditEvent(
        principal_actor=principal_actor,
        action=action,
        target=target,
        mission_id=mission_id,
        timestamp=now or datetime.now(UTC),
        previous_state=previous_state,
        new_state=new_state,
        authority_basis=authority_basis,
        receipt=receipt,
    )
    audit_trail.log(
        actor=principal_actor,
        action=f"MISSION_CONTROL_{action}",
        outcome=new_state,
        risk_level=_risk_for(action),
        approval_id=receipt,
        metadata={
            "target": target,
            "mission_id": mission_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "authority_basis": authority_basis,
            "surface": "god0-mission-control",
        },
    )
    return event


def _risk_for(action: str):
    # Local import keeps the mapping adjacent to usage; RiskLevel lives in
    # governance.risk_types.
    from governance.risk_types import RiskLevel

    if action in {"APPROVE", "DENY"}:
        return RiskLevel.HIGH
    if action == "CANCEL_MISSION":
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def events_differ_only_by(a: MissionControlAuditEvent,
                          b: MissionControlAuditEvent,
                          fields: set[str]) -> bool:
    """Test helper: compare two events ignoring volatile fields."""
    ignore = {"timestamp"} | fields
    da, db = a.__dict__, b.__dict__
    return all(da[k] == db[k] for k in da if k not in ignore)
