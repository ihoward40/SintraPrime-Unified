"""
Blackstone Reference Architecture (BRA) — Volume III of the Blackstone Governance Library.

This package is the codebase-resident implementation of BRA. It provides:
  - CCS (Constitutional Compliance Score) scoring engine   — bra.ccs
  - CEL (Constitutional Evidence Ledger)                   — bra.cel
  - CDR (Constitutional Decision Record) filer             — bra.cdr
  - KO (Knowledge Object) metadata validation              — bra.ko
  - JSON Schema registry                                   — bra/schemas/

Governed by:
  BKGC v2.0 (Volume I)  — Constitutional authority
  BGS v1.0  (Volume II) — Operational standards
  BCCM v1.0 (Volume IV) — Certification and compliance
  BKR v1.0  (Volume V)  — Canonical definitions and registries

BRA does NOT contain legal conclusions, research findings, or case-specific content.
It is pure infrastructure. All substantive content lives in Knowledge Objects (KOs)
managed by the CEL.

Version: 1.0.0
Effective: 2026-07-06
"""

from blackstone.bra.ccs import CCSScorer, CCSResult
from blackstone.bra.cel import ConstitutionalEvidenceLedger
from blackstone.bra.cdr import CDRFiler
from blackstone.bra.ko import KnowledgeObjectValidator

__all__ = [
    "CCSScorer",
    "CCSResult",
    "ConstitutionalEvidenceLedger",
    "CDRFiler",
    "KnowledgeObjectValidator",
]

__version__ = "1.0.0"
__bkgc_version__ = "2.0"
__bgs_version__ = "1.0"
