"""Principal Command (God Mode) governance for the PARL orchestration layer.

God Mode is a Principal capability, never an agent capability.  This module
keeps elevated orchestration explicit, short-lived, least-privileged, and
independent from any model/provider implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Any, Iterable, Mapping, Optional


class GodModeTier(IntEnum):
    """Principal Command capability tiers."""

    GLOBAL_READ = 0
    GLOBAL_ORCHESTRATION = 1
    CONTROLLED_WRITE = 2
    EXTERNAL_ACTION = 3
    CRITICAL_ADMIN = 4


class ActionRisk(StrEnum):
    """Normalized action risk classes understood by the central router."""

    READ = "read"
    ORCHESTRATE = "orchestrate"
    WRITE = "write"
    EXTERNAL = "external"
    CRITICAL = "critical"


_MINIMUM_TIER = {
    ActionRisk.READ: GodModeTier.GLOBAL_READ,
    ActionRisk.ORCHESTRATE: GodModeTier.GLOBAL_ORCHESTRATION,
    ActionRisk.WRITE: GodModeTier.CONTROLLED_WRITE,
    ActionRisk.EXTERNAL: GodModeTier.EXTERNAL_ACTION,
    ActionRisk.CRITICAL: GodModeTier.CRITICAL_ADMIN,
}

_NEVER_DELEGATE = frozenset(
    {
        "disable_governance",
        "self_elevate",
        "reveal_secrets",
        "export_raw_credentials",
        "bypass_approval",
    }
)


@dataclass(frozen=True)
class PrincipalSession:
    """Short-lived authenticated Principal Command session."""

    principal_id: str
    tier: GodModeTier
    expires_at: datetime
    authenticated: bool = True
    step_up_verified: bool = False
    capabilities: frozenset[str] = field(default_factory=frozenset)

    @property
    def expired(self) -> bool:
        now = datetime.now(timezone.utc)
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return now >= expiry


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    approval_required: bool = False
    minimum_tier: GodModeTier = GodModeTier.GLOBAL_READ


class PrincipalCommandPolicy:
    """Fail-closed evaluator for elevated PARL work.

    Ordinary read/orchestration remains backward compatible.  Write,
    external, and critical work can only be admitted when a valid Principal
    session is supplied.  Admission never substitutes for the downstream
    approval gateway: external and critical actions remain approval-gated.
    """

    def evaluate(
        self,
        *,
        risk: ActionRisk | str,
        session: Optional[PrincipalSession],
        requested_capability: Optional[str] = None,
    ) -> PolicyDecision:
        risk = ActionRisk(risk)
        minimum = _MINIMUM_TIER[risk]

        if requested_capability in _NEVER_DELEGATE:
            return PolicyDecision(False, "capability is non-delegable", minimum_tier=minimum)

        if risk in (ActionRisk.READ, ActionRisk.ORCHESTRATE) and session is None:
            return PolicyDecision(True, "ordinary non-privileged execution", minimum_tier=minimum)

        if session is None:
            return PolicyDecision(False, "principal session required", minimum_tier=minimum)
        if not session.authenticated:
            return PolicyDecision(False, "principal session is not authenticated", minimum_tier=minimum)
        if session.expired:
            return PolicyDecision(False, "principal session expired", minimum_tier=minimum)
        if session.tier < minimum:
            return PolicyDecision(False, "principal session tier is insufficient", minimum_tier=minimum)
        if requested_capability and session.capabilities and requested_capability not in session.capabilities:
            return PolicyDecision(False, "capability is outside the session scope", minimum_tier=minimum)
        if risk is ActionRisk.CRITICAL and not session.step_up_verified:
            return PolicyDecision(False, "critical action requires step-up verification", minimum_tier=minimum)

        approval_required = risk in (ActionRisk.EXTERNAL, ActionRisk.CRITICAL)
        return PolicyDecision(
            True,
            "principal command policy admitted task",
            approval_required=approval_required,
            minimum_tier=minimum,
        )

    def authorize_specs(
        self,
        specs: Iterable[Mapping[str, Any]],
        *,
        session: Optional[PrincipalSession],
    ) -> None:
        """Validate every subtask specification before any worker is spawned.

        A spec may declare ``risk_level`` and ``capability`` at the top level
        or inside its payload.  Missing risk defaults to ``orchestrate`` so
        existing PARL callers continue to work unchanged.
        """

        for spec in specs:
            payload = spec.get("payload", {}) or {}
            risk = spec.get("risk_level", payload.get("risk_level", ActionRisk.ORCHESTRATE))
            capability = spec.get("capability", payload.get("capability"))
            decision = self.evaluate(risk=risk, session=session, requested_capability=capability)
            if not decision.allowed:
                raise PermissionError(f"Principal Command denied subtask: {decision.reason}")
            if decision.approval_required:
                payload_approval = payload.get("approval_granted", False)
                if not payload_approval:
                    raise PermissionError(
                        "Principal Command admitted the capability, but downstream approval is required"
                    )
