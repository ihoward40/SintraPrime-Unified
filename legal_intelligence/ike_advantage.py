"""SP-IKE-ADVANTAGE-001 — evidence moat and lawful private-treasury playbook.

This module gives IKE Solutions a defensible competitive advantage by combining
transaction classification, evidence provenance, procedural timing, audit-grade
workpapers, and regulated-activity boundary checks.  "Private banking" is treated
as private treasury / bank-relationship management unless the business is actually
licensed to conduct regulated banking, lending, deposit-taking, or money transmission.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AdvantageControl:
    control_id: str
    name: str
    purpose: str
    deliverable: str
    moat: str
    caveat: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TreasuryStep:
    step: int
    name: str
    action: str
    evidence: tuple[str, ...]
    boundary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class IKEAdvantageEngine:
    """Generate IKE's evidence-first competitive moat and treasury architecture."""

    MODULE_ID = "SP-IKE-ADVANTAGE-001"

    def competitive_controls(self) -> list[AdvantageControl]:
        return [
            AdvantageControl(
                "IKE-MOAT-001",
                "Evidence-to-element map",
                "Tie every claim, defense, deadline, and requested remedy to the exact supporting exhibit and missing proof.",
                "Matter map: legal element -> authority -> exhibit/page -> confidence -> contrary evidence -> missing evidence.",
                "Competitors often sell templates; IKE can sell a reproducible evidentiary record showing why each sentence is supportable.",
                "Do not present a confidence score as a court finding or legal conclusion.",
            ),
            AdvantageControl(
                "IKE-MOAT-002",
                "Theory firewall",
                "Prevent unsupported commercial/redemption theories from contaminating otherwise valid consumer-law and UCC arguments.",
                "PROVEN / FACT-DEPENDENT / NEEDS-AUTHORITY / UNSUPPORTED / CONTRADICTED classification attached to every outbound theory.",
                "Makes IKE's work easier for attorneys, regulators, courts, and consumers to trust and audit.",
                "The firewall should preserve rejected theories for research history without using them in outbound documents.",
            ),
            AdvantageControl(
                "IKE-MOAT-003",
                "Deadline and procedural leverage ledger",
                "Convert quiet statutory and rule-based deadlines into tracked tasks with proof of trigger and receipt.",
                "Trigger date, authority, response deadline, proof-of-service/receipt, consequence, follow-up date, escalation gate.",
                "A disciplined deadline ledger creates leverage without exaggerated legal claims.",
                "Never calculate a deadline until forum, service method, holidays, and tolling rules are verified.",
            ),
            AdvantageControl(
                "IKE-MOAT-004",
                "Evidence provenance and contradiction matrix",
                "Record where each fact came from and expose conflicts between contracts, ledgers, notices, credit reporting, and later explanations.",
                "Source hash, source date, author/custodian, page/field, extracted fact, contradiction target, status.",
                "Turns document review into a reusable audit product rather than an opinion letter.",
                "Preserve originals; extracted data should never replace source documents.",
            ),
            AdvantageControl(
                "IKE-MOAT-005",
                "Opponent-defense forecast",
                "Require every recommendation to state the strongest likely response and the evidence needed to defeat it.",
                "Best argument / best evidence / missing evidence / opponent's strongest defense / weak theories / deadline / next move.",
                "Reduces confirmation bias and differentiates IKE from one-sided template mills.",
                "Forecasts are strategy tools, not admissions about what the opponent will actually prove.",
            ),
            AdvantageControl(
                "IKE-MOAT-006",
                "Regulated-activity boundary check",
                "Screen new services before IKE handles money, extends credit, adjusts debt, transmits funds, or markets regulated financial services.",
                "Activity classification memo: own funds vs customer funds; payment processing; money transmission; lending; debt adjustment; required licenses/partners.",
                "Lets IKE innovate aggressively while avoiding the common mistake of crossing into a regulated financial business accidentally.",
                "Licensing is activity- and state-specific; a software label or trust structure does not eliminate regulatory requirements.",
            ),
        ]

    def private_treasury_blueprint(self) -> list[TreasuryStep]:
        """Lawful private-treasury workflow for IKE/trust-owned funds and bank relationships."""
        return [
            TreasuryStep(
                1,
                "Define treasury perimeter",
                "List every entity/trust, beneficial owner, account purpose, authorized signer, source of funds, and whether any money belongs to customers or third parties.",
                ("entity documents", "trust authority", "EIN records", "ownership/capacity map"),
                "Managing your own or affiliated-entity funds is different from taking deposits or transmitting customer funds.",
            ),
            TreasuryStep(
                2,
                "Separate legal capacities and accounts",
                "Maintain distinct operating, tax, reserve, payroll, trust, and project accounts where warranted; title each account in the correct legal capacity.",
                ("bank agreements", "signature cards", "account titles", "authorized signer resolutions"),
                "Do not commingle personal, trust, business, or client money merely for convenience.",
            ),
            TreasuryStep(
                3,
                "Adopt a treasury policy",
                "Document permitted banks, minimum liquidity, reserve targets, approval limits, transfer authorities, investment limits, prohibited uses, and emergency access.",
                ("treasury policy", "board/trustee approval", "risk limits"),
                "Internal policy does not override bank contracts, trust duties, tax rules, or licensing law.",
            ),
            TreasuryStep(
                4,
                "Install dual-control payments",
                "Use maker/checker approval for larger ACH/wires, separate credentials, device controls, transaction alerts, positive-pay or equivalent bank controls where available.",
                ("bank permissions", "approval matrix", "audit logs"),
                "Security controls should match the institution's actual features; never share credentials to simulate dual control.",
            ),
            TreasuryStep(
                5,
                "Build rolling liquidity tiers",
                "Forecast 13 weeks of cash; separate immediate operating cash, near-term reserves, tax reserves, and longer-horizon funds eligible for conservative yield products through regulated institutions.",
                ("13-week forecast", "reserve schedule", "cash-flow ledger"),
                "Investment suitability, FDIC/SIPC coverage, market risk, and trust investment duties must be evaluated separately.",
            ),
            TreasuryStep(
                6,
                "Create receivables discipline",
                "Invoice consistently, age receivables, document disputes, set collection escalation rules, and reconcile incoming payments to invoices and bank deposits.",
                ("invoice ledger", "aging report", "payment reconciliation"),
                "Do not convert collection support into unlicensed debt-adjustment or collection activity for third parties without reviewing applicable law.",
            ),
            TreasuryStep(
                7,
                "Document internal loans and advances",
                "For advances among IKE, the trust, owners, or affiliates, use written notes, purpose, amount, maturity, interest if appropriate, authorization, repayment history, and tax/accounting treatment.",
                ("promissory note", "approval", "funding proof", "repayment ledger"),
                "Repeated lending to consumers or the public may trigger lender/usury/licensing rules even if funded with your own money.",
            ),
            TreasuryStep(
                8,
                "Build a bank relationship packet",
                "Maintain a current package containing formation/trust documents, EIN confirmation, ownership/control chart, IDs, business model, source-of-funds narrative, expected transaction profile, contracts, and financial statements.",
                ("KYC packet", "financial statements", "business narrative", "ownership chart"),
                "Truthful consistency matters more than exotic status language; banks must perform their own KYC/AML review.",
            ),
            TreasuryStep(
                9,
                "Use regulated partners for customer-money features",
                "Before offering bill pay, remittance, stored value, wallets, payment instruments, customer fund custody, or similar services, route the product through a licensing analysis and regulated partner strategy.",
                ("activity flowchart", "funds-flow diagram", "partner agreement", "licensing memo"),
                "FinCEN treats money transmission as fact-specific and no dollar threshold applies to the money-transmitter category; state licensing can also apply.",
            ),
            TreasuryStep(
                10,
                "Monthly treasury certification",
                "Reconcile every account, review unusual transfers, verify reserves, confirm signer access, review upcoming obligations, and store a signed monthly treasury certificate with source statements.",
                ("bank reconciliations", "exception report", "monthly certificate", "source statements"),
                "Certification is an internal control, not a substitute for an audit, tax return, fiduciary accounting, or regulated financial statement.",
            ),
        ]

    def regulated_activity_flags(self, model: dict[str, Any]) -> list[str]:
        """Return activities that require licensing/partner review before launch."""
        activities = {str(x).strip().lower() for x in (model.get("activities") or [])}
        customer_funds = bool(model.get("holds_customer_funds"))
        flags: list[str] = []

        if customer_funds or {"money_transmission", "remittance", "bill_pay", "wallet", "stored_value"} & activities:
            flags.append("MONEY_TRANSMISSION_OR_CUSTOMER_FUNDS_REVIEW_REQUIRED")
        if {"consumer_lending", "sales_finance", "installment_lending"} & activities:
            flags.append("LENDING_AND_USURY_LICENSE_REVIEW_REQUIRED")
        if {"debt_adjustment", "debt_management", "creditor_payment_plan"} & activities:
            flags.append("DEBT_ADJUSTMENT_LICENSE_REVIEW_REQUIRED")
        if {"deposit_taking", "bank_account_for_customers", "banking_services"} & activities:
            flags.append("BANKING_OR_DEPOSIT_TAKING_PROHIBITION_LICENSE_REVIEW_REQUIRED")
        return flags
