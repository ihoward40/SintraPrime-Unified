"""Rare but defensible legal leverage catalog for SP-LEGAL-LEVERAGE.

The engine surfaces underused authorities only when transaction facts make them
potentially relevant.  It never converts a candidate into a merits conclusion.
Every lever includes trigger conditions, required proof, the practical move, and
an anti-overreach caveat.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class LegalLever:
    lever_id: str
    name: str
    authority: tuple[str, ...]
    trigger: str
    method: str
    evidence_needed: tuple[str, ...]
    effect: str
    caveat: str
    priority: int = 50

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class RareLegalLeverageEngine:
    """Suggest fact-dependent legal levers without asserting their merits."""

    def suggest(self, transaction_context: dict[str, Any]) -> list[LegalLever]:
        tx = self._text(transaction_context.get("transaction_type")).lower()
        jurisdiction = {self._text(x).lower() for x in transaction_context.get("jurisdiction", [])}
        evidence = {self._text(x).lower() for x in transaction_context.get("evidence", [])}
        status = self._text(transaction_context.get("matter_status")).lower()
        facts = {self._text(x).lower() for x in transaction_context.get("facts", [])}
        parties = transaction_context.get("parties", []) or []
        capacities = {
            self._text(p.get("capacity")).lower()
            for p in parties
            if isinstance(p, dict) and self._text(p.get("capacity"))
        }

        secured = (
            "secured" in tx
            or "consumer_obligor" in capacities
            or "debtor" in capacities
            or "security_agreement" in evidence
        )
        auto = "auto" in tx or "vehicle" in tx or "motor_vehicle" in facts
        post_disposition = bool({"collateral_sold", "disposition_occurred", "repossession_sale"} & (evidence | facts))
        credit_reporting = bool({"credit_reporting", "furnished_credit_data", "consumer_report"} & (evidence | facts))
        litigation = status in {"litigation", "filed", "discovery", "court"} or "pending_action" in facts
        seller_financed = bool({"retail_installment_contract", "seller_arranged_credit", "dealer_financing"} & (evidence | facts))

        levers: list[LegalLever] = []

        if secured:
            levers.append(
                LegalLever(
                    lever_id="LEV-UCC-9-210",
                    name="Authenticated accounting / statement-of-account request",
                    authority=("UCC § 9-210", "N.J.S.A. 12A:9-210 when New Jersey law governs"),
                    trigger="A debtor needs the secured party to state the unpaid secured obligation or approve/correct a proposed statement of account.",
                    method="Send an authenticated request that reasonably identifies the transaction and requests an accounting or approval/correction of a stated balance as of a specified date.",
                    evidence_needed=("debtor status", "secured transaction", "identified relationship", "proof of receipt"),
                    effect="The secured party generally must respond within 14 days; one response in each six-month period is available without charge under the uniform text.",
                    caveat="Use the statutory request format. A generic debt-validation letter is not automatically a § 9-210 request.",
                    priority=95,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-UCC-9-602",
                    name="Nonwaivable Article 9 rights audit",
                    authority=("UCC § 9-602", "N.J.S.A. 12A:9-602"),
                    trigger="A contract, waiver, repossession form, or settlement appears to waive core Article 9 debtor protections before default.",
                    method="Compare each purported waiver against the rights listed in § 9-602, including accounting, commercial reasonableness, notice, surplus/deficiency accounting, redemption, and remedies.",
                    evidence_needed=("contract", "waiver language", "default date", "disposition documents"),
                    effect="Certain Article 9 duties cannot be waived or varied to the debtor/obligor's detriment except where Article 9 specifically permits post-default waiver.",
                    caveat="Not every contractual term is invalid; the analysis must identify the exact right and timing of the purported waiver.",
                    priority=88,
                )
            )

        if post_disposition:
            levers.append(
                LegalLever(
                    lever_id="LEV-UCC-9-616",
                    name="14-day surplus/deficiency explanation demand",
                    authority=("UCC § 9-616", "N.J.S.A. 12A:9-616"),
                    trigger="Consumer-goods collateral has been disposed of and a deficiency is claimed or a surplus may exist.",
                    method="Send an authenticated post-disposition request for the statutory explanation of the surplus or deficiency calculation.",
                    evidence_needed=("disposition occurred", "consumer-goods transaction", "proof of request receipt"),
                    effect="The secured party generally must send the required explanation within 14 days after receipt of a qualifying request or, for a liable consumer obligor, send a record waiving the deficiency.",
                    caveat="The content and timing rules matter; do not confuse this with a pre-sale notice request.",
                    priority=100,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-UCC-9-615F",
                    name="Related-party low-sale deficiency recalculation",
                    authority=("UCC § 9-615(f)", "N.J.S.A. 12A:9-615(f)"),
                    trigger="Collateral was sold to the secured party, a related person, or a secondary obligor for proceeds significantly below a compliant arm's-length disposition.",
                    method="Identify the buyer and affiliations, obtain independent valuation evidence, and compare actual proceeds with proceeds a compliant sale to an unrelated transferee would have produced.",
                    evidence_needed=("buyer identity", "relationship evidence", "sale price", "independent value", "sale method"),
                    effect="For the statutory related-party scenario, surplus/deficiency may be calculated using the amount that would have been realized in a complying disposition rather than the depressed actual proceeds.",
                    caveat="Low price alone does not trigger § 9-615(f); the transferee relationship and significant price disparity are required.",
                    priority=92,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-UCC-9-625",
                    name="Article 9 noncompliance remedies / pre-disposition restraint",
                    authority=("UCC § 9-625", "N.J.S.A. 12A:9-625"),
                    trigger="There is provable Article 9 noncompliance, or a threatened noncompliant collection/enforcement/disposition can still be stopped.",
                    method="Map the precise violated Article 9 duty to available judicial restraint, actual damages, and any specifically authorized statutory damages.",
                    evidence_needed=("specific Article 9 duty", "noncompliance", "causation/damages where required"),
                    effect="A court may restrain noncompliant enforcement/disposition; Article 9 also provides damages and certain section-specific statutory remedies.",
                    caveat="Do not quote a statutory-damages amount unless the exact subsection applies. Remedies vary by violation and consumer-transaction context.",
                    priority=90,
                )
            )

        if "new jersey" in jurisdiction or "nj" in jurisdiction:
            if post_disposition:
                levers.append(
                    LegalLever(
                        lever_id="LEV-NJ-DEFICIENCY-PRESUMPTION",
                        name="New Jersey deficiency burden / collateral-value presumption",
                        authority=("Security Sav. Bank v. Tranchitella, 249 N.J. Super. 234 (App. Div. 1991)", "NJ Model Civil Jury Charge 4.44"),
                        trigger="A secured creditor seeks a deficiency and commercial reasonableness of the collateral sale is genuinely disputed.",
                        method="Force proof of commercially reasonable disposition and, if that proof fails, invoke the New Jersey presumption that collateral value equaled the debt unless the creditor rebuts it with competent valuation evidence.",
                        evidence_needed=("deficiency claim", "sale records", "commercial-reasonableness challenge", "valuation evidence"),
                        effect="If the creditor cannot establish commercial reasonableness and cannot rebut the value presumption, the claimed deficiency can collapse.",
                        caveat="This is a litigation burden framework, not an automatic pre-suit cancellation of debt. Apply current New Jersey law to the transaction and pleadings.",
                        priority=100,
                    )
                )

        if seller_financed or auto:
            levers.append(
                LegalLever(
                    lever_id="LEV-FTC-HOLDER-RULE",
                    name="FTC Holder Rule seller-defense pass-through",
                    authority=("16 C.F.R. Part 433", "FTC Holder in Due Course Rule"),
                    trigger="Consumer goods/services were financed through a seller-arranged consumer credit contract and the consumer has a viable claim or defense against the seller.",
                    method="Locate the Holder Rule notice in the retail installment contract, identify the seller-side claim/defense, and test whether it can be asserted against the assignee/holder.",
                    evidence_needed=("consumer credit contract", "seller-arranged financing", "seller claim or defense", "assignment/holder identity"),
                    effect="A qualifying holder takes the contract subject to claims and defenses the consumer could assert against the seller, subject to the Rule's recovery limitation.",
                    caveat="The Holder Rule does not create the underlying seller claim. First prove fraud, breach, nondelivery, warranty, or another valid seller-side theory.",
                    priority=91,
                )
            )

        if credit_reporting:
            levers.append(
                LegalLever(
                    lever_id="LEV-REGV-1022-43",
                    name="Regulation V direct furnisher dispute",
                    authority=("12 C.F.R. § 1022.43", "FCRA / Regulation V"),
                    trigger="A furnisher is reporting disputed liability, terms, payment status, balance, dates, or other account information bearing on creditworthiness.",
                    method="Send the dispute to the furnisher's proper direct-dispute address, identify the exact field(s), explain the basis, and attach relevant substantiation.",
                    evidence_needed=("consumer report", "specific disputed field", "account identity", "supporting documents", "proper dispute address"),
                    effect="A qualifying direct dispute requires a reasonable investigation, review of relevant information, timely results, and correction notice to CRAs if the furnisher determines the information was inaccurate.",
                    caveat="Regulation V contains subject-matter and credit-repair-organization exceptions. A vague 'verify everything' letter is weaker than a field-specific dispute.",
                    priority=96,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-REGV-ACCURACY-INTEGRITY",
                    name="Furnisher record-substantiation audit",
                    authority=("12 C.F.R. § 1022.42", "Appendix E to 12 C.F.R. Part 1022"),
                    trigger="The furnisher's own records, transfer history, dates, balances, or dispute handling appear inconsistent with what it reports.",
                    method="Build a field-level contradiction matrix tying each furnished data point to the furnisher record that should substantiate it; use that matrix to sharpen direct/CRA disputes and discovery.",
                    evidence_needed=("credit report fields", "furnisher statements", "payment ledger", "transfer/assignment history", "dispute responses"),
                    effect="Regulation V requires reasonable written accuracy/integrity procedures and the Appendix E guidelines emphasize substantiation, updating, transfer accuracy, record retention, and reasonable dispute investigations.",
                    caveat="Do not assume § 1022.42 itself creates a standalone private damages action. Use it primarily as a compliance benchmark, evidence target, and support for applicable FCRA dispute claims.",
                    priority=86,
                )
            )

        if litigation:
            levers.append(
                LegalLever(
                    lever_id="LEV-FRCP-36",
                    name="Requests for Admission — rule-based consequence for silence",
                    authority=("Fed. R. Civ. P. 36",),
                    trigger="A federal civil action is pending and narrow facts, document genuineness, or application-of-law-to-fact issues can be pinned down.",
                    method="Serve separately stated requests for admission on a party; track the response deadline and move on insufficient answers when appropriate.",
                    evidence_needed=("pending federal action", "proper service", "deadline calculation", "separately stated requests"),
                    effect="A matter is admitted if the opposing party fails to timely answer or object; an admission is conclusive in that pending action unless withdrawn or amended by the court.",
                    caveat="This is a real but narrow silence rule. It does not apply to unsolicited pre-suit affidavits, invoices, notices, or administrative letters.",
                    priority=98,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-FRCP-30B6",
                    name="Organization deposition — force a prepared institutional witness",
                    authority=("Fed. R. Civ. P. 30(b)(6)",),
                    trigger="A corporation/organization possesses institutional knowledge spread across employees, systems, servicing vendors, or records.",
                    method="Describe deposition topics with reasonable particularity and require the organization to designate and prepare witness(es) to testify about information known or reasonably available to it.",
                    evidence_needed=("pending federal action", "proper deposition notice/subpoena", "particularized topics"),
                    effect="Prevents the organization from defeating discovery merely by claiming no single employee personally knows the whole story.",
                    caveat="Topic scope must remain proportional and discoverable; state-court analogues have their own rules and numbering.",
                    priority=94,
                )
            )
            levers.append(
                LegalLever(
                    lever_id="LEV-FRCP-37E",
                    name="ESI preservation / spoliation proof architecture",
                    authority=("Fed. R. Civ. P. 37(e)",),
                    trigger="Relevant electronically stored information should have been preserved in anticipation or conduct of federal litigation and may have been lost.",
                    method="Identify the preservation trigger, custodians, systems, retention periods, lost data, reasonable steps, ability to restore/replace, prejudice, and—if seeking severe sanctions—evidence of intent to deprive.",
                    evidence_needed=("foreseeability/pending litigation", "specific ESI", "preservation duty", "loss", "failed reasonable steps", "nonreplaceability"),
                    effect="The court may order curative measures for prejudice and severe measures only on the rule's heightened intent finding.",
                    caveat="A preservation letter does not automatically create sanctions. Rule 37(e) requires the statutory sequence of duty, loss, failed reasonable steps, and inability to restore or replace.",
                    priority=89,
                )
            )

        return sorted(levers, key=lambda item: (-item.priority, item.lever_id))

    @staticmethod
    def _text(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
