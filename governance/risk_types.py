"""
risk_types.py — Core data models for the AI Governance system.

Defines risk levels, approval requests, governance policies, and audit entries
used throughout the SintraPrime-Unified governance framework.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Risk classification levels for agent actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def requires_approval(self) -> bool:
        """Return True if this risk level requires human approval by default."""
        return self in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def numeric(self) -> int:
        """Numeric representation for comparison."""
        return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}[self.value]

    def __lt__(self, other: "RiskLevel") -> bool:
        return self.numeric < other.numeric

    def __le__(self, other: "RiskLevel") -> bool:
        return self.numeric <= other.numeric

    def __gt__(self, other: "RiskLevel") -> bool:
        return self.numeric > other.numeric

    def __ge__(self, other: "RiskLevel") -> bool:
        return self.numeric >= other.numeric


class ApprovalStatus(str, Enum):
    """Lifecycle states for an approval request."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    AUTO_APPROVED = "AUTO_APPROVED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ActionRisk:
    """Risk assessment result for a single agent action."""
    action_type: str
    risk_level: RiskLevel
    reason: str
    requires_approval: bool
    reversible: bool
    estimated_impact: str
    domain: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "reversible": self.reversible,
            "estimated_impact": self.estimated_impact,
            "domain": self.domain,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalRequest:
    """A request for human approval before executing a high-risk action."""
    action: str
    risk: ActionRisk
    requestor: str
    requested_at: datetime
    expires_at: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    approval_link: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc) if self.expires_at.tzinfo is None else datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "risk": self.risk.to_dict(),
            "requestor": self.requestor,
            "requested_at": self.requested_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "approver": self.approver,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "notes": self.notes,
            "context": self.context,
            "approval_link": self.approval_link,
        }


@dataclass
class Rule:
    """A single governance policy rule."""
    name: str
    description: str
    action_pattern: str          # glob or regex pattern matching action names
    risk_threshold: RiskLevel    # minimum risk level triggering this rule
    requires_approval: bool = True
    auto_reject: bool = False    # immediately reject without asking
    notify_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernancePolicy:
    """A collection of rules applied to a set of actions/domains."""
    name: str
    rules: List[Rule]
    applies_to: List[str]        # list of action prefixes or domains
    description: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"

    def get_applicable_rules(self, action_type: str) -> List[Rule]:
        """Return rules that match the given action type."""
        import fnmatch
        return [
            r for r in self.rules
            if fnmatch.fnmatch(action_type, r.action_pattern)
        ]


@dataclass
class AuditEntry:
    """A single immutable audit log record."""
    timestamp: datetime
    actor: str
    action: str
    outcome: str
    risk_level: RiskLevel
    approval_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checksum: Optional[str] = None

    def compute_checksum(self) -> str:
        """Compute a SHA-256 checksum for tamper detection."""
        import hashlib
        import json
        payload = f"{self.id}{self.timestamp.isoformat()}{self.actor}{self.action}{self.outcome}{self.risk_level.value}{self.approval_id}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "outcome": self.outcome,
            "risk_level": self.risk_level.value,
            "approval_id": self.approval_id,
            "metadata": self.metadata,
            "checksum": self.checksum,
        }


@dataclass
class AgentStatus:
    """Current status of a running agent."""
    agent_id: str
    status: str          # running, paused, terminated
    current_task: Optional[str] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    last_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceResult:
    """Result of a compliance check for an action."""
    compliant: bool
    standard: str
    action: str
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EthicsResult:
    """Result of an ethical/legal check."""
    passes: bool
    flags: List[str] = field(default_factory=list)
    unauthorized_practice: bool = False
    bias_detected: bool = False
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Violation:
    """A recorded compliance or ethical violation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    rule: str = ""
    severity: str = "medium"
    description: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """A full compliance audit report for a specific standard."""
    standard: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    compliant: bool = True
    score: float = 100.0
    violations: List[Violation] = field(default_factory=list)
    controls_checked: int = 0
    controls_passed: int = 0
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GovernanceReport:
    """Weekly governance summary report."""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_actions: int = 0
    approvals_requested: int = 0
    approvals_granted: int = 0
    approvals_rejected: int = 0
    auto_approved: int = 0
    violations: int = 0
    by_risk_level: Dict[str, int] = field(default_factory=dict)
    top_actors: List[Dict[str, Any]] = field(default_factory=list)
    top_actions: List[Dict[str, Any]] = field(default_factory=list)
    interventions: int = 0
    compliance_score: float = 100.0
