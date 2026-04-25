"""
Credit Report Analyzer — Parse and display credit report data beautifully.
Generates ASCII credit dashboards and full dispute packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DisputePackage:
    """Complete credit dispute package."""
    cover_letter: str
    dispute_letters: List[str] = field(default_factory=list)
    tracking_instructions: str = ""
    follow_up_timeline: str = ""
    account_summary: str = ""

    @property
    def full_package(self) -> str:
        parts = [self.cover_letter]
        for i, letter in enumerate(self.dispute_letters, 1):
            parts.append(f"\n{'='*70}\n  DISPUTE LETTER #{i}\n{'='*70}\n")
            parts.append(letter)
        parts.append(f"\n{'='*70}\n  TRACKING & FOLLOW-UP INSTRUCTIONS\n{'='*70}\n")
        parts.append(self.tracking_instructions)
        parts.append(self.follow_up_timeline)
        return "\n\n".join(parts)


class CreditReportAnalyzer:
    """
    Analyzes credit report data and generates beautiful ASCII dashboards,
    dispute letters, and actionable recommendations.
    """

    SCORE_RANGES = [
        (800, 850, "EXCEPTIONAL", "████████████████████"),
        (740, 799, "VERY GOOD",   "████████████████░░░░"),
        (670, 739, "GOOD",        "████████████░░░░░░░░"),
        (580, 669, "FAIR",        "████████░░░░░░░░░░░░"),
        (300, 579, "POOR",        "████░░░░░░░░░░░░░░░░"),
    ]

    FACTOR_WEIGHTS = {
        "Payment History":       35,
        "Amounts Owed":          30,
        "Length of History":     15,
        "Credit Mix":            10,
        "New Credit":            10,
    }

    WIDTH = 44

    # ------------------------------------------------------------------
    # Credit Dashboard
    # ------------------------------------------------------------------

    def generate_credit_dashboard(self, profile: Dict[str, Any]) -> str:
        """Generate a beautiful ASCII credit score dashboard."""
        W = self.WIDTH

        score = int(profile.get("score", 700))
        name = profile.get("name", "[YOUR NAME]")
        date = profile.get("date", datetime.now().strftime("%B %d, %Y"))
        bureau = profile.get("bureau", "Equifax / Experian / TransUnion")

        payment_pct = profile.get("payment_history_pct", 98)
        utilization_pct = profile.get("utilization_pct", 18)
        history_years = profile.get("history_years", 7)
        accounts = profile.get("total_accounts", 8)
        derogatory = profile.get("derogatory_marks", 0)
        inquiries = profile.get("hard_inquiries", 2)

        # Score label and gauge
        score_label = "UNKNOWN"
        score_bar = "░" * 20
        for low, high, label, bar in self.SCORE_RANGES:
            if low <= score <= high:
                score_label = label
                score_bar = bar
                break

        # Score gauge (300–850 range on 40 chars)
        gauge_width = 40
        gauge_pos = int((score - 300) / 550 * gauge_width)
        gauge = "▓" * gauge_pos + "▲" + "░" * (gauge_width - gauge_pos - 1)

        lines = []
        lines.append("  ╔══════════════════════════════════════════╗")
        lines.append("  ║     CREDIT INTELLIGENCE REPORT           ║")
        lines.append("  ║         Powered by SintraPrime           ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append(f"  ║  Name:   {name[:30]:<30}  ║")
        lines.append(f"  ║  Date:   {date[:30]:<30}  ║")
        lines.append(f"  ║  Bureau: {bureau[:30]:<30}  ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║                                          ║")

        # Large score display
        score_str = str(score)
        score_display = f"SCORE:  {score_str}  [{score_label}]"
        lines.append(f"  ║  {score_display:<40}  ║")
        lines.append(f"  ║  [{score_bar}]  ║")
        lines.append("  ║                                          ║")

        # Gauge
        lines.append(f"  ║  POOR    FAIR    GOOD    V.GOOD  EXCEL  ║")
        lines.append(f"  ║  [{gauge}]  ║")
        lines.append(f"  ║  300                               850   ║")
        lines.append("  ║                                          ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  SCORE FACTORS              IMPACT       ║")
        lines.append("  ╠══════════════════════════════════════════╣")

        # Payment history
        ph_bar = self._make_bar(payment_pct, 12)
        lines.append(f"  ║  Payment History    {ph_bar}  {payment_pct:>3}%   ║")

        # Utilization
        util_bar = self._make_bar(100 - utilization_pct, 12)  # lower is better
        util_label = "LOW ✓" if utilization_pct <= 30 else "HIGH ✗"
        lines.append(f"  ║  Credit Usage       {util_bar}  {utilization_pct:>3}% {util_label}  ║")

        # History
        hist_score = min(100, history_years * 10)
        hist_bar = self._make_bar(hist_score, 12)
        lines.append(f"  ║  Credit Age         {hist_bar}  {history_years}yrs   ║")

        # Accounts
        acct_bar = self._make_bar(min(100, accounts * 10), 12)
        lines.append(f"  ║  Total Accounts     {acct_bar}  {accounts:>3}       ║")

        # Inquiries
        inq_score = max(0, 100 - inquiries * 15)
        inq_bar = self._make_bar(inq_score, 12)
        lines.append(f"  ║  Hard Inquiries     {inq_bar}  {inquiries:>3}       ║")

        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  DEROGATORY MARKS                        ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        if derogatory == 0:
            lines.append("  ║  ✓ No derogatory marks — Excellent!      ║")
        else:
            lines.append(f"  ║  ✗ {derogatory} derogatory mark(s) found          ║")

        # What's helping / hurting
        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  WHAT'S HELPING YOUR SCORE               ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        positives = profile.get("positives", [
            "On-time payment history",
            "Low credit card utilization" if utilization_pct <= 30 else None,
            "Long credit history" if history_years >= 7 else None,
            "No derogatory marks" if derogatory == 0 else None,
        ])
        for pos in positives:
            if pos:
                lines.append(f"  ║  + {str(pos)[:37]:<37}  ║")

        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  WHAT'S HURTING YOUR SCORE               ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        negatives = profile.get("negatives", [
            "High credit utilization" if utilization_pct > 30 else None,
            f"{derogatory} derogatory mark(s)" if derogatory > 0 else None,
            f"{inquiries} recent hard inquiries" if inquiries > 2 else None,
            "Short credit history" if history_years < 3 else None,
        ])
        has_negatives = False
        for neg in negatives:
            if neg:
                lines.append(f"  ║  - {str(neg)[:37]:<37}  ║")
                has_negatives = True
        if not has_negatives:
            lines.append("  ║  - Nothing significant at this time      ║")

        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  RECOMMENDED ACTIONS                     ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        recommendations = profile.get("recommendations", self._auto_recommendations(profile))
        for i, rec in enumerate(recommendations[:6], 1):
            lines.append(f"  ║  {i}. {str(rec)[:35]:<35}  ║")

        lines.append("  ╠══════════════════════════════════════════╣")
        lines.append("  ║  SCORE IMPROVEMENT TIMELINE              ║")
        lines.append("  ╠══════════════════════════════════════════╣")
        target = profile.get("target_score", min(850, score + 50))
        timeline = profile.get("timeline", "6-12 months")
        lines.append(f"  ║  Target Score: {target:<10} Est. Time: {timeline[:8]:<8}  ║")
        lines.append("  ╚══════════════════════════════════════════╝")

        disclaimer = "\n  * This is an educational credit analysis tool. Not a credit monitoring service."
        return "\n".join(lines) + disclaimer

    def _make_bar(self, pct: float, width: int = 12) -> str:
        """Create a filled bar representing a percentage."""
        pct = max(0, min(100, float(pct or 0)))
        filled = int(pct / 100 * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def _auto_recommendations(self, profile: Dict[str, Any]) -> List[str]:
        recs = []
        utilization = profile.get("utilization_pct", 50)
        derogatory = profile.get("derogatory_marks", 0)
        inquiries = profile.get("hard_inquiries", 0)
        payment_pct = profile.get("payment_history_pct", 90)

        if payment_pct < 100:
            recs.append("Enable autopay to ensure 100% on-time payments")
        if utilization > 30:
            recs.append(f"Pay down balances to below 30% utilization")
        if utilization > 10:
            recs.append("Request credit limit increases without hard pull")
        if derogatory > 0:
            recs.append("Dispute inaccurate derogatory marks with bureaus")
            recs.append("Send goodwill letters for paid late accounts")
        if inquiries > 2:
            recs.append("Avoid new credit applications for 6+ months")
        recs.append("Keep oldest accounts open to maintain credit age")
        recs.append("Diversify credit mix (installment + revolving)")
        if not recs:
            recs.append("Maintain current excellent habits")
        return recs

    # ------------------------------------------------------------------
    # Dispute Package Generator
    # ------------------------------------------------------------------

    def dispute_package_generator(self, accounts: List[Dict[str, Any]]) -> DisputePackage:
        """Generate a complete credit dispute package."""
        date_str = datetime.now().strftime("%B %d, %Y")

        # Cover letter to all bureaus
        cover = self._dispute_cover_letter(accounts, date_str)

        # Individual dispute letters per bureau
        bureaus = ["Equifax", "Experian", "TransUnion"]
        dispute_letters = []
        for bureau in bureaus:
            # Filter accounts that should be disputed with this bureau
            bureau_accounts = [a for a in accounts
                               if bureau.lower() in [b.lower() for b in a.get("bureaus", bureaus)]]
            if bureau_accounts:
                dispute_letters.append(
                    self._dispute_letter_to_bureau(bureau, bureau_accounts, date_str)
                )

        tracking = self._tracking_instructions(bureaus, date_str)
        timeline = self._follow_up_timeline(date_str)
        account_summary = self._account_summary_table(accounts)

        return DisputePackage(
            cover_letter=cover,
            dispute_letters=dispute_letters,
            tracking_instructions=tracking,
            follow_up_timeline=timeline,
            account_summary=account_summary,
        )

    def _dispute_cover_letter(self, accounts: List[Dict[str, Any]], date_str: str) -> str:
        num_items = len(accounts)
        return f"""\
CREDIT DISPUTE COVER LETTER — MASTER PACKAGE
Generated by SintraPrime-Unified Credit Intelligence
Date: {date_str}

TO: All Three Major Credit Bureaus
    Equifax | Experian | TransUnion

RE: Formal Credit Report Dispute — {num_items} Item(s)

This package contains formal credit report dispute letters addressing
{num_items} inaccurate, outdated, or unverifiable item(s) on my credit
reports pursuant to the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681.

DISPUTED ACCOUNTS SUMMARY:
{self._account_summary_table(accounts)}

INSTRUCTIONS FOR USE:
1. Sign each dispute letter.
2. Attach copies of supporting documents (ID, account statements, etc.).
3. Send via CERTIFIED MAIL with RETURN RECEIPT REQUESTED to each bureau.
4. Keep copies of everything.
5. Note the certified mail tracking numbers below.
6. Follow up after 30 days if no response received.

Each bureau has 30 days to investigate and respond (45 days if based on
an annual free credit report request).

Your Rights Under the FCRA:
• Free annual credit reports from AnnualCreditReport.com
• Free report after dispute investigation
• Notification of reinsertion of deleted items
• Ability to add 100-word statement to your file
• Sue in federal court for FCRA violations ($1,000 + attorney fees)
"""

    def _account_summary_table(self, accounts: List[Dict[str, Any]]) -> str:
        lines = []
        lines.append("  ┌──────────────────────────┬────────────────┬──────────────────┐")
        lines.append("  │ CREDITOR / ACCOUNT        │ ACCOUNT NO.    │ DISPUTE REASON   │")
        lines.append("  ├──────────────────────────┼────────────────┼──────────────────┤")
        for acct in accounts:
            creditor = str(acct.get("creditor", "[CREDITOR]"))[:26].ljust(26)
            acct_no = str(acct.get("account_number", "XXXX"))[:14].ljust(14)
            reason = str(acct.get("dispute_reason", "Inaccurate"))[:18].ljust(18)
            lines.append(f"  │ {creditor} │ {acct_no} │ {reason} │")
        lines.append("  └──────────────────────────┴────────────────┴──────────────────┘")
        return "\n".join(lines)

    def _dispute_letter_to_bureau(
        self,
        bureau: str,
        accounts: List[Dict[str, Any]],
        date_str: str,
    ) -> str:
        bureau_addresses = {
            "Equifax": "Equifax Information Services LLC\nP.O. Box 740256\nAtlanta, GA 30374-0256",
            "Experian": "Experian\nP.O. Box 4500\nAllen, TX 75013",
            "TransUnion": "TransUnion LLC\nConsumer Dispute Center\nP.O. Box 2000\nChester, PA 19016",
        }
        address = bureau_addresses.get(bureau, f"{bureau}\n[BUREAU ADDRESS]")

        dispute_items = ""
        for i, acct in enumerate(accounts, 1):
            creditor = acct.get("creditor", "[CREDITOR NAME]")
            acct_no = acct.get("account_number", "[ACCOUNT NUMBER]")
            reported_amount = acct.get("amount", "[AMOUNT]")
            dispute_reason = acct.get("dispute_reason", "This information is inaccurate and cannot be verified.")
            supporting_docs = acct.get("supporting_docs", ["[LIST SUPPORTING DOCUMENTS]"])

            dispute_items += f"""
DISPUTED ITEM #{i}:
  Creditor:         {creditor}
  Account Number:   {acct_no}
  Amount Reported:  ${reported_amount}
  Dispute Reason:   {dispute_reason}
  Supporting Docs:  {', '.join(supporting_docs)}
  Requested Action: [DELETE / CORRECT] this account from my credit file.
"""

        return f"""\
[YOUR FULL NAME]
[YOUR ADDRESS]
[CITY, STATE ZIP]
[YOUR PHONE]
[YOUR EMAIL]
SSN (last 4 only): XXX-XX-[LAST 4]
Date of Birth: [DOB]
Date: {date_str}

VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED
Certified Mail No.: ______________________________

{address}

  Re: FORMAL CREDIT REPORT DISPUTE — {len(accounts)} ITEM(S)

To Whom It May Concern:

I am writing pursuant to the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681i,
to formally dispute the following inaccurate information currently appearing on
my {bureau} credit report.

{dispute_items}

ENCLOSED DOCUMENTS:
  [ ] Copy of government-issued photo ID
  [ ] Copy of Social Security card or utility bill
  [ ] Copy of my {bureau} credit report with disputed items circled
  [ ] [SUPPORTING DOCUMENTS SPECIFIC TO EACH DISPUTE]

Per FCRA § 1681i, you are required to:
  1. Conduct a reasonable investigation within 30 days;
  2. Forward my dispute to the furnisher of information;
  3. Delete or correct inaccurate, incomplete, or unverifiable information;
  4. Provide me with written results of the investigation;
  5. Send a revised credit report reflecting any corrections.

If you cannot verify the accuracy of any disputed item within the
required time period, you must PERMANENTLY DELETE it from my credit file.

Please send all correspondence to the address above. Do NOT call.

                              Sincerely,
                              _________________________________
                              [YOUR FULL NAME]
                              Date: {date_str}
"""

    def _tracking_instructions(self, bureaus: List[str], date_str: str) -> str:
        lines = [
            "CERTIFIED MAIL TRACKING",
            "=" * 50,
            f"Date Mailed: {date_str}",
            "",
            "BUREAU               CERTIFIED MAIL NO.       DATE SENT",
            "─" * 60,
        ]
        for bureau in bureaus:
            lines.append(f"{bureau:<20} {'_' * 25}  {date_str}")
        lines += [
            "",
            "INSTRUCTIONS:",
            "1. Mail each letter via USPS Certified Mail with Return Receipt.",
            "2. Keep your USPS receipt with the certified mail article number.",
            "3. Track delivery at usps.com/tracking.",
            "4. Keep the signed green card (PS Form 3811) as proof of delivery.",
            "5. Log the delivery date — your 30-day investigation clock starts.",
            "",
            "RETURN RECEIPT TRACKING:",
            f"  Equifax delivered:     __________________",
            f"  Experian delivered:    __________________",
            f"  TransUnion delivered:  __________________",
        ]
        return "\n".join(lines)

    def _follow_up_timeline(self, date_str: str) -> str:
        return f"""\
FOLLOW-UP TIMELINE
{'='*50}

WEEK 1-2 ({date_str}):
  ✓ Mail all dispute letters via certified mail
  ✓ Save copies of all letters and documents
  ✓ Record certified mail tracking numbers

DAY 30 (30 days after mailing):
  □ If no response: Send follow-up letter referencing original dispute
  □ Check online portals (Equifax, Experian, TransUnion) for updates
  □ Request investigation results in writing

DAY 35-45 (bureau investigation window):
  □ Review investigation results carefully
  □ If item deleted: Pull new credit report to confirm removal
  □ If item remains: Prepare escalation strategy

ESCALATION OPTIONS (if dispute unsuccessful):
  1. Re-dispute with additional evidence
  2. File CFPB complaint at ConsumerFinance.gov
  3. File FTC complaint at ReportFraud.ftc.gov
  4. Consult consumer protection attorney (FCRA violations = $1,000+ damages)
  5. Add 100-word consumer statement to credit file

IMPORTANT CONTACTS:
  Equifax:     1-866-349-5191  |  equifax.com/personal/disputes
  Experian:    1-888-397-3742  |  experian.com/disputes
  TransUnion:  1-800-916-8800  |  transunion.com/credit-disputes
  CFPB:        1-855-411-2372  |  consumerfinance.gov/complaint
  FTC:         1-877-382-4357  |  reportfraud.ftc.gov
"""
