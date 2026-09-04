"""JARVIS-001-B1 action-bound approval (B1-2).

Composes the real Mission Control approval architecture patterns:
TenantPrincipal validation, tenant scoping, exactly-once consumption.
Binds one approval to exactly one action_id + params_hash. NOT the
agents/nova or governance/approval_gate demo gateways (B0 verdict).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from .jarvis_action_taxonomy import ActionFailure

APPROVAL_TTL_SECONDS = 900


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def approval_token_for(artifact: ActionApprovalArtifact) -> str:
    """Opaque executor-presentable token bound to one approval artifact."""
    return f"jarvis-b1-approval:{artifact.approval_id}"


@dataclass
class ActionApprovalArtifact:
    approval_id: str
    action_id: str
    tenant_id: str
    params_hash: str
    principal_user_id: str
    status: str  # PENDING -> APPROVED -> CONSUMED | REJECTED
    created_at: str
    consumed_at: str | None
    approved_at: str | None = None


class _ActionApprovalRegistry:
    """Process-local artifact store. B1 proves the enforcement order, not the
    storage engine; consumption state machine mirrors RunApproval semantics."""

    def __init__(self) -> None:
        self._by_action: dict[str, ActionApprovalArtifact] = {}
        self._by_approval: dict[str, ActionApprovalArtifact] = {}

    def create(self, *, action_id: str, tenant_id: str, params_hash: str, principal_user_id: str) -> ActionApprovalArtifact:
        for existing in self._by_action.values():
            if existing.action_id == action_id and existing.status == "PENDING":
                raise ActionFailure("APPROVAL_MISMATCH", "approval already exists for action")
        artifact = ActionApprovalArtifact(
            approval_id=f"appr-{uuid.uuid4()}",
            action_id=action_id,
            tenant_id=tenant_id,
            params_hash=params_hash,
            principal_user_id=principal_user_id,
            status="PENDING",
            created_at=_now_iso(),
            consumed_at=None,
        )
        self._by_action[action_id] = artifact
        self._by_approval[artifact.approval_id] = artifact
        return artifact

    def get_by_approval_id(self, approval_id: str) -> ActionApprovalArtifact | None:
        return self._by_approval.get(approval_id)

    def all(self) -> list:
        return list(self._by_approval.values())


_REGISTRY = _ActionApprovalRegistry()


def reset_registry_for_tests() -> None:
    """B1 test isolation: drop all artifacts (single-process only)."""
    _REGISTRY.__init__()


async def create_action_approval(db, *, action, tenant_id: str, principal_user_id: str) -> ActionApprovalArtifact:
    """Create a PENDING approval bound to action_id + params_hash.

    Principal authority is verified with the real TenantPrincipal service —
    the same constitutional check mission_control uses. Fails closed.
    """
    from .tenant_principal_service import is_tenant_principal

    ok = await is_tenant_principal(
        db, authenticated_user_id=principal_user_id, tenant_id=tenant_id
    )
    if not ok:
        raise ActionFailure("AUTHORITY_DENIED", "actor is not the tenant Principal")
    return _REGISTRY.create(
        action_id=action.action_id,
        tenant_id=tenant_id,
        params_hash=action.params_hash,
        principal_user_id=principal_user_id,
    )


async def approve_action(db, *, artifact: ActionApprovalArtifact, decision: str, principal_user_id: str) -> ActionApprovalArtifact:
    """Record the Principal decision on the artifact (fail closed)."""
    if artifact.status != "PENDING":
        raise ActionFailure("APPROVAL_MISMATCH", f"artifact status {artifact.status}")
    if principal_user_id != artifact.principal_user_id:
        raise ActionFailure("AUTHORITY_DENIED", "decider is not the artifact principal")
    if decision != "APPROVED":
        artifact.status = "REJECTED"
    else:
        artifact.status = "APPROVED"
        artifact.approved_at = datetime.now(UTC).isoformat()
    return artifact


async def consume_action_approval(db, *, artifact: ActionApprovalArtifact) -> ActionApprovalArtifact:
    """Exactly-once consumption: PENDING -> CONSUMED."""
    if artifact.status == "CONSUMED":
        raise ActionFailure("APPROVAL_REPLAY")
    if artifact.status == "PENDING":
        raise ActionFailure("APPROVAL_MISSING", "approval not yet granted")
    if artifact.status != "APPROVED":
        raise ActionFailure("APPROVAL_MISMATCH")
    artifact.status = "CONSUMED"
    artifact.consumed_at = _now_iso()
    return artifact
