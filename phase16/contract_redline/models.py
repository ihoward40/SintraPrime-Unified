"""Phase 16D — AI Contract Redlining: data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClauseType(str, Enum):
    INDEMNIFICATION = "indemnification"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    TERMINATION = "termination"
    PAYMENT = "payment"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    NON_COMPETE = "non_compete"
    ASSIGNMENT = "assignment"
    AMENDMENT = "amendment"
    GENERAL = "general"


class RedlineAction(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    MODIFY = "modify"
    FLAG = "flag"
    COMMENT = "comment"


@dataclass
class ContractClause:
    """A single clause extracted from a contract."""
    clause_id: str
    clause_type: ClauseType
    original_text: str
    section_number: str = ""
    page_number: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskFlag:
    """A risk flag on a specific clause."""
    flag_id: str
    clause_id: str
    risk_level: RiskLevel
    issue: str
    recommendation: str
    legal_basis: str = ""
    confidence: float = 0.0


@dataclass
class Redline:
    """A suggested change to a contract clause."""
    redline_id: str
    clause_id: str
    action: RedlineAction
    original_text: str
    suggested_text: str
    rationale: str
    risk_level: RiskLevel = RiskLevel.LOW
    accepted: Optional[bool] = None
    comment: str = ""


@dataclass
class ContractAnalysis:
    """Full analysis result for a contract."""
    analysis_id: str
    contract_id: str
    clauses: List[ContractClause] = field(default_factory=list)
    risk_flags: List[RiskFlag] = field(default_factory=list)
    redlines: List[Redline] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    summary: str = ""
    created_at: float = 0.0

    @property
    def critical_flags(self) -> List[RiskFlag]:
        return [f for f in self.risk_flags if f.risk_level == RiskLevel.CRITICAL]

    @property
    def high_risk_flags(self) -> List[RiskFlag]:
        return [f for f in self.risk_flags if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

    @property
    def accepted_redlines(self) -> List[Redline]:
        return [r for r in self.redlines if r.accepted is True]

    @property
    def pending_redlines(self) -> List[Redline]:
        return [r for r in self.redlines if r.accepted is None]
