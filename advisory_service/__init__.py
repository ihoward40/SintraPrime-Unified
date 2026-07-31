"""
Advisory Service — Increment One architectural scaffold (DESIGN ONLY).

This module defines the protocol schemas for the Advisory Service. It contains
NO runtime logic: no provider client, no Slack handler, no network calls, no
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


PROTOCOL_VERSION = "1.0.0"
SERVICE_VERSION = "0.1"


class RequestedAdvice(str, Enum):
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    GOVERNANCE = "governance"
    STRATEGY = "strategy"


class ResponseClassification(str, Enum):
    INFORMATION = "Information"
    ANALYSIS = "Analysis"
    RECOMMENDATION = "Recommendation"
    ARCHITECTURE_REVIEW = "Architecture Review"
    GOVERNANCE_REVIEW = "Governance Review"
    RISK_REVIEW = "Risk Review"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProviderInterface(str, Enum):
    """Provider-agnostic fulfillment engines (PROTOCOL.md §11)."""

    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    LOCAL_LLM = "Local LLM"
    FUTURE = "Future Provider"


@dataclass
class Provenance:
    """Provenance metadata for a packet or response (PROTOCOL.md §10)."""

    requester: str
    mission_id: str
    source_channel: str
    timestamp_utc: str
    governance_basis: str
    repository_commit: str
    provider: Optional[str] = None
    model: Optional[str] = None
    provider_api_version: Optional[str] = None
    completion_id: Optional[str] = None
    advisory_session_id: Optional[str] = None
    protocol_version: str = PROTOCOL_VERSION
    advisory_service_version: str = SERVICE_VERSION


@dataclass
class ContextManifest:
    """Explicit context manifest bounding prompt size (PROTOCOL.md §5)."""

    mission_id: str
    evidence_ids: List[str]
    relevant_bkgc_requirements: List[str]
    requested_question: str
    expected_deliverable: ResponseClassification
    relevant_cdrs: List[str] = field(default_factory=list)
    repository_commit: str = ""


@dataclass
class AdvisoryPacket:
    """Request schema sent by Hermes to the Advisory Service (PROTOCOL.md §6)."""

    advisory_session_id: str
    protocol_version: str
    mission_id: str
    context_manifest: ContextManifest
    requested_advice: RequestedAdvice
    governance_basis: str
    provenance: Provenance
    deadline: Optional[str] = None


@dataclass
class AdvisoryClassification:
    """Safeguard block appended to every response (PROTOCOL.md §12)."""

    advisor_classification: str = "Advisory"
    decision_authority: str = "Principal"
    execution_authority: str = "Hermes"
    governance_authority: str = "GB-1"


@dataclass
class AdvisoryResponse:
    """Response schema returned by the Advisory Service (PROTOCOL.md §7)."""

    assessment: str
    missing_evidence: List[str]
    risks: List[str]
    alternatives: List[str]
    recommendation: str
    confidence: Confidence
    coverage: float  # 0.0..1.0 — fraction of relevant evidence available
    response_classification: ResponseClassification
    not_a_decision: bool = True
    human_override: bool = True
    questions: List[str] = field(default_factory=list)
    advisory_classification: AdvisoryClassification = field(
        default_factory=AdvisoryClassification
    )
    provenance: Optional[Provenance] = None


@dataclass
class ServiceContract:
    """The protocol boundary (PROTOCOL.md §7). Inputs -> Outputs only."""

    inputs: tuple = ("Mission", "Context (Context Manifest)", "Question")
    outputs: tuple = (
        "Assessment",
        "Missing Evidence",
        "Risks",
        "Alternatives",
        "Recommendation",
        "Confidence",
        "Coverage",
        "Classification",
    )


def format_advisory_session_id(year: int, sequence: int) -> str:
    """Pure formatter for an Advisory Session ID (PROTOCOL.md §3).

    Allocation of the sequence number is an Increment Two concern; this helper
    only formats it. No state, no I/O.
    """
    return f"ADV-{year}-{sequence:06d}"


# Safeguard blocks — appended verbatim to every advisor response (PROTOCOL.md §12).
CLASSIFICATION_BLOCK = (
    "Advisor Classification: Advisory\n"
    "Decision Authority: Principal\n"
    "Execution Authority: Hermes\n"
    "Governance Authority: GB-1"
)

HUMAN_OVERRIDE_BLOCK = (
    "Principal Review Required\n"
    "This advisory is non-binding and requires Principal judgment before implementation."
)

# Capability registration record (PROTOCOL.md §14) — informational. The
# authoritative registration lives in docs/CAPABILITY_INDEX.md and BKR.
CAPABILITY_RECORD = {
    "capability": "Advisor",
    "status": "Engineering (design)",
    "version": SERVICE_VERSION,
    "protocol_version": PROTOCOL_VERSION,
    "provider": "Provider-agnostic (OpenAI default)",
    "classification": "Advisory Only",
    "authority": "None",
    "decision_rights": "None",
}

# Provider configuration — provider-agnostic; model is configurable, never
# hardcoded (PROTOCOL.md §11).
DEFAULT_PROVIDER: ProviderInterface = ProviderInterface.OPENAI
PROVIDER_INTERFACE = "Advisor Provider Interface"
MODEL = "Configurable"
