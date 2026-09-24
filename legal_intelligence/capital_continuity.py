"""SP-CAPITAL-CONTINUITY-001 — capital-book continuity and reconstruction package.

Defines the evidence package needed to rebuild the private-capital book from
source records if the primary application or database is unavailable or corrupted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ContinuityReport:
    module_id: str
    reconstructable: bool
    missing_components: list[str] = field(default_factory=list)
    verified_components: list[str] = field(default_factory=list)
    reconstruction_order: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalContinuityEngine:
    MODULE_ID = "SP-CAPITAL-CONTINUITY-001"

    REQUIRED_COMPONENTS = {
        "bank_source_records",
        "capital_ledger_export",
        "facility_register",
        "approval_records",
        "credit_decisions",
        "security_agreements",
        "collateral_records",
        "receivables_schedules",
        "servicing_history",
        "dashboard_snapshot",
        "decision_journal_export",
        "journal_head_hash",
        "external_anchor_receipt",
        "document_hash_manifest",
    }

    def evaluate(self, context: dict[str, Any]) -> ContinuityReport:
        available = {str(x).strip() for x in (context.get("available_components") or [])}
        missing = sorted(self.REQUIRED_COMPONENTS - available)
        verified = sorted(self.REQUIRED_COMPONENTS & available)
        reconstruction_order = [
            "1. verify document-hash manifest and external journal anchor receipt",
            "2. restore facility register and approval/credit decision records",
            "3. rebuild funding and payment history from independent bank source records",
            "4. reconcile rebuilt cash movements to capital-ledger export",
            "5. restore collateral/security/perfection and receivables records",
            "6. restore servicing events, exceptions, restructures, and write-offs",
            "7. regenerate dashboard metrics from reconstructed source data",
            "8. verify decision-journal chain and head hash against external anchor",
            "9. produce a reconstruction variance report before re-opening normal operations",
        ]
        suggestions = [
            "Keep encrypted monthly continuity bundles in at least two administratively separate locations.",
            "Include machine-readable exports plus human-readable PDF/CSV manifests so reconstruction is not vendor-dependent.",
            "Test restoration quarterly instead of assuming backups are usable.",
        ]
        if missing:
            suggestions.append("Treat missing continuity components as a governance exception and close the gap before increasing deployed capital.")
        return ContinuityReport(
            module_id=self.MODULE_ID,
            reconstructable=not missing,
            missing_components=missing,
            verified_components=verified,
            reconstruction_order=reconstruction_order,
            beneficial_suggestions=suggestions,
        )
