"""
Advisory Service — Increment One architectural scaffold (DESIGN ONLY).

This module defines the protocol schemas for the Advisory Service. It contains
NO runtime logic: no OpenAI client, no Slack handler, no network calls, no
execution paths. Runtime implementation is authorized only in Increment Two
(see docs/advisory-service/PROTOCOL.md).

Governance:
- Classification: Advisory Only.
- Authority: None. Decision Rights: None.
- Governance Authority: GB-1.
- The Advisory Service never approves, dispatches, or mutates system state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RequestedAdvice(str, Enum):
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    GOVERNANCE = "governance"
    STRATEGY = "strategy"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Provenance:
    """Provenance metadata for an advisory packet or response (PROTOCOL.md §7)."""

    requester: str
    mission_id: str
    source_channel: str
    timestamp_utc: str
    governance_basis: str
    provider: Optional[str] = None
    model: Optional[str] = None
    provider_api_version: Optional[str] = None
    completion_id: Optional[str] = None
    advisory_service_version: str = "0.1"


@dataclass
class AdvisoryPacket:
    """Request schema sent by Hermes to the Advisory Service (PROTOCOL.md §3)."""

    mission_id: str
    question: str
    current_evidence: List[str]
    requested_advice: RequestedAdvice
    governance_basis: str
    provenance: Provenance
    known_risks: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    deadline: Optional[str] = None


@dataclass
class AdvisoryClassification:
    """Safeguard block appended to every response (PROTOCOL.md §8)."""

    advisor_classification: str = "Advisory"
    decision_authority: str = "Principal"
    execution_authority: str = "Hermes"
    governance_authority: str = "GB-1"


@dataclass
class AdvisoryResponse:
    """Response schema returned by the Advisory Service to Hermes (PROTOCOL.md §4)."""

    assessment: str
    strengths: List[str]
    weaknesses: List[str]
    missing_evidence: List[str]
    recommendation: str
    confidence: Confidence
    not_a_decision: bool = True
    questions: List[str] = field(default_factory=list)
    advisory_classification: AdvisoryClassification = field(
        default_factory=AdvisoryClassification
    )
    provenance: Optional[Provenance] = None


# Safeguard block — appended verbatim to every advisor response (PROTOCOL.md §8).
CLASSIFICATION_BLOCK = (
    "Advisor Classification: Advisory\n"
    "Decision Authority: Principal\n"
    "Execution Authority: Hermes\n"
    "Governance Authority: GB-1"
)

# Capability registration record (PROTOCOL.md §11) — informational. The
# authoritative registration lives in docs/CAPABILITY_INDEX.md and BKR.
CAPABILITY_RECORD = {
    "capability": "Advisor",
    "status": "Engineering (design)",
    "version": "0.1",
    "provider": "OpenAI",
    "classification": "Advisory Only",
    "authority": "None",
    "decision_rights": "None",
}

# Provider configuration — model is configurable, never hardcoded (PROTOCOL.md §10).
PROVIDER = "OpenAI"
CAPABILITY = "Strategic Advisory"
MODEL = "Configurable"
