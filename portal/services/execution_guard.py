"""
Centralized Execution Guard (G4.7).

Constitutional rule: No consequential action may execute unless it passes
through the centralized execution guard.

The guard evaluates:
    - Global kill-switch state
    - Mission state
    - Action classification (risk level, governance gate, approval requirement)
    - Agent status
    - Principal context (G4.8 placeholder)
    - Requested scope and resource target
    - Applicable exemptions

G4.7 establishes the enforcement boundary. G4.8 will later provide
authenticated principal identity and permissions. Until then, the
principal_context is a placeholder that defaults to unauthenticated.

All denials emit canonical Observatory audit events via the existing
run-scoped hash-chain service (EventService.create).

Usage:
    from portal.services.execution_guard import ExecutionGuard, ExecutionAction

    await ExecutionGuard.require_allowed(
        session=db,
        action=ExecutionAction.FILE_MODIFY,
        mission_id=mission_id,
        agent_id=agent_id,
        resource_type="file",
        resource_id="/path/to/file",
        principal_context=principal_context,
    )
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

POLICY_VERSION = "G4.7.1"
SYSTEM_RUN_ID = "system:execution-guard"


# ═══════════════════════════════════════════════════════════════════════════════
# Action Classification
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionAction(str, enum.Enum):
    """Every consequential and read-only action the guard knows about."""

    # Mission operations
    MISSION_CREATE = "mission.create"
    MISSION_START = "mission.start"
    MISSION_RESUME = "mission.resume"
    MISSION_CANCEL = "mission.cancel"
    MISSION_FREEZE = "mission.freeze"

    # Agent operations
    SUBAGENT_SPAWN = "subagent.spawn"
    TOOL_INVOKE = "tool.invoke"

    # File operations
    FILE_READ = "file.read"
    FILE_CREATE = "file.create"
    FILE_MODIFY = "file.modify"
    FILE_DELETE = "file.delete"

    # Communication
    EXTERNAL_COMMUNICATION = "communication.external"

    # Repository operations
    REPOSITORY_COMMIT = "repository.commit"
    REPOSITORY_PUSH = "repository.push"
    REPOSITORY_MERGE = "repository.merge"

    # Destructive
    DESTRUCTIVE_COMMAND = "command.destructive"

    # Sensitive domains
    FINANCIAL_ACTION = "financial.action"
    LEGAL_SUBMISSION = "legal.submission"
    PRODUCTION_DEPLOYMENT = "deployment.production"
    CREDENTIAL_READ = "credential.read"
    CREDENTIAL_MODIFY = "credential.modify"

    # Identity and approvals
    IDENTITY_ACTION = "identity.action"
    APPROVAL_DECISION = "approval.decision"

    # Kill switch
    KILL_SWITCH_ACTIVATE = "kill_switch.activate"
    KILL_SWITCH_CLEAR = "kill_switch.clear"

    # Read-only evidence paths (exempt from kill-switch block)
    EVIDENCE_READ = "evidence.read"
    EVENT_READ = "event.read"
    REPLAY_READ = "replay.read"
    EXPORT_EVIDENCE = "evidence.export"
    INCIDENT_READ = "incident.read"
    HEALTH_READ = "health.read"


class ActionRiskLevel(str, enum.Enum):
    """Risk classification for each action."""
    READ_ONLY = "READ_ONLY"
    MUTATING = "MUTATING"
    EXTERNAL = "EXTERNAL"
    DESTRUCTIVE = "DESTRUCTIVE"
    PRIVILEGED = "PRIVILEGED"
    EMERGENCY = "EMERGENCY"


class KillSwitchBehavior(str, enum.Enum):
    """How an action behaves when the kill switch is active."""
    BLOCKED = "BLOCKED"        # Action is denied when kill switch is active
    ALLOWED = "ALLOWED"        # Action proceeds even when kill switch is active
    ACTIVATION = "ACTIVATION"  # This is the activation itself — always allowed
    CLEARING = "CLEARING"      # Clearing path — evaluated separately


class ApprovalBehavior(str, enum.Enum):
    """Approval requirement for an action."""
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    CONDITIONAL = "CONDITIONAL"  # Required only under certain conditions


# ═══════════════════════════════════════════════════════════════════════════════
# Policy Table — single authoritative classification map
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ActionPolicy:
    """Classification for a single action type."""
    risk_level: ActionRiskLevel
    governance_gate: Optional[str]      # e.g. "G-05", or None for no gate
    kill_switch: KillSwitchBehavior
    approval: ApprovalBehavior
    mission_state_required: bool        # True if action requires a valid mission context
    description: str


_ACTION_POLICY: dict[ExecutionAction, ActionPolicy] = {
    # ── Mission operations ──
    ExecutionAction.MISSION_CREATE: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate="G-01",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Create a new mission",
    ),
    ExecutionAction.MISSION_START: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate="G-01",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=True,
        description="Start mission execution",
    ),
    ExecutionAction.MISSION_RESUME: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate="G-01",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=True,
        description="Resume a paused mission",
    ),
    ExecutionAction.MISSION_CANCEL: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=True,
        description="Cancel a mission",
    ),
    ExecutionAction.MISSION_FREEZE: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-05",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=True,
        description="Freeze a mission",
    ),

    # ── Agent operations ──
    ExecutionAction.SUBAGENT_SPAWN: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate="G-02",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=True,
        description="Spawn a subagent",
    ),
    ExecutionAction.TOOL_INVOKE: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate="G-07",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.CONDITIONAL,
        mission_state_required=True,
        description="Invoke a tool with side effects",
    ),

    # ── File operations ──
    ExecutionAction.FILE_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read a file",
    ),
    ExecutionAction.FILE_CREATE: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Create a file",
    ),
    ExecutionAction.FILE_MODIFY: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Modify a file",
    ),
    ExecutionAction.FILE_DELETE: ActionPolicy(
        risk_level=ActionRiskLevel.DESTRUCTIVE,
        governance_gate="G-09",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Delete a file",
    ),

    # ── Communication ──
    ExecutionAction.EXTERNAL_COMMUNICATION: ActionPolicy(
        risk_level=ActionRiskLevel.EXTERNAL,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Send external communication",
    ),

    # ── Repository operations ──
    ExecutionAction.REPOSITORY_COMMIT: ActionPolicy(
        risk_level=ActionRiskLevel.MUTATING,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Commit to repository",
    ),
    ExecutionAction.REPOSITORY_PUSH: ActionPolicy(
        risk_level=ActionRiskLevel.EXTERNAL,
        governance_gate="G-08",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Push to remote repository",
    ),
    ExecutionAction.REPOSITORY_MERGE: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-10",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Merge a pull request",
    ),

    # ── Destructive ──
    ExecutionAction.DESTRUCTIVE_COMMAND: ActionPolicy(
        risk_level=ActionRiskLevel.DESTRUCTIVE,
        governance_gate="G-09",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Execute a destructive command",
    ),

    # ── Sensitive domains ──
    ExecutionAction.FINANCIAL_ACTION: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-05",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Execute a financial action",
    ),
    ExecutionAction.LEGAL_SUBMISSION: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-06",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Submit a legal filing",
    ),
    ExecutionAction.PRODUCTION_DEPLOYMENT: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-08",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Deploy to production",
    ),
    ExecutionAction.CREDENTIAL_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read credential metadata (not secrets)",
    ),
    ExecutionAction.CREDENTIAL_MODIFY: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-05",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Modify credentials",
    ),

    # ── Identity and approvals ──
    ExecutionAction.IDENTITY_ACTION: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-02",
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Modify identity or permissions",
    ),
    ExecutionAction.APPROVAL_DECISION: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.BLOCKED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Make an approval decision",
    ),

    # ── Kill switch ──
    ExecutionAction.KILL_SWITCH_ACTIVATE: ActionPolicy(
        risk_level=ActionRiskLevel.EMERGENCY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ACTIVATION,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Activate the global kill switch",
    ),
    ExecutionAction.KILL_SWITCH_CLEAR: ActionPolicy(
        risk_level=ActionRiskLevel.PRIVILEGED,
        governance_gate="G-05",
        kill_switch=KillSwitchBehavior.CLEARING,
        approval=ApprovalBehavior.REQUIRED,
        mission_state_required=False,
        description="Clear the global kill switch",
    ),

    # ── Read-only evidence paths (exempt) ──
    ExecutionAction.EVIDENCE_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read evidence",
    ),
    ExecutionAction.EVENT_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read observatory events",
    ),
    ExecutionAction.REPLAY_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Replay event chain",
    ),
    ExecutionAction.EXPORT_EVIDENCE: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Export evidence package",
    ),
    ExecutionAction.INCIDENT_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read incident records",
    ),
    ExecutionAction.HEALTH_READ: ActionPolicy(
        risk_level=ActionRiskLevel.READ_ONLY,
        governance_gate=None,
        kill_switch=KillSwitchBehavior.ALLOWED,
        approval=ApprovalBehavior.NOT_REQUIRED,
        mission_state_required=False,
        description="Read system health status",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Mission-State Policy (table-driven)
# ═══════════════════════════════════════════════════════════════════════════════

# Mission states that block consequential execution.
# Maps mission status -> set of actions still allowed.
# Actions not in the allowed set are denied.

# Standard mission statuses from MissionStatus enum:
# QUEUED, PLANNING, RESEARCHING, EXECUTING, TESTING, VERIFYING,
# WAITING_FOR_AGENT, WAITING_FOR_HUMAN, BLOCKED, FAILED,
# CANCELED, COMPLETED, COMPLETED_WITH_CONDITIONS
#
# G4.7 adds PAUSED and FROZEN as control states.

_MISSION_STATE_ALLOWLIST: dict[str, frozenset[ExecutionAction]] = {
    # Active states — most actions allowed
    "QUEUED": frozenset({
        ExecutionAction.MISSION_START, ExecutionAction.MISSION_CANCEL,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),
    "PLANNING": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.SUBAGENT_SPAWN,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ, ExecutionAction.FILE_READ,
        ExecutionAction.TOOL_INVOKE,
    }),
    "RESEARCHING": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.SUBAGENT_SPAWN,
        ExecutionAction.TOOL_INVOKE, ExecutionAction.FILE_READ,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),
    "EXECUTING": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.MISSION_FREEZE,
        ExecutionAction.SUBAGENT_SPAWN, ExecutionAction.TOOL_INVOKE,
        ExecutionAction.FILE_CREATE, ExecutionAction.FILE_MODIFY,
        ExecutionAction.FILE_READ, ExecutionAction.EVIDENCE_READ,
        ExecutionAction.EVENT_READ, ExecutionAction.REPLAY_READ,
        ExecutionAction.HEALTH_READ, ExecutionAction.INCIDENT_READ,
        ExecutionAction.EXTERNAL_COMMUNICATION,
    }),
    "TESTING": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.TOOL_INVOKE,
        ExecutionAction.FILE_READ, ExecutionAction.FILE_MODIFY,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),
    "VERIFYING": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.FILE_READ,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),
    "WAITING_FOR_AGENT": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.EVIDENCE_READ,
        ExecutionAction.EVENT_READ, ExecutionAction.REPLAY_READ,
        ExecutionAction.HEALTH_READ, ExecutionAction.INCIDENT_READ,
    }),
    "WAITING_FOR_HUMAN": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.APPROVAL_DECISION,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),

    # Paused — allow resume, cancel, read-only
    "PAUSED": frozenset({
        ExecutionAction.MISSION_RESUME, ExecutionAction.MISSION_CANCEL,
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),

    # Frozen — allow read-only, incident review, deny resume unless explicitly unfrozen
    "FROZEN": frozenset({
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.INCIDENT_READ,
        ExecutionAction.HEALTH_READ,
    }),

    # Blocked — allow cancel and read-only
    "BLOCKED": frozenset({
        ExecutionAction.MISSION_CANCEL, ExecutionAction.EVIDENCE_READ,
        ExecutionAction.EVENT_READ, ExecutionAction.REPLAY_READ,
        ExecutionAction.HEALTH_READ, ExecutionAction.INCIDENT_READ,
    }),

    # Failed — allow read-only only
    "FAILED": frozenset({
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),

    # Canceled — deny all execution
    "CANCELED": frozenset({
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.HEALTH_READ,
        ExecutionAction.INCIDENT_READ,
    }),

    # Completed — deny further mutation unless a new run is created
    "COMPLETED": frozenset({
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.EXPORT_EVIDENCE,
        ExecutionAction.HEALTH_READ, ExecutionAction.INCIDENT_READ,
    }),
    "COMPLETED_WITH_CONDITIONS": frozenset({
        ExecutionAction.EVIDENCE_READ, ExecutionAction.EVENT_READ,
        ExecutionAction.REPLAY_READ, ExecutionAction.EXPORT_EVIDENCE,
        ExecutionAction.HEALTH_READ, ExecutionAction.INCIDENT_READ,
    }),
}

# Actions that don't require a mission context
_NO_MISSION_REQUIRED_ACTIONS = frozenset({
    ExecutionAction.MISSION_CREATE,
    ExecutionAction.KILL_SWITCH_ACTIVATE,
    ExecutionAction.KILL_SWITCH_CLEAR,
    ExecutionAction.HEALTH_READ,
    ExecutionAction.EVIDENCE_READ,
    ExecutionAction.EVENT_READ,
    ExecutionAction.REPLAY_READ,
    ExecutionAction.INCIDENT_READ,
    ExecutionAction.EXPORT_EVIDENCE,
    ExecutionAction.FILE_READ,
    ExecutionAction.CREDENTIAL_READ,
    ExecutionAction.EXTERNAL_COMMUNICATION,
    ExecutionAction.REPOSITORY_COMMIT,
    ExecutionAction.REPOSITORY_PUSH,
    ExecutionAction.REPOSITORY_MERGE,
    ExecutionAction.DESTRUCTIVE_COMMAND,
    ExecutionAction.FINANCIAL_ACTION,
    ExecutionAction.LEGAL_SUBMISSION,
    ExecutionAction.PRODUCTION_DEPLOYMENT,
    ExecutionAction.CREDENTIAL_MODIFY,
    ExecutionAction.IDENTITY_ACTION,
    ExecutionAction.APPROVAL_DECISION,
})


# ═══════════════════════════════════════════════════════════════════════════════
# Principal Context (G4.8 placeholder)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PrincipalContext:
    """Placeholder principal context for G4.8.

    G4.7 does NOT trust actor names from request bodies.
    G4.7 does NOT claim full authorization is complete.
    G4.8 will replace this with authenticated principal identity.

    For now, is_authenticated defaults to False, meaning no
    principal-backed authorization is available. Guard logic must
    treat unauthenticated principals as lacking all permissions.
    """
    subject_id: Optional[str] = None
    authentication_method: Optional[str] = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_authenticated: bool = False

    @classmethod
    def unauthenticated(cls) -> PrincipalContext:
        """Create an unauthenticated placeholder principal."""
        return cls(is_authenticated=False)

    @classmethod
    def for_testing(
        cls,
        subject_id: str = "test-principal",
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
    ) -> PrincipalContext:
        """Create a test principal for unit tests only.

        This must NOT be used in production code paths.
        """
        return cls(
            subject_id=subject_id,
            authentication_method="test",
            roles=roles or [],
            permissions=permissions or [],
            is_authenticated=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Request and Decision Types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionGuardRequest:
    """Input to the execution guard."""
    action: ExecutionAction
    mission_id: Optional[str] = None
    agent_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    principal_context: PrincipalContext = field(default_factory=PrincipalContext.unauthenticated)
    extra_context: dict[str, Any] = field(default_factory=dict)


class DecisionReasonCode(str, enum.Enum):
    """Machine-readable reason codes for guard decisions."""
    ALLOWED = "ALLOWED"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    MISSION_STATE_BLOCKED = "MISSION_STATE_BLOCKED"
    MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_DENIED = "APPROVAL_DENIED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    GOVERNANCE_GATE_DENIED = "GOVERNANCE_GATE_DENIED"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    UNKNOWN_MISSION_STATE = "UNKNOWN_MISSION_STATE"
    FAIL_CLOSED = "FAIL_CLOSED"
    PRINCIPAL_NOT_AUTHENTICATED = "PRINCIPAL_NOT_AUTHENTICATED"


@dataclass
class ExecutionGuardDecision:
    """Structured decision from the execution guard."""
    allowed: bool
    action: ExecutionAction
    reason_code: DecisionReasonCode
    reason: str
    governance_gate: Optional[str] = None
    approval_required: bool = False
    approval_id: Optional[str] = None
    mission_id: Optional[str] = None
    agent_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    risk_level: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    policy_version: str = POLICY_VERSION


# ═══════════════════════════════════════════════════════════════════════════════
# Typed Errors
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionGuardError(Exception):
    """Base error for execution guard denials."""
    def __init__(self, decision: ExecutionGuardDecision):
        self.decision = decision
        # Do NOT include sensitive resource_id or payload in the message
        safe_msg = f"Execution guard denied {decision.action.value}: {decision.reason_code.value}"
        if decision.reason and "credential" not in decision.reason.lower():
            safe_msg += f" — {decision.reason}"
        super().__init__(safe_msg)


class KillSwitchActiveError(ExecutionGuardError):
    """Raised when a consequential action is blocked by an active kill switch."""
    pass


class MissionStateBlockedError(ExecutionGuardError):
    """Raised when a mission state blocks the requested action."""
    pass


class ApprovalRequiredError(ExecutionGuardError):
    """Raised when an action requires approval that has not been obtained."""
    pass


class GovernanceGateDeniedError(ExecutionGuardError):
    """Raised when a governance gate check fails."""
    pass


class ExecutionDeniedError(ExecutionGuardError):
    """Raised for other denial reasons (fail-closed, unknown action, etc.)."""
    pass


# ── Backwards-compatible aliases for existing service code ──

# The old execution_guard.py exported ActionType and require_execution_allowed.
# observatory_service.py imports these. We provide aliases to avoid breaking
# existing service integration while the new guard API is adopted.

ActionType = ExecutionAction  # type alias for backwards compatibility


# Backwards-compatible attribute access for old ActionType member names.
# In G4.7, the enum was expanded and some members were renamed.
# We provide a mapping so old code like ActionType.PRODUCTION_DEPLOY still works.
_OLD_ACTION_ALIASES = {
    "PRODUCTION_DEPLOY": ExecutionAction.PRODUCTION_DEPLOYMENT,
    "MISSION_EXECUTE": ExecutionAction.TOOL_INVOKE,
    "AGENT_SPAWN": ExecutionAction.SUBAGENT_SPAWN,
    "AGENT_CONTROL": ExecutionAction.TOOL_INVOKE,
}


class _ActionTypeAliasWrapper:
    """Wrapper that delegates to ExecutionAction but supports old attribute names."""
    def __getattr__(self, name):
        if name in _OLD_ACTION_ALIASES:
            return _OLD_ACTION_ALIASES[name]
        return getattr(ExecutionAction, name)

    def __iter__(self):
        return iter(ExecutionAction)

    def __contains__(self, item):
        return item in ExecutionAction

    def __getitem__(self, key):
        return ExecutionAction[key]

    # Make it behave like an enum class
    __members__ = ExecutionAction.__members__


ActionType = _ActionTypeAliasWrapper()


# Read-only operations that remain available during kill-switch active state.
# Backwards-compatible frozenset from the old execution_guard.py.
READONLY_OPERATIONS = frozenset({
    action.value for action, policy in _ACTION_POLICY.items()
    if policy.kill_switch == KillSwitchBehavior.ALLOWED
})


async def require_execution_allowed(
    db: AsyncSession,
    action: ActionType,
    mission_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    """Backwards-compatible guard function.

    Delegates to ExecutionGuard.require_allowed with the old API signature.
    Raises ExecutionBlockedError (aliased) on denial.
    """
    try:
        await ExecutionGuard.require_allowed(
            session=db,
            action=action if isinstance(action, ExecutionAction) else ExecutionAction(action),
            mission_id=mission_id,
            agent_id=agent_id,
        )
    except ExecutionGuardError as e:
        # Re-raise as ExecutionBlockedError for backwards compatibility
        raise ExecutionBlockedError(
            action=action,
            reason=e.decision.reason,
        ) from e


class ExecutionBlockedError(Exception):
    """Backwards-compatible error for kill-switch blocks."""
    def __init__(self, action, reason=None, scope=None):
        self.action = action
        self.reason = reason
        self.scope = scope
        msg = f"Execution blocked: {action.value if hasattr(action, 'value') else action} is prohibited"
        if reason:
            msg += f" (reason: {reason})"
        super().__init__(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Guard Statistics (for observability)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GuardStatistics:
    """In-memory guard statistics (not persisted; for health/dashboards)."""
    allowed: int = 0
    denied: int = 0
    denials_by_reason: dict[str, int] = field(default_factory=dict)
    denials_by_action: dict[str, int] = field(default_factory=dict)
    approval_required_count: int = 0
    fail_closed_count: int = 0

    def record(self, decision: ExecutionGuardDecision) -> None:
        if decision.allowed:
            self.allowed += 1
        else:
            self.denied += 1
            reason = decision.reason_code.value
            self.denials_by_reason[reason] = self.denials_by_reason.get(reason, 0) + 1
            action = decision.action.value
            self.denials_by_action[action] = self.denials_by_action.get(action, 0) + 1
            if decision.reason_code == DecisionReasonCode.APPROVAL_REQUIRED:
                self.approval_required_count += 1
            if decision.reason_code == DecisionReasonCode.FAIL_CLOSED:
                self.fail_closed_count += 1


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionGuard — the single authoritative enforcement boundary
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionGuard:
    """Centralized execution guard.

    Every consequential action must pass through this guard before execution.
    The guard evaluates kill-switch state, mission state, action classification,
    governance gates, and approval requirements.

    Usage:
        await ExecutionGuard.require_allowed(
            session=db,
            action=ExecutionAction.FILE_MODIFY,
            mission_id=mission_id,
        )
    """

    _statistics = GuardStatistics()
    _audit_enabled = True  # Can be disabled in tests to avoid event pollution

    @classmethod
    def get_statistics(cls) -> GuardStatistics:
        return cls._statistics

    @classmethod
    def reset_statistics(cls) -> None:
        cls._statistics = GuardStatistics()

    @classmethod
    async def evaluate(
        cls,
        session: AsyncSession,
        action: ExecutionAction,
        mission_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        principal_context: Optional[PrincipalContext] = None,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> ExecutionGuardDecision:
        """Evaluate the guard without raising. Returns a structured decision.

        This method does NOT mutate the requested resource.
        It may emit an audit event recording the decision.
        """
        if principal_context is None:
            principal_context = PrincipalContext.unauthenticated()
        if extra_context is None:
            extra_context = {}

        request = ExecutionGuardRequest(
            action=action,
            mission_id=mission_id,
            agent_id=agent_id,
            resource_type=resource_type,
            resource_id=resource_id,
            principal_context=principal_context,
            extra_context=extra_context,
        )

        # ── Step 1: Action classification ──
        policy = _ACTION_POLICY.get(action)
        if policy is None:
            decision = ExecutionGuardDecision(
                allowed=False,
                action=action,
                reason_code=DecisionReasonCode.UNKNOWN_ACTION,
                reason=f"Unknown action: {action}",
                policy_version=POLICY_VERSION,
            )
            cls._statistics.record(decision)
            await cls._emit_audit_event(session, decision, policy=None)
            return decision

        # ── Step 2: Kill-switch enforcement ──
        if policy.kill_switch == KillSwitchBehavior.BLOCKED:
            try:
                from portal.services.observatory_service import KillSwitchService
                is_ks_active = await KillSwitchService.is_active(session)
            except Exception as e:
                # Fail closed for consequential actions
                logger.error("execution_guard.kill_switch_lookup_failed action=%s error=%s", action.value, e)
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.FAIL_CLOSED,
                    reason="Unable to determine kill-switch state; failing closed for safety",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    resource_type=resource_type,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

            if is_ks_active:
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.KILL_SWITCH_ACTIVE,
                    reason="Kill switch is active; consequential actions are blocked",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

        # Kill-switch activation is always allowed
        # Kill-switch clearing is evaluated separately (approval required)
        # Read-only actions skip kill-switch check entirely

        # ── Step 3: Mission-state enforcement ──
        if policy.mission_state_required and mission_id:
            try:
                mission_state = await cls._get_mission_state(session, mission_id)
            except Exception as e:
                logger.error("execution_guard.mission_lookup_failed action=%s mission=%s error=%s", action.value, mission_id, e)
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.FAIL_CLOSED,
                    reason="Unable to determine mission state; failing closed",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

            if mission_state is None:
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.MISSION_NOT_FOUND,
                    reason=f"Mission not found: {mission_id}",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

            allowlist = _MISSION_STATE_ALLOWLIST.get(mission_state)
            if allowlist is None:
                # Unknown mission state — fail closed
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.UNKNOWN_MISSION_STATE,
                    reason=f"Unknown mission state: {mission_state}",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

            if action not in allowlist:
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.MISSION_STATE_BLOCKED,
                    reason=f"Mission state '{mission_state}' does not permit action '{action.value}'",
                    governance_gate=policy.governance_gate,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

        # ── Step 4: Approval enforcement ──
        approval_id = None
        if policy.approval == ApprovalBehavior.REQUIRED:
            if mission_id:
                try:
                    approval_id = await cls._check_approval(session, mission_id, policy.governance_gate)
                except Exception as e:
                    logger.error("execution_guard.approval_lookup_failed action=%s error=%s", action.value, e)
                    decision = ExecutionGuardDecision(
                        allowed=False,
                        action=action,
                        reason_code=DecisionReasonCode.FAIL_CLOSED,
                        reason="Unable to determine approval state; failing closed",
                        governance_gate=policy.governance_gate,
                        mission_id=mission_id,
                        agent_id=agent_id,
                        risk_level=policy.risk_level.value,
                        policy_version=POLICY_VERSION,
                    )
                    cls._statistics.record(decision)
                    await cls._emit_audit_event(session, decision, policy=policy)
                    return decision

            if approval_id is None:
                decision = ExecutionGuardDecision(
                    allowed=False,
                    action=action,
                    reason_code=DecisionReasonCode.APPROVAL_REQUIRED,
                    reason=f"Action '{action.value}' requires approval (gate: {policy.governance_gate or 'N/A'})",
                    governance_gate=policy.governance_gate,
                    approval_required=True,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    resource_type=resource_type,
                    risk_level=policy.risk_level.value,
                    policy_version=POLICY_VERSION,
                )
                cls._statistics.record(decision)
                await cls._emit_audit_event(session, decision, policy=policy)
                return decision

        # ── Step 5: Allow ──
        decision = ExecutionGuardDecision(
            allowed=True,
            action=action,
            reason_code=DecisionReasonCode.ALLOWED,
            reason="Action permitted",
            governance_gate=policy.governance_gate,
            approval_required=False,
            approval_id=approval_id,
            mission_id=mission_id,
            agent_id=agent_id,
            resource_type=resource_type,
            resource_id=resource_id,
            risk_level=policy.risk_level.value,
            policy_version=POLICY_VERSION,
        )
        cls._statistics.record(decision)
        await cls._emit_audit_event(session, decision, policy=policy)
        return decision

    @classmethod
    async def require_allowed(
        cls,
        session: AsyncSession,
        action: ExecutionAction,
        mission_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        principal_context: Optional[PrincipalContext] = None,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> ExecutionGuardDecision:
        """Evaluate the guard and raise a typed exception on denial.

        Returns the decision on success. Raises on denial.
        Denials occur before any side effect.
        """
        decision = await cls.evaluate(
            session=session,
            action=action,
            mission_id=mission_id,
            agent_id=agent_id,
            resource_type=resource_type,
            resource_id=resource_id,
            principal_context=principal_context,
            extra_context=extra_context,
        )

        if not decision.allowed:
            exc_map = {
                DecisionReasonCode.KILL_SWITCH_ACTIVE: KillSwitchActiveError,
                DecisionReasonCode.MISSION_STATE_BLOCKED: MissionStateBlockedError,
                DecisionReasonCode.MISSION_NOT_FOUND: MissionStateBlockedError,
                DecisionReasonCode.UNKNOWN_MISSION_STATE: MissionStateBlockedError,
                DecisionReasonCode.APPROVAL_REQUIRED: ApprovalRequiredError,
                DecisionReasonCode.APPROVAL_DENIED: ApprovalRequiredError,
                DecisionReasonCode.APPROVAL_EXPIRED: ApprovalRequiredError,
                DecisionReasonCode.GOVERNANCE_GATE_DENIED: GovernanceGateDeniedError,
            }
            exc_cls = exc_map.get(decision.reason_code, ExecutionDeniedError)
            raise exc_cls(decision)

        return decision

    # ── Internal helpers ──

    @staticmethod
    async def _get_mission_state(session: AsyncSession, mission_id: str) -> Optional[str]:
        """Look up the mission status by ID."""
        from portal.models.observatory import Mission
        try:
            mid = uuid.UUID(mission_id) if isinstance(mission_id, str) else mission_id
        except (ValueError, AttributeError):
            return None
        result = await session.execute(
            select(Mission).where(Mission.id == mid)
        )
        mission = result.scalar_one_or_none()
        return mission.status if mission else None

    @staticmethod
    async def _check_approval(
        session: AsyncSession,
        mission_id: str,
        gate: Optional[str],
    ) -> Optional[str]:
        """Check if there is an approved, non-expired approval for the mission/gate.

        Returns the approval ID if approved, None otherwise.
        """
        from portal.models.observatory import Approval
        try:
            mid = uuid.UUID(mission_id) if isinstance(mission_id, str) else mission_id
        except (ValueError, AttributeError):
            return None

        result = await session.execute(
            select(Approval).where(
                Approval.mission_id == mid,
                Approval.status == "APPROVED",
            )
        )
        approvals = result.scalars().all()

        for a in approvals:
            if gate and a.gate and a.gate != gate:
                continue
            # Check not expired (simplified: EXPIRED status would be set by a cleanup job)
            if a.status == "APPROVED":
                return str(a.id)

        return None

    @staticmethod
    async def _emit_audit_event(
        session: AsyncSession,
        decision: ExecutionGuardDecision,
        policy: Optional[ActionPolicy],
    ) -> None:
        """Emit a canonical observatory audit event for the guard decision.

        Uses the existing run-scoped hash-chain service.
        Does NOT include secrets, full file contents, credentials, or sensitive payload data.
        Resource IDs are included for audit trail but masked if they contain sensitive patterns.
        """
        if not ExecutionGuard._audit_enabled:
            return
        try:
            from portal.services.observatory_service import EventService

            event_type = (
                "EXECUTION_GUARD_ALLOWED" if decision.allowed
                else "EXECUTION_GUARD_DENIED" if decision.reason_code != DecisionReasonCode.FAIL_CLOSED
                else "EXECUTION_GUARD_ERROR"
            )

            # Mask sensitive resource identifiers
            masked_resource_id = decision.resource_id
            if masked_resource_id and any(
                s in masked_resource_id.lower()
                for s in ("password", "secret", "token", "credential", "api_key", "private_key")
            ):
                masked_resource_id = "***MASKED***"

            payload: dict[str, Any] = {
                "action": decision.action.value,
                "reason_code": decision.reason_code.value,
                "reason": decision.reason,
                "governance_gate": decision.governance_gate,
                "risk_level": decision.risk_level or (policy.risk_level.value if policy else None),
                "approval_required": decision.approval_required,
                "policy_version": decision.policy_version,
                "evaluated_at": decision.evaluated_at,
            }
            if decision.mission_id:
                payload["mission_id"] = decision.mission_id
            if decision.agent_id:
                payload["agent_id"] = decision.agent_id
            if decision.resource_type:
                payload["resource_type"] = decision.resource_type
            if masked_resource_id:
                payload["resource_id"] = masked_resource_id

            await EventService.create(
                db=session,
                event_type=event_type,
                payload=payload,
                mission_id=None,  # System-level event, not tied to a specific mission
                agent_id="system:execution-guard",
                run_id=SYSTEM_RUN_ID,
            )
            await session.commit()
        except Exception as e:
            # Audit failure must NOT allow the action to proceed if it was denied,
            # and must NOT block the action if it was allowed (the decision is already made).
            logger.error("execution_guard.audit_emit_failed error=%s", e)

    # ── Health ──

    @classmethod
    async def health(cls, session: AsyncSession) -> dict[str, Any]:
        """Return guard health status."""
        health: dict[str, Any] = {
            "policy_loaded": True,
            "policy_version": POLICY_VERSION,
            "actions_classified": len(_ACTION_POLICY),
            "kill_switch_lookup_healthy": False,
            "mission_state_lookup_healthy": False,
            "approval_lookup_healthy": False,
            "audit_emission_healthy": False,
        }
        try:
            from portal.services.observatory_service import KillSwitchService
            await KillSwitchService.is_active(session)
            health["kill_switch_lookup_healthy"] = True
        except Exception:
            pass
        try:
            from portal.models.observatory import Mission
            await session.execute(select(Mission).limit(1))
            health["mission_state_lookup_healthy"] = True
        except Exception:
            pass
        try:
            from portal.models.observatory import Approval
            await session.execute(select(Approval).limit(1))
            health["approval_lookup_healthy"] = True
        except Exception:
            pass
        # Audit emission health: best-effort check that EventService is importable
        try:
            from portal.services.observatory_service import EventService  # noqa: F401
            health["audit_emission_healthy"] = True
        except Exception:
            pass

        stats = cls.get_statistics()
        health["statistics"] = {
            "allowed": stats.allowed,
            "denied": stats.denied,
            "denials_by_reason": dict(stats.denials_by_reason),
            "denials_by_action": dict(stats.denials_by_action),
            "approval_required_count": stats.approval_required_count,
            "fail_closed_count": stats.fail_closed_count,
        }
        return health
