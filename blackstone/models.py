"""
Blackstone models — data types shared across the BRA engines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


class ClaimStatus(StrEnum):
    CONTROLLING = "controlling"
    PERSUASIVE = "persuasive"
    HISTORICALLY_DOCUMENTED = "historically_documented"
    SCHOLARLY = "scholarly"
    EDUCATIONAL = "educational"
    EMERGING = "emerging"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class SourceClassification(StrEnum):
    PRIMARY_LEGAL = "primary_legal"
    SECONDARY_LEGAL = "secondary_legal"
    SCHOLARLY = "scholarly"
    HISTORICAL = "historical"
    PRIVATE_PUBLISHED = "private_published"
    COMMERCIAL = "commercial"
    AI_GENERATED = "ai_generated"
    ARCHIVAL = "archival"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"
    PRELIMINARY = "preliminary"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class Jurisdiction:
    name: str
    level: str = "unknown"  # e.g., federal, state, county, municipal, international
    parent: str | None = None


@dataclass(frozen=True)
class Source:
    id: str
    citation: str
    classification: SourceClassification
    jurisdiction: Jurisdiction | None = None
    effective_date: datetime | None = None
    url: str | None = None
    publisher: str | None = None
    retrieved_at: datetime | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "citation": self.citation,
            "classification": self.classification.value,
            "jurisdiction": self.jurisdiction.name if self.jurisdiction else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "url": self.url,
            "publisher": self.publisher,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "notes": self.notes,
        }


@dataclass
class EvidenceItem:
    id: str
    source: Source
    claim_text: str
    quotation: str = ""
    context: str = ""
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: Confidence = Confidence.INSUFFICIENT
    supports: list[str] = field(default_factory=list)
    challenges: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    jurisdiction: Jurisdiction | None = None
    created_at: datetime = field(default_factory=utcnow)
    reviewed_at: datetime | None = None
    reviewer: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.to_dict(),
            "claim_text": self.claim_text,
            "quotation": self.quotation,
            "context": self.context,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "supports": self.supports,
            "challenges": self.challenges,
            "tags": self.tags,
            "jurisdiction": self.jurisdiction.name if self.jurisdiction else None,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewer": self.reviewer,
            "metadata": self.metadata,
        }


@dataclass
class Claim:
    id: str
    text: str
    subject: str
    jurisdiction: Jurisdiction | None = None
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: Confidence = Confidence.INSUFFICIENT
    evidence: list[EvidenceItem] = field(default_factory=list)
    counter_evidence: list[EvidenceItem] = field(default_factory=list)
    related_claims: list[str] = field(default_factory=list)
    competing_interpretations: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    effective_date: datetime | None = None
    review_date: datetime | None = None
    reviewed_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "subject": self.subject,
            "jurisdiction": self.jurisdiction.name if self.jurisdiction else None,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "evidence_count": len(self.evidence),
            "counter_evidence_count": len(self.counter_evidence),
            "related_claims": self.related_claims,
            "competing_interpretations": self.competing_interpretations,
            "assumptions": self.assumptions,
            "missing_evidence": self.missing_evidence,
            "tags": self.tags,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "reviewed_by": self.reviewed_by,
        }


@dataclass
class Risk:
    id: str
    category: str
    description: str
    likelihood: Confidence = Confidence.INSUFFICIENT
    impact: Confidence = Confidence.INSUFFICIENT
    controls: list[str] = field(default_factory=list)
    owner: str = ""
    actor: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "likelihood": self.likelihood.value,
            "impact": self.impact.value,
            "controls": self.controls,
            "owner": self.owner,
            "actor": self.actor,
            "tags": self.tags,
        }


@dataclass
class ProvenanceEntry:
    id: str
    object_id: str
    object_type: str  # claim, evidence, source, recommendation, risk
    action: str
    actor: str
    timestamp: datetime = field(default_factory=utcnow)
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object_id": self.object_id,
            "object_type": self.object_type,
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }


@dataclass
class Recommendation:
    id: str
    question: str
    recommendation: str
    rationale: str
    evidence_considered: list[str] = field(default_factory=list)
    authorities_consulted: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    conditions_for_change: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.INSUFFICIENT
    agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "evidence_considered": self.evidence_considered,
            "authorities_consulted": self.authorities_consulted,
            "assumptions": self.assumptions,
            "alternatives": self.alternatives,
            "conditions_for_change": self.conditions_for_change,
            "confidence": self.confidence.value,
            "agents": self.agents,
        }
