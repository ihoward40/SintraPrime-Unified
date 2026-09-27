"""SP-RELATED-PARTY-001 — fiduciary and conflict firewall for affiliated capital transactions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RelatedPartyReport:
    module_id: str
    decision: str
    conflicts: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class RelatedPartyEngine:
    MODULE_ID = "SP-RELATED-PARTY-001"

    def evaluate(self, context: dict[str, Any]) -> RelatedPartyReport:
        conflicts: list[str] = []
        approvals: list[str] = []
        evidence: list[str] = []
        suggestions: list[str] = []

        lender = str(context.get("lender") or "")
        borrower = str(context.get("borrower") or "")
        relationship = str(context.get("relationship") or "").lower()
        trustee_involved = bool(context.get("trustee_involved"))
        common_control = bool(context.get("common_control"))
        independent_benefit = bool(context.get("independent_benefit_documented"))
        fair_terms = bool(context.get("fair_terms_documented"))
        disinterested_review = bool(context.get("disinterested_review"))
        governing_docs_checked = bool(context.get("governing_documents_checked"))

        if not lender or not borrower:
            conflicts.append("PARTIES_NOT_FULLY_IDENTIFIED")
        if relationship or common_control:
            conflicts.append("RELATED_PARTY_TRANSACTION")
            evidence.extend([
                "relationship/control map",
                "transaction purpose",
                "fairness/market-comparison record",
                "independent-benefit analysis",
                "written approval record",
            ])
            approvals.append("Principal approval after conflict review")

        if trustee_involved:
            conflicts.append("FIDUCIARY_CAPACITY_REVIEW_REQUIRED")
            evidence.extend([
                "trust instrument authority",
                "trustee capacity record",
                "benefit-to-trust analysis",
                "conflict/self-dealing analysis",
            ])
            approvals.append("trustee/co-trustee or other authorized approval consistent with governing instrument")

        blockers: list[str] = []
        if (relationship or common_control or trustee_involved) and not independent_benefit:
            blockers.append("INDEPENDENT_BENEFIT_NOT_DOCUMENTED")
        if (relationship or common_control) and not fair_terms:
            blockers.append("FAIR_TERMS_NOT_DOCUMENTED")
        if trustee_involved and not governing_docs_checked:
            blockers.append("GOVERNING_DOCUMENT_AUTHORITY_NOT_VERIFIED")
        if len(conflicts) > 0 and not disinterested_review:
            approvals.append("disinterested or second-level review recommended before funding")

        decision = "BLOCK" if blockers else "PASS_WITH_CONDITIONS" if conflicts else "PASS"
        conflicts.extend(blockers)
        suggestions.extend([
            "Use written resolutions identifying the conflict, authority, purpose, terms, and approving person/capacity.",
            "Keep pricing and covenant comparisons to show why terms are fair even when the parties are affiliated.",
            "Separate lender and borrower books, bank accounts, and repayment records; do not rely on journal entries alone as proof funds moved.",
            "For trust-related transactions, document why the transaction benefits the trust and is permitted by the governing instrument before execution.",
        ])

        return RelatedPartyReport(
            module_id=self.MODULE_ID,
            decision=decision,
            conflicts=list(dict.fromkeys(conflicts)),
            required_approvals=list(dict.fromkeys(approvals)),
            required_evidence=list(dict.fromkeys(evidence)),
            beneficial_suggestions=suggestions,
        )
