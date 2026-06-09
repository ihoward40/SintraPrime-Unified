"""Credit Command Center — consumer evidence organization service.

Tiers:
  - Audit ($97): Scorecard, Top 5 Findings, Evidence Inventory, Next Steps
  - Blueprint ($397): Full violation matrix, dispute strategy, CFPB checklist
  - Vault ($29/mo): Ongoing storage, timeline tracking, annual review

Core message: "Most disputes fail because the evidence was never organized."
"""

from .helpers import (
    build_case_folder_path,
    build_evidence_folder_path,
    create_receipt,
    normalize_client_name,
    rate_scorecard,
)
from .models import (
    AccountStatus,
    ActionReceipt,
    Bureau,
    CaseStatus,
    ClientCase,
    ConfidenceLevel,
    CreditAccount,
    EvidenceItem,
    Finding,
    FindingCategory,
    Scorecard,
    ScorecardRating,
    ServiceTier,
)

__all__ = [
    "AccountStatus",
    "ActionReceipt",
    "Bureau",
    "CaseStatus",
    "ClientCase",
    "ConfidenceLevel",
    "CreditAccount",
    "EvidenceItem",
    "Finding",
    "FindingCategory",
    "Scorecard",
    "ScorecardRating",
    "ServiceTier",
    "build_case_folder_path",
    "build_evidence_folder_path",
    "create_receipt",
    "normalize_client_name",
    "rate_scorecard",
]
