"""Evidence Command Center

Industrialized evidence management system for consumer law, trust administration,
and litigation support.

Status: MVP (design validation)
Created: 2026-06-14

Modules:
- models: Core data models (Evidence, Violation, Exhibit)
- registry: In-memory registries for evidence tracking
- scoring: Case readiness scoring engine
- exhibits: Utilities for creating court-ready exhibits
"""

from .models import (
    Evidence,
    Violation,
    Exhibit,
    ChainEntry,
    Statute,
    Severity,
    EvidenceStatus,
    ViolationStatus,
    EvidenceStrength,
    generate_letter_label,
    generate_exhibit_number,
    create_evidence_id,
    create_violation_id,
    create_exhibit_id
)

from .registry import (
    EvidenceRegistry,
    ViolationRegistry,
    ExhibitRegistry
)

from .scoring import (
    ReadinessScore,
    calculate_readiness_score,
    score_evidence_completeness,
    score_violation_support,
    score_chain_of_custody,
    score_timeline_completeness,
    score_document_quality
)

from .exhibits import (
    create_exhibit_from_evidence,
    batch_create_exhibits,
    generate_exhibit_manifest,
    get_exhibit_stats
)

__version__ = "0.1.0-mvp"

__all__ = [
    # Models
    "Evidence",
    "Violation",
    "Exhibit",
    "ChainEntry",
    "Statute",
    "Severity",
    "EvidenceStatus",
    "ViolationStatus",
    "EvidenceStrength",
    
    # Registries
    "EvidenceRegistry",
    "ViolationRegistry",
    "ExhibitRegistry",
    
    # Scoring
    "ReadinessScore",
    "calculate_readiness_score",
    
    # Exhibits
    "create_exhibit_from_evidence",
    "batch_create_exhibits",
    "generate_exhibit_manifest",
    "get_exhibit_stats",
    
    # Utilities
    "generate_letter_label",
    "generate_exhibit_number",
    "create_evidence_id",
    "create_violation_id",
    "create_exhibit_id",
]
