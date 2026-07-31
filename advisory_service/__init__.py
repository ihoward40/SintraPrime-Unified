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
from enum import StrEnum
from typing import Any

PROTOCOL_VERSION = "1.0.0"
SERVICE_VERSION = "0.1"


class RequestedAdvice(StrEnum):
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    GOVERNANCE = "governance"
    STRATEGY = "strategy"


class AdvisoryScope(StrEnum):
    """Types of authority/depth requested (PROTOCOL.md §7)."""

    INFORMATIONAL = "Informational"
    ANALYTICAL = "Analytical"
    STRATEGIC = "Strategic"
    GOVERNANCE = "Governance"
    ARCHITECTURAL = "Architectural"
    ENGINEERING = "Engineering"
    LEGAL_RESEARCH = "Legal Research"


class ResponseClassification(StrEnum):
    INFORMATION = "Information"
    ANALYSIS = "Analysis"
    RECOMMENDATION = "Recommendation"
    ARCHITECTURE_REVIEW = "Architecture Review"
    GOVERNANCE_REVIEW = "Governance Review"
    RISK_REVIEW = "Risk Review"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdvisoryLifecycleState(StrEnum):
    """Advisory session lifecycle (PROTOCOL.md §17)."""

    REQUESTED = "Requested"
    PREPARED = "Prepared"
    SUBMITTED = "Submitted"
    ANALYZED = "Analyzed"
    RETURNED = "Returned"
    ACKNOWLEDGED = "Acknowledged"
    ARCHIVED = "Archived"


class ProviderInterface(StrEnum):
    """Provider-agnostic fulfillment engines (PROTOCOL.md §14)."""

    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    LOCAL_LLM = "Local LLM"
    FUTURE = "Future Provider"


@dataclass
class Provenance:
    """Provenance metadata for a packet or response (PROTOCOL.md §13)."""

    requester: str
    mission_id: str
    source_channel: str
    timestamp_utc: str
    governance_basis: str
    repository_commit: str
    provider: str | None = None
    model: str | None = None
    provider_api_version: str | None = None
    completion_id: str | None = None
    advisory_session_id: str | None = None
    protocol_version: str = PROTOCOL_VERSION
    advisory_service_version: str = SERVICE_VERSION


@dataclass
class ContextManifest:
    """Explicit context manifest bounding prompt size (PROTOCOL.md §6)."""

    mission_id: str
    evidence_ids: list[str]
    relevant_bkgc_requirements: list[str]
    requested_question: str
    expected_deliverable: ResponseClassification
    relevant_cdrs: list[str] = field(default_factory=list)
    repository_commit: str = ""


@dataclass
class EvidenceSnapshot:
    """Immutable record for reproducibility (PROTOCOL.md §11)."""

    generated_at: str  # ISO-8601 timestamp
    evidence_revision: str  # Hash or version ID of the evidence set
    repository_commit: str  # Git SHA of the codebase


@dataclass
class AdvisoryPacket:
    """Request schema sent by Hermes to the Advisory Service (PROTOCOL.md §8)."""

    advisory_session_id: str
    protocol_version: str
    mission_id: str
    context_manifest: ContextManifest
    advisory_scope: list[AdvisoryScope]
    requested_advice: RequestedAdvice
    governance_basis: str
    provenance: Provenance
    deadline: str | None = None
    extensions: dict[str, Any] | None = None  # Reserved for future optional fields


@dataclass
class AdvisoryClassification:
    """Safeguard block appended to every response (PROTOCOL.md §15)."""

    advisor_classification: str = "Advisory"
    decision_authority: str = "Principal"
    execution_authority: str = "Hermes"
    governance_authority: str = "GB-1"


@dataclass
class AdvisoryResponse:
    """Response schema returned by the Advisory Service (PROTOCOL.md §9)."""

    assessment: str
    missing_evidence: list[str]
    risks: list[str]
    alternatives: list[str]
    recommendation: str
    confidence: Confidence
    coverage: float  # 0.0..1.0 — fraction of relevant evidence available
    response_classification: ResponseClassification
    evidence_snapshot: EvidenceSnapshot
    not_a_decision: bool = True
    human_override: bool = True
    questions: list[str] = field(default_factory=list)
    advisory_classification: AdvisoryClassification = field(
        default_factory=AdvisoryClassification
    )
    provenance: Provenance | None = None
    extensions: dict[str, Any] | None = None  # Reserved for future optional fields


@dataclass
class ErrorResponse:
    """Error response envelope (PROTOCOL.md §18). For future implementation."""

    error_code: str
    error_message: str
    advisory_session_id: str
    provenance: Provenance | None = None
    error_detail: str | None = None  # Stack trace or provider details


@dataclass
class ServiceContract:
    """The protocol boundary (PROTOCOL.md §9). Inputs -> Outputs only."""

    inputs: tuple = (
        "Mission",
        "Context (Context Manifest)",
        "Question",
        "Advisory Scope",
    )
    outputs: tuple = (
        "Assessment",
        "Missing Evidence",
        "Risks",
        "Alternatives",
        "Recommendation",
        "Confidence",
        "Coverage",
        "Classification",
        "Evidence Snapshot",
    )


def format_advisory_session_id(year: int, sequence: int) -> str:
    """Pure formatter for an Advisory Session ID (PROTOCOL.md §4).

    Allocation of the sequence number is an Increment Two concern; this helper
    only formats it. No state, no I/O.
    """
    return f"ADV-{year}-{sequence:06d}"


# Safeguard blocks — appended verbatim to every advisor response (PROTOCOL.md §15).
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

# Capability registration record (PROTOCOL.md §21) — informational. The
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
# hardcoded (PROTOCOL.md §14).
DEFAULT_PROVIDER: ProviderInterface = ProviderInterface.OPENAI
PROVIDER_INTERFACE = "Advisor Provider Interface"
MODEL = "Configurable"

# Extension point namespaces (PROTOCOL.md §19) — reserved for future capabilities.
EXTENSION_NAMESPACES = [
    "advisor.extensions.*",
    "provider.extensions.*",
]
