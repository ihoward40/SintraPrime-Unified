"""SP-PRIVATE-CAPITAL-DOCS-001 — controlled private-capital document specifications.

Produces structured template specifications and required-clause checklists. Final legal
language remains subject to current-law, transaction, tax, fiduciary, and licensing review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentTemplateSpec:
    doc_type: str
    required_fields: tuple[str, ...]
    required_sections: tuple[str, ...]
    prohibited_shortcuts: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PrivateCapitalDocsEngine:
    MODULE_ID = "SP-PRIVATE-CAPITAL-DOCS-001"

    def templates(self) -> dict[str, DocumentTemplateSpec]:
        common_prohibited = (
            "do not call an internal note a bank instrument or deposit",
            "do not state that a UCC filing alone creates attachment, priority, or payment",
            "do not use unverified usury, licensing, or tax conclusions",
        )
        common_suggestions = (
            "attach the approval record, source-of-funds proof, and final repayment schedule",
            "assign a facility/document ID and preserve the signed final version plus hashes",
        )
        return {
            "promissory_note": DocumentTemplateSpec(
                "promissory_note",
                ("lender", "borrower", "capacity", "principal", "funding_date", "maturity", "governing_law"),
                ("promise to pay", "funding evidence", "interest/fee terms if lawful", "payment terms", "events of default", "notices", "governing law", "signatures/capacity"),
                common_prohibited,
                common_suggestions,
            ),
            "security_agreement": DocumentTemplateSpec(
                "security_agreement",
                ("debtor", "secured_party", "obligation", "collateral_description", "debtor_rights_basis"),
                ("grant of security interest", "collateral", "secured obligations", "representations", "covenants", "default/remedies", "authorization", "signatures"),
                common_prohibited + ("do not use an overbroad collateral description without transaction-specific review",),
                common_suggestions + ("run attachment, filing-location, perfection, and priority workpapers separately",),
            ),
            "borrowing_base_certificate": DocumentTemplateSpec(
                "borrowing_base_certificate",
                ("facility_id", "as_of_date", "gross_receivables", "ineligible_receivables", "eligible_receivables", "advance_rate", "borrowing_base", "outstanding_advance"),
                ("receivable aging", "ineligibles", "concentration deductions", "dilution", "availability/overadvance", "certification"),
                common_prohibited,
                common_suggestions + ("tie totals to the receivables subledger and source invoices",),
            ),
            "subordination_agreement": DocumentTemplateSpec(
                "subordination_agreement",
                ("senior_creditor", "junior_creditor", "debtor", "senior_debt", "subordinated_debt"),
                ("priority/subordination", "payment blockage if applicable", "turnover", "enforcement standstill if applicable", "notices", "signatures"),
                common_prohibited,
                common_suggestions + ("confirm effect on existing liens, guarantees, and insolvency rights before execution",),
            ),
            "repayment_schedule": DocumentTemplateSpec(
                "repayment_schedule",
                ("facility_id", "principal", "payment_dates", "principal_allocation", "interest_allocation"),
                ("opening balance", "scheduled payment", "interest", "principal", "closing balance", "exceptions"),
                common_prohibited,
                common_suggestions + ("reconcile schedule to actual ledger postings after every payment",),
            ),
            "guarantee": DocumentTemplateSpec(
                "guarantee",
                ("guarantor", "creditor", "primary_obligor", "guaranteed_obligation", "scope"),
                ("guarantee scope", "conditions", "waivers only where lawful", "notices", "governing law", "signature/capacity"),
                common_prohibited + ("do not label someone a surety/guarantor without an actual secondary-liability undertaking",),
                common_suggestions + ("route through the suretyship/accommodation element check in SP-TRANSACTION-CAPACITY-001",),
            ),
            "resolution": DocumentTemplateSpec(
                "resolution",
                ("entity_or_trust", "approver_capacity", "transaction_summary", "approved_amount", "counterparty"),
                ("authority", "conflict disclosure", "transaction approval", "authorized signers", "record preservation"),
                common_prohibited,
                common_suggestions + ("identify disinterested approval or conflict treatment for related-party transactions",),
            ),
            "default_notice": DocumentTemplateSpec(
                "default_notice",
                ("facility_id", "default_event", "contract_section", "amount_or_cure", "notice_address"),
                ("identified default", "supporting facts", "cure rights/deadline if any", "reservation of remedies", "delivery method"),
                common_prohibited + ("do not invent a cure period, acceleration right, or fee not provided by law/contract",),
                common_suggestions + ("verify notice method, cure rules, waiver history, and proof of delivery before sending",),
            ),
        }

    def validate_payload(self, doc_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = self.templates().get(doc_type)
        if not spec:
            return {"module_id": self.MODULE_ID, "valid": False, "errors": ["UNKNOWN_DOCUMENT_TYPE"], "beneficial_suggestions": ["Choose a controlled document type or add a reviewed template specification first."]}
        missing = [field for field in spec.required_fields if payload.get(field) in {None, "", []}]
        return {
            "module_id": self.MODULE_ID,
            "valid": not missing,
            "missing_fields": missing,
            "required_sections": list(spec.required_sections),
            "prohibited_shortcuts": list(spec.prohibited_shortcuts),
            "beneficial_suggestions": list(spec.beneficial_suggestions),
        }
