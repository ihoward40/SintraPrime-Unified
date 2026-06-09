"""
Credit Dispute Engine — SintraPrime-Unified Extension
=====================================================
Generates FCRA-compliant bureau and furnisher dispute documents
for derogatory credit tradelines.

Part of the Howard Recovery System — Credit Repair Track.

SAFETY RULE: This module DRAFTS only. It does NOT send, mail, submit,
or contact any external party. All output requires explicit human approval
before any action is taken.

Usage:
    from legal_intelligence.credit_dispute_engine import CreditDisputeEngine, DisputeAccount

    account = DisputeAccount(
        creditor_name="First Premier Bank",
        account_type="Credit Card",
        credit_limit=400.00,
        reported_balance=777.00,
        status="Charge-off",
        charge_off_year=2022,
        furnisher_address="First Premier Bank\\nP.O. Box 5524\\nSioux Falls, SD 57117-5524",
    )
    engine = CreditDisputeEngine(consumer_name="Isiah Tarik Howard", consumer_address="Newark, NJ 07114")
    docs = engine.generate_all(account)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import textwrap

# Reuse SintraPrime LegalDocument structure
try:
    from legal_intelligence.motion_drafting_engine import LegalDocument
except ImportError:
    # Fallback if run standalone
    from dataclasses import dataclass as _dc

    @_dc
    class LegalDocument:  # type: ignore[no-redef]
        title: str
        court: str
        case_number: str
        content: str
        motion_type: str
        word_count: int = 0
        citations: list = field(default_factory=list)
        sections: dict = field(default_factory=dict)
        page_count: int = 0
        jurisdiction: str = "consumer"
        date_created: str = field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))
        proposed_order: Optional[str] = None


# ---------------------------------------------------------------------------
# FCRA Citation Library (credit dispute specific)
# ---------------------------------------------------------------------------

FCRA_CITATIONS = {
    "sec_611_investigation": {
        "citation": "15 U.S.C. § 1681i(a)(1)(A)",
        "holding": (
            "If the completeness or accuracy of any item of information contained in a "
            "consumer's file at a consumer reporting agency is disputed by the consumer, "
            "the agency shall, within 30 days of receiving the notice of dispute, conduct "
            "a reasonable reinvestigation to determine whether the disputed information "
            "is inaccurate."
        ),
    },
    "sec_611_method_of_verification": {
        "citation": "15 U.S.C. § 1681i(a)(7)",
        "holding": (
            "The consumer reporting agency shall provide to the consumer a description "
            "of the procedure used to determine the accuracy and completeness of the "
            "information, including the business name and address of any furnisher "
            "of information contacted in connection with such information."
        ),
    },
    "sec_623_furnisher_accuracy": {
        "citation": "15 U.S.C. § 1681s-2(a)(1)(A)",
        "holding": (
            "A person shall not furnish any information relating to a consumer to any "
            "consumer reporting agency if the person knows or has reasonable cause to "
            "believe that the information is inaccurate."
        ),
    },
    "sec_623_post_dispute": {
        "citation": "15 U.S.C. § 1681s-2(b)",
        "holding": (
            "After receiving a notice of dispute from a consumer reporting agency, a "
            "furnisher must investigate the disputed information, review all relevant "
            "information, and report the results to the CRA — including modifying, "
            "deleting, or permanently blocking inaccurate or unverifiable information."
        ),
    },
    "sec_1681e_accuracy": {
        "citation": "15 U.S.C. § 1681e(b)",
        "holding": (
            "Whenever a consumer reporting agency prepares a consumer report it shall "
            "follow reasonable procedures to assure maximum possible accuracy of the "
            "information concerning the individual about whom the report relates."
        ),
    },
    "sec_1681n_willful": {
        "citation": "15 U.S.C. § 1681n",
        "holding": (
            "Any person who willfully fails to comply with any requirement imposed under "
            "the FCRA is liable for actual damages or statutory damages of $100–$1,000 "
            "per violation, plus punitive damages and attorney's fees."
        ),
    },
    "sec_1681o_negligent": {
        "citation": "15 U.S.C. § 1681o",
        "holding": (
            "Any person who negligently fails to comply with any requirement imposed "
            "under the FCRA is liable for actual damages and attorney's fees."
        ),
    },
    "direct_dispute_reg": {
        "citation": "12 C.F.R. § 1022.43",
        "holding": (
            "A furnisher must investigate direct disputes submitted by consumers unless "
            "the dispute is frivolous or irrelevant. Investigation must be completed within "
            "30 days of receipt. Results must be reported to all applicable CRAs."
        ),
    },
}

BUREAU_ADDRESSES = {
    "TransUnion": {
        "name": "TransUnion LLC",
        "address": "P.O. Box 2000\nChester, PA 19016",
        "dispute_url": "https://www.transunion.com/credit-disputes/dispute-your-credit",
    },
    "Experian": {
        "name": "Experian Information Solutions, Inc.",
        "address": "P.O. Box 4500\nAllen, TX 75013",
        "dispute_url": "https://www.experian.com/disputes/main.html",
    },
    "Equifax": {
        "name": "Equifax Information Services LLC",
        "address": "P.O. Box 740256\nAtlanta, GA 30374",
        "dispute_url": "https://www.equifax.com/personal/credit-report-services/credit-dispute/",
    },
}


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class DisputeAccount:
    """
    Represents a credit tradeline being disputed.

    Example:
        >>> account = DisputeAccount(
        ...     creditor_name="First Premier Bank",
        ...     account_type="Credit Card",
        ...     credit_limit=400.00,
        ...     reported_balance=777.00,
        ...     status="Charge-off",
        ...     charge_off_year=2022,
        ...     furnisher_address="First Premier Bank\\nP.O. Box 5524\\nSioux Falls, SD 57117-5524",
        ... )
    """
    creditor_name: str
    account_type: str
    credit_limit: float
    reported_balance: float
    status: str
    furnisher_address: str
    charge_off_year: Optional[int] = None
    account_last4: Optional[str] = None
    date_opened: Optional[str] = None
    date_of_first_delinquency: Optional[str] = None

    @property
    def utilization_pct(self) -> float:
        if self.credit_limit == 0:
            return 0.0
        return (self.reported_balance / self.credit_limit) * 100

    @property
    def over_limit_pct(self) -> float:
        return self.utilization_pct - 100.0

    @property
    def years_since_chargeoff(self) -> Optional[int]:
        if self.charge_off_year:
            return datetime.now().year - self.charge_off_year
        return None

    @property
    def profit_narrative(self) -> str:
        """Generate the furnisher-profit leverage narrative."""
        years = self.years_since_chargeoff
        year_str = f"approximately {years} year{'s' if years != 1 else ''}" if years else "multiple years"
        return (
            f"{self.creditor_name} has extracted significant commercial value from this "
            f"account over its lifetime: years of interest payments and fee revenue collected "
            f"prior to charge-off, a tax deduction on the charged-off balance under "
            f"26 U.S.C. § 166, and in all likelihood a sale of the debt to a third-party "
            f"buyer at a negotiated price — generating further proceeds. Despite having fully "
            f"monetized this account, {self.creditor_name} continues — {year_str} after "
            f"charge-off — to furnish and/or allow the furnishing of an inflated, over-limit "
            f"balance to all three major credit bureaus, causing ongoing, compounding harm to "
            f"consumer's creditworthiness with no remaining legitimate commercial justification. "
            f"This pattern of continued adverse reporting long after full profit extraction "
            f"supports a finding of willful noncompliance under FCRA § 1681n."
        )


@dataclass
class ConsumerProfile:
    """Consumer identity for dispute letters."""
    name: str
    address: str
    phone: str = ""
    email: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))


@dataclass
class DisputePacket:
    """
    Complete dispute packet for one account — all generated documents.

    Attributes:
        account: The disputed account
        bureau_disputes: Dict of bureau name → LegalDocument
        furnisher_dispute: Direct furnisher dispute LegalDocument
        case_notes: Summary notes for case file
        receipt_id: SintraPrime receipt identifier
    """
    account: DisputeAccount
    bureau_disputes: dict = field(default_factory=dict)
    furnisher_dispute: Optional[LegalDocument] = None
    case_notes: str = ""
    receipt_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CreditDisputeEngine:
    """
    Generates FCRA-compliant credit dispute documents for derogatory tradelines.

    DRAFT ONLY — no external submission without explicit human approval.

    Example:
        >>> engine = CreditDisputeEngine(
        ...     consumer=ConsumerProfile(
        ...         name="Isiah Tarik Howard",
        ...         address="Newark, NJ 07114",
        ...         phone="(908) 365-4234",
        ...         email="isiahh@ikesolutions.org",
        ...     )
        ... )
        >>> packet = engine.generate_all(account)
    """

    def __init__(self, consumer: ConsumerProfile):
        self.consumer = consumer

    def _bureau_dispute_text(self, account: DisputeAccount, bureau_key: str) -> str:
        bureau = BUREAU_ADDRESSES[bureau_key]
        c = self.consumer
        over_pct = int(account.over_limit_pct)
        util_pct = int(account.utilization_pct)

        return textwrap.dedent(f"""
        VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED

        {bureau["name"]}
        {bureau["address"]}

        Date: {c.date}

        RE: Formal Dispute of Inaccurate Tradeline — {account.creditor_name}
        Consumer: {c.name}

        To Whom It May Concern at {bureau["name"]}:

        I, {c.name}, hereby formally dispute the accuracy of the {account.creditor_name}
        tradeline currently appearing on my {bureau_key} consumer credit file pursuant to
        the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681 et seq., specifically
        §§ 611(a) and 623(a)(8). This dispute is submitted in good faith based on
        specific, verifiable inaccuracies.

        DISPUTED ACCOUNT DETAILS:
          Creditor:          {account.creditor_name}
          Account Type:      {account.account_type}
          Status:            {account.status}
          Credit Limit:      ${account.credit_limit:,.2f}
          Reported Balance:  ${account.reported_balance:,.2f}
          Reported Util.:    {util_pct}%

        GROUND 1 — BALANCE EXCEEDS CREDIT LIMIT BY {over_pct}% (Post-Charge-off
        Fee Inflation Since {account.charge_off_year or "~2022"})

        The reported balance of ${account.reported_balance:,.2f} on a credit limit of
        ${account.credit_limit:,.2f} is factually inaccurate absent an itemized breakdown
        of every fee and interest charge that produced it. This account charged off in or
        around {account.charge_off_year or "2022"}. Any balance above ${account.credit_limit:,.2f}
        consists entirely of post-charge-off accretions — fees, interest, and penalties —
        that must be individually identified and verified under FCRA § 623(a)(8). Reporting
        a consolidated lump balance without line-item transparency violates the maximum
        possible accuracy standard of FCRA § 1681e(b).

        GROUND 2 — PROFIT EXTRACTION ARGUMENT / ONGOING HARM WITHOUT PURPOSE

        {account.profit_narrative}

        GROUND 3 — CREDIT LIMIT OMITTED OR INACCURATELY REPORTED

        The absence or inaccuracy of the credit limit figure distorts the utilization
        calculation displayed to prospective creditors and automated underwriting systems,
        causing harm disproportionate to any accurate account history.

        GROUND 4 — METHOD OF VERIFICATION DEMAND (FCRA § 1681i(a)(7))

        Consumer formally demands the complete method of verification used during any prior
        reinvestigation of this tradeline, including: the name, business address, and
        telephone number of every person at {account.creditor_name} contacted; the date
        of contact; and the information provided by the furnisher in response.

        RELIEF REQUESTED:
          1. Conduct an immediate, reasonable reinvestigation of this tradeline.
          2. Delete or correct the inaccurate balance of ${account.reported_balance:,.2f}.
          3. Accurately reflect the credit limit of ${account.credit_limit:,.2f}.
          4. Provide the method of verification within the statutory period.
          5. If the account cannot be verified with specificity, delete the tradeline.

        LEGAL NOTICE: Failure to conduct a reasonable investigation and correct or delete
        inaccurate information may subject {bureau["name"]} to civil liability under
        FCRA § 1681n (willful noncompliance — actual damages or $100–$1,000 statutory
        damages per violation, plus punitive damages and attorney's fees) and § 1681o
        (negligent noncompliance — actual damages and attorney's fees). I reserve all
        rights and remedies available under the FCRA, FCBA, and applicable state law.

        I declare under penalty of perjury that the foregoing is true and correct.

        Respectfully submitted,

        ___________________________________
        {c.name}
        {c.address}
        {c.phone}
        {c.email}
        Date: _______________

        ENCLOSURES:
          - Copy of government-issued photo ID
          - Copy of Social Security card or equivalent
          - Copy of utility bill or bank statement confirming current address
          - Copy of {bureau_key} credit report excerpt showing disputed tradeline
        """).strip()

    def _furnisher_dispute_text(self, account: DisputeAccount) -> str:
        c = self.consumer
        util_pct = int(account.utilization_pct)
        over_pct = int(account.over_limit_pct)

        return textwrap.dedent(f"""
        VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED

        {account.furnisher_address}
        ATTN: Credit Dispute Department

        Date: {c.date}

        RE: Direct Dispute of Inaccurate Information Furnished to Credit Bureaus
            Account: {account.creditor_name} — {account.account_type}
            FCRA § 1681s-2(a)(8)(D) | 12 C.F.R. § 1022.43

        Consumer: {c.name} | {c.address} | {c.phone} | {c.email}

        To the Credit Dispute Department at {account.creditor_name}:

        I, {c.name}, hereby submit this direct dispute to {account.creditor_name} as
        the furnisher of the above-referenced account information pursuant to the Fair
        Credit Reporting Act, 15 U.S.C. § 1681s-2(a) and (b), the Fair Credit Billing
        Act, 15 U.S.C. § 1666 et seq., and Regulation V, 12 C.F.R. § 1022.43.

        As the entity that has directly furnished information about this account to
        TransUnion, Experian, and Equifax, you bear statutory responsibility for the
        completeness, accuracy, and integrity of all furnished information.

        DISPUTED ACCOUNT:
          Creditor:          {account.creditor_name}
          Account Type:      {account.account_type}
          Status:            {account.status}
          Credit Limit:      ${account.credit_limit:,.2f}
          Reported Balance:  ${account.reported_balance:,.2f}
          Reported Util.:    {util_pct}%

        GROUND 1 — OVER-LIMIT BALANCE WITHOUT ITEMIZATION ({over_pct}% OVER LIMIT)

        The balance of ${account.reported_balance:,.2f} on a ${account.credit_limit:,.2f}
        limit was impossible to incur within the credit limit alone. The excess
        ${account.reported_balance - account.credit_limit:,.2f} consists of fees and
        interest that must be individually itemized per FCRA § 623(a)(8). Furnishing a
        consolidated inflated balance without transparency violates your accuracy
        obligations under 15 U.S.C. § 1681s-2(a)(1)(A).

        GROUND 2 — PROFIT EXTRACTION / CONTINUED HARM WITHOUT JUSTIFICATION

        {account.profit_narrative}

        GROUND 3 — REQUEST FOR COMPLETE ACCOUNT RECORDS

        To verify the accuracy of any information you have furnished, consumer requests:
          a. Complete payment history from account opening through charge-off
          b. Itemized breakdown of all fees, interest, and penalties in reported balance
          c. Confirmation of original credit limit and any credit limit changes with dates
          d. Date of first delinquency (as defined under FCRA § 1681c(c))
          e. Name and contact of the person responsible for bureau reporting
          f. Copy of original signed credit/card agreement

        INFORMATION AND RELIEF DEMANDED:
          1. Investigate this dispute within 30 days per 12 C.F.R. § 1022.43
          2. Correct or delete the inaccurate balance of ${account.reported_balance:,.2f}
          3. Accurately report the credit limit of ${account.credit_limit:,.2f}
          4. Notify TransUnion, Experian, and Equifax of all corrections immediately
          5. Provide written confirmation of all corrections within 5 business days of
             completing investigation
          6. Provide written response to this dispute within the statutory 30-day period

        ESCALATION NOTICE: Failure to comply with this direct dispute will result in
        escalation to the Consumer Financial Protection Bureau, the Office of the
        Comptroller of the Currency, and private civil action under FCRA § 1681n (willful
        noncompliance — statutory damages up to $1,000 per violation, punitive damages,
        and attorney's fees) and § 1681o (negligent noncompliance). I reserve all rights.

        DRAFT — APPROVAL REQUIRED BEFORE SUBMISSION

        I declare under penalty of perjury that the foregoing is true and correct.

        Respectfully submitted,

        ___________________________________
        {c.name}
        {c.address}
        {c.phone}
        {c.email}
        Date: _______________

        ENCLOSURES:
          - Copy of government-issued photo ID
          - Credit report excerpt showing disputed tradeline (all three bureaus)
          - Copy of any prior dispute correspondence or responses
        """).strip()

    def generate_bureau_dispute(
        self, account: DisputeAccount, bureau_key: str
    ) -> LegalDocument:
        """Generate a bureau dispute letter for a single credit bureau."""
        text = self._bureau_dispute_text(account, bureau_key)
        return LegalDocument(
            title=f"{account.creditor_name} — {bureau_key} Bureau Dispute",
            court=f"{BUREAU_ADDRESSES[bureau_key]['name']}",
            case_number=f"DISPUTE-{account.creditor_name.replace(' ', '_').upper()}-{bureau_key.upper()}-{datetime.now().strftime('%Y%m%d')}",
            content=text,
            motion_type="credit_bureau_dispute",
            word_count=len(text.split()),
            citations=[
                FCRA_CITATIONS["sec_611_investigation"]["citation"],
                FCRA_CITATIONS["sec_611_method_of_verification"]["citation"],
                FCRA_CITATIONS["sec_1681e_accuracy"]["citation"],
                FCRA_CITATIONS["sec_623_furnisher_accuracy"]["citation"],
                FCRA_CITATIONS["sec_1681n_willful"]["citation"],
                FCRA_CITATIONS["sec_1681o_negligent"]["citation"],
            ],
            sections={
                "ground_1": "Balance Exceeds Credit Limit Without Itemization",
                "ground_2": "Profit Extraction / Ongoing Harm Without Purpose",
                "ground_3": "Credit Limit Omitted or Inaccurate",
                "ground_4": "Method of Verification Demand",
                "relief": "Delete or correct tradeline",
            },
            jurisdiction="consumer_fcra",
        )

    def generate_furnisher_dispute(self, account: DisputeAccount) -> LegalDocument:
        """Generate a direct furnisher dispute letter."""
        text = self._furnisher_dispute_text(account)
        return LegalDocument(
            title=f"{account.creditor_name} — Direct Furnisher Dispute",
            court=f"{account.creditor_name} — Credit Dispute Department",
            case_number=f"DISPUTE-{account.creditor_name.replace(' ', '_').upper()}-FURNISHER-{datetime.now().strftime('%Y%m%d')}",
            content=text,
            motion_type="direct_furnisher_dispute",
            word_count=len(text.split()),
            citations=[
                FCRA_CITATIONS["sec_623_furnisher_accuracy"]["citation"],
                FCRA_CITATIONS["sec_623_post_dispute"]["citation"],
                FCRA_CITATIONS["direct_dispute_reg"]["citation"],
                FCRA_CITATIONS["sec_1681n_willful"]["citation"],
                FCRA_CITATIONS["sec_1681o_negligent"]["citation"],
            ],
            sections={
                "ground_1": "Over-limit Balance Without Itemization",
                "ground_2": "Profit Extraction / Continued Harm Without Justification",
                "ground_3": "Request for Complete Account Records",
                "relief": "Correct/delete and notify all bureaus",
                "escalation": "CFPB / OCC / private civil action",
            },
            jurisdiction="consumer_fcra",
        )

    def generate_all(
        self,
        account: DisputeAccount,
        bureaus: list[str] | None = None,
    ) -> DisputePacket:
        """
        Generate the complete dispute packet for one account.

        Args:
            account: The disputed tradeline.
            bureaus: List of bureau names (defaults to all three).

        Returns:
            DisputePacket with all generated documents and case notes.
        """
        if bureaus is None:
            bureaus = ["TransUnion", "Experian", "Equifax"]

        bureau_disputes = {
            bureau: self.generate_bureau_dispute(account, bureau)
            for bureau in bureaus
        }
        furnisher_dispute = self.generate_furnisher_dispute(account)

        case_notes = (
            f"CASE: {account.creditor_name} Charge-off Dispute\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Status: DRAFT — Awaiting Isiah Howard approval before any submission\n\n"
            f"ACCOUNT: {account.account_type} | Limit: ${account.credit_limit:,.2f} | "
            f"Balance: ${account.reported_balance:,.2f} | Util: {int(account.utilization_pct)}%\n"
            f"Status: {account.status} | Charge-off year: {account.charge_off_year or 'unknown'}\n\n"
            f"LEVERAGE: {account.profit_narrative}\n\n"
            f"DOCUMENTS GENERATED:\n"
            + "\n".join(f"  - {bureau} Bureau Dispute" for bureau in bureaus)
            + f"\n  - Direct Furnisher Dispute to {account.creditor_name}\n\n"
            f"LEGAL THEORIES:\n"
            f"  - FCRA § 611 (reinvestigation obligation)\n"
            f"  - FCRA § 623(a)(8) (furnisher accuracy — over-limit balance without itemization)\n"
            f"  - FCRA § 611(a)(7) (method of verification demand)\n"
            f"  - FCRA § 1681e(b) (maximum possible accuracy)\n"
            f"  - FCRA § 1681n (willful noncompliance — statutory damages up to $1,000/violation)\n"
            f"  - 12 C.F.R. § 1022.43 (direct dispute — furnisher 30-day investigation duty)\n\n"
            f"ESCALATION PATH (if ignored):\n"
            f"  1. CFPB complaint\n"
            f"  2. OCC complaint\n"
            f"  3. Private civil action under FCRA § 1681n\n"
        )

        return DisputePacket(
            account=account,
            bureau_disputes=bureau_disputes,
            furnisher_dispute=furnisher_dispute,
            case_notes=case_notes,
        )


# ---------------------------------------------------------------------------
# Pre-configured Howard Recovery accounts
# ---------------------------------------------------------------------------

HOWARD_RECOVERY_CONSUMER = ConsumerProfile(
    name="Isiah Tarik Howard",
    address="Newark, NJ 07114",
    phone="(908) 365-4234",
    email="isiahh@ikesolutions.org",
)

FIRST_PREMIER_ACCOUNT = DisputeAccount(
    creditor_name="First Premier Bank",
    account_type="Credit Card",
    credit_limit=400.00,
    reported_balance=777.00,
    status="Charge-off",
    charge_off_year=2022,
    furnisher_address="First Premier Bank\nP.O. Box 5524\nSioux Falls, SD 57117-5524",
)

MERRICK_BANK_ACCOUNT = DisputeAccount(
    creditor_name="Merrick Bank",
    account_type="Credit Card",
    credit_limit=550.00,
    reported_balance=1064.00,
    status="Charge-off",
    charge_off_year=2022,
    furnisher_address="Merrick Bank\nP.O. Box 9201\nOld Bethpage, NY 11804-9001",
)


if __name__ == "__main__":
    engine = CreditDisputeEngine(consumer=HOWARD_RECOVERY_CONSUMER)

    for account in [FIRST_PREMIER_ACCOUNT, MERRICK_BANK_ACCOUNT]:
        packet = engine.generate_all(account)
        slug = account.creditor_name.replace(" ", "_").lower()
        print(f"\n{'='*60}")
        print(f"PACKET: {account.creditor_name}")
        print(f"{'='*60}")
        print(packet.case_notes)
        for bureau, doc in packet.bureau_disputes.items():
            fname = f"{slug}_{bureau.lower()}_bureau_dispute.txt"
            with open(fname, "w") as f:
                f.write(doc.content)
            print(f"  Written: {fname}")
        fname = f"{slug}_furnisher_dispute.txt"
        with open(fname, "w") as f:
            f.write(packet.furnisher_dispute.content)
        print(f"  Written: {fname}")
