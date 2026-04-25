"""
Credit Mastery Module — The ultimate credit intelligence system.
Replaces a credit consultant and credit repair specialist.
Covers FICO/VantageScore optimization, dispute letters, repair strategies,
business credit building, and comprehensive credit law knowledge.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date


# ─────────────────────────────────────────────────────────────────────────────
# LEGAL REFERENCE DATA
# ─────────────────────────────────────────────────────────────────────────────

CREDIT_LAWS: Dict[str, Dict[str, Any]] = {
    "FCRA": {
        "full_name": "Fair Credit Reporting Act",
        "usc": "15 U.S.C. § 1681 et seq.",
        "key_provisions": [
            "Section 611: Right to dispute inaccurate information (30-day investigation)",
            "Section 609: Right to access your credit report",
            "Section 605: Obsolescence — most negatives must be removed after 7 years",
            "Section 605B: Identity theft block (5 business days after affidavit)",
            "Section 616: Civil liability for willful noncompliance — actual + punitive damages",
            "Section 617: Civil liability for negligent noncompliance — actual damages",
            "Section 623: Furnisher duties — must investigate consumer disputes",
            "Section 604: Permissible purposes for obtaining credit report",
        ],
        "remedies": [
            "Actual damages (no minimum)",
            "Statutory damages: $100–$1,000 per willful violation",
            "Punitive damages (court discretion)",
            "Attorney fees and costs",
        ],
        "statute_of_limitations": "2 years from discovery, 5 years from violation",
    },
    "FDCPA": {
        "full_name": "Fair Debt Collection Practices Act",
        "usc": "15 U.S.C. § 1692 et seq.",
        "key_provisions": [
            "Section 1692b: Restrictions on contacting third parties",
            "Section 1692c: Communication restrictions (times, places, represented persons)",
            "Section 1692d: Prohibition on harassment or abuse",
            "Section 1692e: Prohibition on false or misleading representations",
            "Section 1692f: Prohibition on unfair practices",
            "Section 1692g: 30-day debt validation right upon written request",
            "Section 1692k: Civil liability",
        ],
        "remedies": [
            "Actual damages",
            "Statutory damages up to $1,000 per lawsuit",
            "Attorney fees and costs",
            "Class action: up to $500,000 or 1% of net worth",
        ],
        "statute_of_limitations": "1 year from violation",
    },
    "ECOA": {
        "full_name": "Equal Credit Opportunity Act",
        "usc": "15 U.S.C. § 1691 et seq.",
        "key_provisions": [
            "Prohibits discrimination based on race, color, religion, national origin, sex, marital status, age, or receipt of public assistance",
            "Adverse action notice required within 30 days of application",
            "Must provide specific reasons for credit denial",
            "Regulation B (12 CFR Part 202) implements ECOA",
        ],
        "remedies": [
            "Actual and punitive damages (up to $10,000 individual, $500,000 class action)",
            "Equitable relief",
            "Attorney fees",
        ],
        "statute_of_limitations": "2 years from violation",
    },
    "FCBA": {
        "full_name": "Fair Credit Billing Act",
        "usc": "15 U.S.C. § 1666 et seq.",
        "key_provisions": [
            "Right to dispute billing errors within 60 days",
            "Creditor must acknowledge within 30 days, resolve within 2 billing cycles (max 90 days)",
            "Cannot report disputed amount as delinquent during investigation",
            "Applies to open-end credit (credit cards, lines of credit)",
            "Chargeback rights for goods/services not received or misrepresented",
        ],
        "remedies": [
            "Forfeiture of disputed amount up to $50",
            "Actual damages",
            "Statutory damages",
        ],
        "statute_of_limitations": "1 year from violation",
    },
    "TILA": {
        "full_name": "Truth in Lending Act",
        "usc": "15 U.S.C. § 1601 et seq.",
        "key_provisions": [
            "Requires disclosure of APR, finance charges, amount financed",
            "Regulation Z (12 CFR Part 1026) implements TILA",
            "Right of rescission: 3 business days for non-purchase mortgage transactions",
            "Requires periodic statements for credit accounts",
            "Restricts credit card practices (ability to pay, rate increases)",
        ],
        "remedies": [
            "Actual damages",
            "Statutory damages: twice the finance charge (min $200, max $2,000) for closed-end credit",
            "Up to $1 million in class actions",
            "Attorney fees",
        ],
        "statute_of_limitations": "1 year for damages, 3 years for rescission",
    },
    "RESPA": {
        "full_name": "Real Estate Settlement Procedures Act",
        "usc": "12 U.S.C. § 2601 et seq.",
        "key_provisions": [
            "Requires Good Faith Estimate / Loan Estimate at application",
            "Requires Closing Disclosure 3 business days before closing",
            "Prohibits kickbacks and unearned fees (Section 8)",
            "Escrow account limits and annual analysis requirements",
            "Servicing transfer notice requirements",
            "Qualified Written Request (QWR) — servicer must respond in 5 business days",
        ],
        "remedies": [
            "Section 8 violations: Treble damages (3x the charge)",
            "QWR violations: Actual damages + statutory damages up to $2,000",
            "Attorney fees and costs",
        ],
        "statute_of_limitations": "1 year (Section 8), 3 years (Section 6)",
    },
}

STATE_SOL: Dict[str, Dict[str, Any]] = {
    "AL": {"years": 6, "note": "Written contracts; open accounts 6 years"},
    "AK": {"years": 3, "note": "Open accounts 3 years; written contracts 3 years"},
    "AZ": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "AR": {"years": 5, "note": "Written and oral contracts 5 years"},
    "CA": {"years": 4, "note": "Written contracts 4 years; oral 2 years"},
    "CO": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "CT": {"years": 6, "note": "Written contracts 6 years"},
    "DC": {"years": 3, "note": "Written contracts 3 years"},
    "DE": {"years": 3, "note": "Written contracts 3 years"},
    "FL": {"years": 5, "note": "Written contracts 5 years; oral 4 years"},
    "GA": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "HI": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "ID": {"years": 5, "note": "Written contracts 5 years"},
    "IL": {"years": 5, "note": "Written contracts 5 years; open accounts 5 years"},
    "IN": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "IA": {"years": 5, "note": "Written contracts 5 years"},
    "KS": {"years": 5, "note": "Written contracts 5 years; open accounts 3 years"},
    "KY": {"years": 5, "note": "Written contracts 5 years; open accounts 5 years"},
    "LA": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "ME": {"years": 6, "note": "Written contracts 6 years"},
    "MD": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "MA": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "MI": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "MN": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "MS": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "MO": {"years": 5, "note": "Written contracts 5 years; open accounts 5 years"},
    "MT": {"years": 5, "note": "Written contracts 5 years"},
    "NE": {"years": 5, "note": "Written contracts 5 years; open accounts 4 years"},
    "NV": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "NH": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "NJ": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "NM": {"years": 6, "note": "Written contracts 6 years"},
    "NY": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "NC": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "ND": {"years": 6, "note": "Written contracts 6 years"},
    "OH": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "OK": {"years": 5, "note": "Written contracts 5 years; open accounts 3 years"},
    "OR": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "PA": {"years": 4, "note": "Written contracts 4 years; open accounts 4 years"},
    "RI": {"years": 10, "note": "Written contracts 10 years; open accounts 10 years"},
    "SC": {"years": 3, "note": "Written contracts 3 years; open accounts 3 years"},
    "SD": {"years": 6, "note": "Written contracts 6 years"},
    "TN": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "TX": {"years": 4, "note": "Written contracts 4 years; open accounts 4 years"},
    "UT": {"years": 6, "note": "Written contracts 6 years; open accounts 4 years"},
    "VT": {"years": 6, "note": "Written contracts 6 years"},
    "VA": {"years": 5, "note": "Written contracts 5 years; open accounts 3 years"},
    "WA": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "WV": {"years": 10, "note": "Written contracts 10 years; open accounts 10 years"},
    "WI": {"years": 6, "note": "Written contracts 6 years; open accounts 6 years"},
    "WY": {"years": 8, "note": "Written contracts 8 years; open accounts 8 years"},
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CreditProfile:
    """Complete consumer credit profile with all FICO scoring factors."""
    fico_score: int
    vantage_score: int
    payment_history_pct: float          # 35% of FICO score
    amounts_owed_utilization: float     # 30% of FICO score (0.0–1.0)
    length_of_history_months: int       # 15% of FICO score
    credit_mix: List[str]               # 10% of FICO score
    new_credit_inquiries: int           # 10% of FICO score
    derogatory_marks: List[str]         # Collections, chargeoffs, BK, liens
    positive_accounts: List[str]        # Good standing accounts
    oldest_account_months: int = 0
    total_accounts: int = 0
    open_accounts: int = 0
    revolving_utilization: float = 0.0
    installment_utilization: float = 0.0

    def credit_tier(self) -> str:
        """Return the credit tier based on FICO score."""
        if self.fico_score >= 800:
            return "Exceptional"
        elif self.fico_score >= 740:
            return "Very Good"
        elif self.fico_score >= 670:
            return "Good"
        elif self.fico_score >= 580:
            return "Fair"
        else:
            return "Poor"

    def score_gap_to_next_tier(self) -> Tuple[str, int]:
        """Returns (next_tier_name, points_needed)."""
        tiers = [(580, "Fair"), (670, "Good"), (740, "Very Good"), (800, "Exceptional"), (850, "Perfect")]
        for threshold, name in tiers:
            if self.fico_score < threshold:
                return name, threshold - self.fico_score
        return "Perfect", 0


@dataclass
class CreditAction:
    """A specific action to improve credit score."""
    action: str
    priority: int                       # 1 = highest priority
    expected_score_increase: int        # estimated FICO point improvement
    timeline_days: int                  # days to see improvement
    difficulty: str                     # easy / medium / hard
    instructions: str
    cost: float = 0.0                   # estimated dollar cost
    legal_authority: str = ""           # relevant law/regulation


@dataclass
class DisputeLetter:
    """A formatted credit dispute letter."""
    dispute_type: str
    recipient: str                      # Equifax / Experian / TransUnion / Furnisher
    account_name: str
    account_number: str
    legal_basis: str
    letter_body: str
    enclosures: List[str]
    certified_mail_required: bool = True

    def format_as_text(self) -> str:
        """Render a professional dispute letter."""
        today = datetime.now().strftime("%B %d, %Y")
        lines = [
            f"{'═' * 70}",
            f"  CREDIT DISPUTE LETTER",
            f"  {self.dispute_type.upper()}",
            f"{'═' * 70}",
            f"",
            f"Date: {today}",
            f"",
            f"To: {self.recipient}",
            f"Re: Account: {self.account_name} | #{self.account_number}",
            f"Legal Basis: {self.legal_basis}",
            f"",
            "─" * 70,
            "",
            self.letter_body,
            "",
            "─" * 70,
            "",
            "Enclosures:",
        ]
        for enc in self.enclosures:
            lines.append(f"  • {enc}")
        lines += [
            "",
            "Sent via: Certified Mail with Return Receipt Requested" if self.certified_mail_required else "",
            f"{'═' * 70}",
        ]
        return "\n".join(lines)


@dataclass
class CreditRepairPlan:
    """Comprehensive plan to remove derogatory items."""
    total_derogatory_items: int
    items: List[Dict[str, Any]]
    estimated_score_improvement: int
    timeline_months: int
    total_cost_estimate: float
    priority_actions: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 68 + "╗",
            "║  CREDIT REPAIR PLAN" + " " * 48 + "║",
            "╚" + "═" * 68 + "╝",
            "",
            f"  Derogatory Items:        {self.total_derogatory_items}",
            f"  Est. Score Improvement:  +{self.estimated_score_improvement} points",
            f"  Timeline:                {self.timeline_months} months",
            f"  Estimated Cost:          ${self.total_cost_estimate:,.2f}",
            "",
            "  PRIORITY ACTIONS:",
            "  " + "─" * 60,
        ]
        for i, action in enumerate(self.priority_actions, 1):
            lines.append(f"  {i:2d}. {action}")
        lines.append("")
        lines.append("  ITEM BREAKDOWN:")
        lines.append("  " + "─" * 60)
        for item in self.items:
            lines.append(f"  • {item.get('name', 'Unknown')}: {item.get('strategy', 'Dispute')}")
        return "\n".join(lines)


@dataclass
class CreditBuildingRoadmap:
    """Step-by-step roadmap to build credit from zero."""
    starting_score: Optional[int]
    target_score: int
    timeline_months: int
    phases: List[Dict[str, Any]]
    estimated_monthly_cost: float
    first_steps: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 68 + "╗",
            "║  CREDIT BUILDING ROADMAP — ZERO TO 700+" + " " * 27 + "║",
            "╚" + "═" * 68 + "╝",
            "",
            f"  Starting Score:   {self.starting_score or 'No File'}",
            f"  Target Score:     {self.target_score}+",
            f"  Timeline:         {self.timeline_months} months",
            f"  Monthly Cost Est: ${self.estimated_monthly_cost:.2f}",
            "",
            "  FIRST STEPS (Take Immediately):",
        ]
        for step in self.first_steps:
            lines.append(f"    → {step}")
        lines.append("")
        lines.append("  PHASES:")
        for phase in self.phases:
            lines.append(f"  ┌─ Phase {phase.get('phase', '?')}: {phase.get('name', '')}")
            lines.append(f"  │  Months {phase.get('start_month', 0)}–{phase.get('end_month', 0)}")
            for action in phase.get("actions", []):
                lines.append(f"  │    • {action}")
            lines.append(f"  └─ Expected Score: {phase.get('expected_score', 0)}+")
            lines.append("")
        return "\n".join(lines)


@dataclass
class BusinessCreditRoadmap:
    """Roadmap to build business credit independent of personal credit."""
    business_name: str
    ein: str
    current_paydex: Optional[int]
    target_paydex: int
    tiers: List[Dict[str, Any]]
    timeline_months: int
    vendor_recommendations: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 68 + "╗",
            "║  BUSINESS CREDIT BUILDING ROADMAP" + " " * 34 + "║",
            "╚" + "═" * 68 + "╝",
            "",
            f"  Business: {self.business_name}",
            f"  EIN:      {self.ein}",
            f"  Current Paydex: {self.current_paydex or 'None'}",
            f"  Target Paydex:  {self.target_paydex}",
            f"  Timeline:       {self.timeline_months} months",
            "",
        ]
        for tier in self.tiers:
            lines.append(f"  ▶ {tier.get('name', '')}")
            lines.append(f"    Accounts: {tier.get('accounts_needed', 0)} trade lines")
            for vendor in tier.get("vendors", []):
                lines.append(f"      • {vendor}")
            lines.append("")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class CreditMastery:
    """
    The ultimate credit intelligence system.
    Replaces a credit consultant, credit repair specialist, and financial advisor
    for all credit-related matters.

    Example:
        cm = CreditMastery()
        profile = cm.analyze_credit_profile({
            "fico_score": 620,
            "utilization": 0.65,
            "derogatory_marks": ["Collection - Medical $450"]
        })
        plan = cm.build_score_improvement_plan(profile)
    """

    def __init__(self):
        self.laws = CREDIT_LAWS
        self.state_sol = STATE_SOL

    # ─────────────────────────────────────────────────────────────────────────
    # CREDIT PROFILE ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def analyze_credit_profile(self, profile: dict) -> CreditProfile:
        """
        Analyze a raw credit profile dict and return a structured CreditProfile.

        Args:
            profile: dict with keys like fico_score, vantage_score, utilization,
                     payment_history_pct, length_of_history_months, etc.

        Returns:
            CreditProfile dataclass
        """
        fico = profile.get("fico_score", 0)
        vantage = profile.get("vantage_score", profile.get("vantage", fico))
        payment_history = profile.get("payment_history_pct", 1.0 if not profile.get("derogatory_marks") else 0.85)
        utilization = profile.get("amounts_owed_utilization", profile.get("utilization", 0.3))
        history_months = profile.get("length_of_history_months", profile.get("history_months", 24))
        credit_mix = profile.get("credit_mix", ["credit_card"])
        inquiries = profile.get("new_credit_inquiries", profile.get("inquiries", 0))
        derogatory = profile.get("derogatory_marks", [])
        positive = profile.get("positive_accounts", [])

        return CreditProfile(
            fico_score=fico,
            vantage_score=vantage,
            payment_history_pct=payment_history,
            amounts_owed_utilization=utilization,
            length_of_history_months=history_months,
            credit_mix=credit_mix,
            new_credit_inquiries=inquiries,
            derogatory_marks=derogatory,
            positive_accounts=positive,
            oldest_account_months=profile.get("oldest_account_months", history_months),
            total_accounts=profile.get("total_accounts", len(positive) + len(derogatory)),
            open_accounts=profile.get("open_accounts", len(positive)),
            revolving_utilization=utilization,
            installment_utilization=profile.get("installment_utilization", 0.0),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SCORE IMPROVEMENT PLAN
    # ─────────────────────────────────────────────────────────────────────────

    def build_score_improvement_plan(self, profile: CreditProfile) -> List[CreditAction]:
        """
        Build a prioritized action plan to maximize FICO score improvement.

        Strategy order: utilization (fastest wins) → payment history →
        derogatory removal → credit mix → inquiries → history length.

        Args:
            profile: CreditProfile from analyze_credit_profile()

        Returns:
            List[CreditAction] sorted by priority (1 = do first)
        """
        actions: List[CreditAction] = []
        priority = 1

        # ── Utilization optimization (30% weight, fastest impact) ──────────
        if profile.amounts_owed_utilization > 0.30:
            target_util = 0.09  # optimal: under 9% for max points
            actions.append(CreditAction(
                action="Reduce credit card utilization to under 9%",
                priority=priority,
                expected_score_increase=self._util_score_impact(profile.amounts_owed_utilization, target_util),
                timeline_days=30,
                difficulty="easy" if profile.amounts_owed_utilization < 0.60 else "medium",
                instructions=(
                    "PAY DOWN BALANCES BEFORE STATEMENT CLOSE DATE — this is critical. "
                    f"Current utilization: {profile.amounts_owed_utilization*100:.0f}%. "
                    "Target: under 9% on each card and overall. "
                    "Action steps: (1) Call each issuer and ask for your statement close date. "
                    "(2) Pay balance down to <9% of limit 3 days before close. "
                    "(3) Make a small purchase after statement cuts, then pay in full. "
                    "This trick alone can add 50–100 points if you're currently at 50%+ utilization. "
                    "RAPID RESCORE: Ask your mortgage broker to do a rapid rescore ($50–200) "
                    "after paying down — results in 3–5 business days instead of 30."
                ),
                cost=0.0,
                legal_authority="",
            ))
            priority += 1

        # ── Request credit limit increases ─────────────────────────────────
        if profile.amounts_owed_utilization > 0.20 and profile.fico_score >= 640:
            actions.append(CreditAction(
                action="Request credit limit increases on all existing cards",
                priority=priority,
                expected_score_increase=15,
                timeline_days=14,
                difficulty="easy",
                instructions=(
                    "Call each credit card issuer (number on back of card) and request a credit limit increase. "
                    "Best timing: 6+ months after account opening, after a positive payment history period, "
                    "and when your income has increased. "
                    "Mention your income accurately. Ask for 2–3x your current limit. "
                    "Key phrase: 'I'd like to request a credit line increase. Can this be done with a soft pull only?' "
                    "Hard pull limit increase strategy: Only accept hard pull if existing cards already showing "
                    "<30% utilization — the new limit will immediately reduce your utilization ratio. "
                    "Best cards for CLI: Discover, Capital One, American Express (often soft pull only)."
                ),
                cost=0.0,
            ))
            priority += 1

        # ── Authorized user strategy ────────────────────────────────────────
        if profile.fico_score < 720 and profile.length_of_history_months < 48:
            actions.append(CreditAction(
                action="Become an authorized user on a family member's seasoned card",
                priority=priority,
                expected_score_increase=30,
                timeline_days=45,
                difficulty="easy",
                instructions=(
                    "Find a family member or trusted friend with: (1) a card 5+ years old, "
                    "(2) utilization under 10%, (3) perfect payment history. "
                    "Ask them to add you as an authorized user. You do NOT need to receive the card. "
                    "The entire account history will appear on your credit report, potentially adding "
                    "decades to your average account age. "
                    "Alternative — paid AU services: CreditKarma AU board, Tradeline Supply Co. (cost: $100–$300). "
                    "This is 100% legal under FCRA. FICO 8 and FICO 9 both count AU accounts."
                ),
                cost=0.0,
            ))
            priority += 1

        # ── Payment history — fix any late payments ─────────────────────────
        if profile.payment_history_pct < 1.0:
            actions.append(CreditAction(
                action="Send goodwill letters for any late payments",
                priority=priority,
                expected_score_increase=40,
                timeline_days=60,
                difficulty="medium",
                instructions=(
                    "Write a goodwill letter to each original creditor (NOT the credit bureaus) "
                    "for any late payments. Include: (1) account number, (2) date of late payment, "
                    "(3) reason for the late payment (job loss, medical, etc.), "
                    "(4) your current on-time payment record, (5) polite request to remove as goodwill. "
                    "Mail to the credit card's customer service address AND to the CEO's office. "
                    "Success rate: 20–40%. Keep records and follow up in 30 days. "
                    "Lenders most likely to grant goodwill removal: Capital One, Discover, American Express. "
                    "Most difficult: Chase, Citi, Bank of America."
                ),
                cost=0.0,
            ))
            priority += 1

        # ── Derogatory marks — dispute and removal ─────────────────────────
        if profile.derogatory_marks:
            actions.append(CreditAction(
                action=f"Dispute/remove {len(profile.derogatory_marks)} derogatory mark(s)",
                priority=priority,
                expected_score_increase=len(profile.derogatory_marks) * 25,
                timeline_days=90,
                difficulty="medium",
                instructions=(
                    "For each derogatory item: (1) Pull all 3 bureau reports (free at AnnualCreditReport.com). "
                    "(2) Check for ANY inaccuracy — wrong balance, wrong date, wrong account number, "
                    "wrong status. ANY error = grounds for dispute under FCRA Section 611. "
                    "(3) Send dispute letters via certified mail to Equifax, Experian, and TransUnion. "
                    "(4) Bureau must investigate in 30 days (45 if you submit additional info). "
                    "(5) If collector can't verify — MUST DELETE. "
                    "Strategy: Dispute the SAME account multiple times using different legal bases "
                    "(factual dispute, procedural dispute, FCRA 623 furnisher demand)."
                ),
                cost=0.0,
                legal_authority="FCRA Section 611",
            ))
            priority += 1

        # ── Credit mix improvement ──────────────────────────────────────────
        mix_types = set(profile.credit_mix)
        missing_mix = []
        if "installment" not in mix_types and "auto" not in mix_types and "mortgage" not in mix_types:
            missing_mix.append("installment loan")
        if "revolving" not in mix_types and "credit_card" not in mix_types:
            missing_mix.append("revolving credit card")

        if missing_mix and profile.fico_score >= 600:
            actions.append(CreditAction(
                action=f"Add missing credit types to mix: {', '.join(missing_mix)}",
                priority=priority,
                expected_score_increase=20,
                timeline_days=90,
                difficulty="easy",
                instructions=(
                    "Credit mix (10% of FICO) rewards having both revolving and installment credit. "
                    "If missing installment: Open a Credit Builder Loan at a credit union or Self Inc. ($25/mo). "
                    "If missing revolving: Apply for a secured credit card (Capital One Secured, Discover Secured). "
                    "Do NOT open multiple accounts at once — space 6+ months apart."
                ),
                cost=25.0,
            ))
            priority += 1

        # ── New inquiries ── minimize ───────────────────────────────────────
        if profile.new_credit_inquiries > 2:
            actions.append(CreditAction(
                action="Stop all new credit applications for 6 months",
                priority=priority,
                expected_score_increase=10,
                timeline_days=180,
                difficulty="easy",
                instructions=(
                    "Each hard inquiry costs approximately 5–10 points for 12 months. "
                    "After 2 years, inquiries fall off completely. "
                    "Rate shopping exception: Multiple inquiries for the same loan type "
                    "(mortgage, auto) within 14–45 days count as ONE inquiry. "
                    "You can dispute unauthorized hard inquiries under FCRA Section 604 "
                    "(permissible purpose requirement). "
                    "Request the creditor's permissible purpose in writing — if they can't prove it, "
                    "it must be removed."
                ),
                cost=0.0,
                legal_authority="FCRA Section 604",
            ))
            priority += 1

        # ── Sort by priority ────────────────────────────────────────────────
        actions.sort(key=lambda a: a.priority)
        return actions

    def _util_score_impact(self, current: float, target: float) -> int:
        """Estimate score impact from utilization reduction."""
        if current > 0.90 and target < 0.30:
            return 100
        elif current > 0.50 and target < 0.10:
            return 80
        elif current > 0.30 and target < 0.10:
            return 50
        elif current > 0.10 and target < 0.09:
            return 20
        return 10

    # ─────────────────────────────────────────────────────────────────────────
    # DISPUTE LETTER GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def generate_dispute_letter(self, account: dict, dispute_type: str) -> DisputeLetter:
        """
        Generate a legally precise credit dispute letter.

        Args:
            account: dict with account_name, account_number, creditor,
                     amount, open_date, issue_description
            dispute_type: one of 'fcra_611', 'method_of_verification',
                         'debt_validation', 'cfpb_complaint', 'factual', 'procedural'

        Returns:
            DisputeLetter with formatted letter body
        """
        account_name = account.get("account_name", "Unknown Creditor")
        account_number = account.get("account_number", "XXXX")
        issue = account.get("issue_description", "inaccurate information")
        amount = account.get("amount", "unknown amount")
        bureau = account.get("bureau", "Equifax, Experian, and TransUnion")

        today = datetime.now().strftime("%B %d, %Y")

        if dispute_type == "fcra_611":
            letter = self._fcra_611_dispute(account_name, account_number, issue, today)
            legal_basis = "FCRA Section 611 — Right to Dispute Inaccurate Information"
            recipient = bureau
            enclosures = [
                "Copy of government-issued photo ID",
                "Proof of current address (utility bill or bank statement)",
                "Copy of credit report with disputed item highlighted",
            ]

        elif dispute_type == "method_of_verification":
            letter = self._method_of_verification_letter(account_name, account_number, today)
            legal_basis = "FCRA Section 611(a)(6)(B)(iii) — Method of Verification"
            recipient = bureau
            enclosures = [
                "Copy of government-issued photo ID",
                "Copy of original dispute letter",
                "Copy of bureau's investigation results",
            ]

        elif dispute_type == "debt_validation":
            letter = self._debt_validation_letter(account_name, amount, today)
            legal_basis = "FDCPA Section 1692g — Right to Debt Validation"
            recipient = account.get("collector_name", "Debt Collector")
            enclosures = []

        elif dispute_type == "cfpb_complaint":
            letter = self._cfpb_complaint_template(account_name, account_number, issue, today)
            legal_basis = "CFPB Complaint — Consumer Financial Protection Bureau"
            recipient = "Consumer Financial Protection Bureau"
            enclosures = [
                "Copy of all dispute letters sent",
                "Copies of certified mail receipts",
                "Credit report excerpt showing disputed item",
                "Any response letters received",
            ]

        elif dispute_type == "factual":
            letter = self._factual_dispute_letter(account_name, account_number, issue, today)
            legal_basis = "FCRA Section 611 — Factual Dispute"
            recipient = bureau
            enclosures = [
                "Evidence of inaccuracy (statements, receipts, correspondence)",
                "Copy of government-issued photo ID",
                "Proof of address",
            ]

        else:  # procedural
            letter = self._procedural_dispute_letter(account_name, account_number, today)
            legal_basis = "FCRA Section 611 — Procedural Dispute"
            recipient = bureau
            enclosures = [
                "Copy of government-issued photo ID",
                "Proof of address",
            ]

        return DisputeLetter(
            dispute_type=dispute_type.replace("_", " ").title(),
            recipient=recipient,
            account_name=account_name,
            account_number=account_number,
            legal_basis=legal_basis,
            letter_body=letter,
            enclosures=enclosures,
            certified_mail_required=True,
        )

    def _fcra_611_dispute(self, account: str, acct_num: str, issue: str, today: str) -> str:
        return f"""To Whom It May Concern:

I am writing pursuant to my rights under the Fair Credit Reporting Act (FCRA),
15 U.S.C. § 1681 et seq., specifically Section 611 (15 U.S.C. § 1681i).

I dispute the following item appearing on my credit report as INACCURATE:

    Account Name:   {account}
    Account Number: {acct_num}
    Issue:          {issue}

Under FCRA § 611(a)(1)(A), you are required to conduct a reasonable reinvestigation
of this disputed information within 30 days of receipt of this notice
(or 45 days if I submit additional information during that period).

If the information cannot be verified as accurate, you are required to PROMPTLY
DELETE the item from my credit file under FCRA § 611(a)(5)(A).

I also demand that you provide me with written notification of the results of
your investigation, including the name, address, and phone number of any
furnisher contacted, pursuant to FCRA § 611(a)(6).

Please note that any continued reporting of inaccurate information after this
notice may constitute a willful violation of the FCRA, entitling me to statutory
damages of $100–$1,000 per violation under 15 U.S.C. § 1681n.

I have enclosed the required identification documents. Please process this
dispute immediately.

Sincerely,

[YOUR FULL NAME]
[YOUR ADDRESS]
[YOUR CITY, STATE, ZIP]
[YOUR DATE OF BIRTH]
[LAST 4 OF SSN]"""

    def _method_of_verification_letter(self, account: str, acct_num: str, today: str) -> str:
        return f"""To Whom It May Concern:

On [DATE OF ORIGINAL DISPUTE], I submitted a dispute regarding the following account:

    Account Name:   {account}
    Account Number: {acct_num}

Your investigation concluded that the information was "verified." I am now
exercising my rights under FCRA § 611(a)(6)(B)(iii) to demand the following:

1. The name, address, and telephone number of each person contacted during
   your reinvestigation;
2. The specific documents or records reviewed during the investigation;
3. The method by which you verified the accuracy of this information.

Please provide this information in writing within 15 days of receipt of this letter.

If you are unable to provide verification methodology, you must DELETE the
disputed item from my credit file, as your verification is insufficient to
satisfy the FCRA's "reasonable reinvestigation" standard established in
Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997).

I reserve all rights under the FCRA, including the right to pursue civil
remedies for any willful or negligent noncompliance.

Sincerely,

[YOUR FULL NAME]
[YOUR ADDRESS]
[YOUR CITY, STATE, ZIP]"""

    def _debt_validation_letter(self, account: str, amount: str, today: str) -> str:
        return f"""NOTICE OF DEBT VALIDATION REQUEST
Pursuant to: Fair Debt Collection Practices Act, 15 U.S.C. § 1692g

To the Debt Collector:

This is a written notice that I dispute the validity of the alleged debt
identified as: {account} in the amount of approximately ${amount}.

Pursuant to FDCPA § 1692g(b), I demand VALIDATION of this debt, including:

1. Proof that your company has the legal right to collect this debt;
2. The name and address of the original creditor;
3. Copy of the original signed contract or agreement;
4. Complete account history showing how the claimed amount was calculated;
5. Proof that this debt is within the statute of limitations for collection
   in my state;
6. Copy of your license to collect debts in my state.

Under FDCPA § 1692g(b), you must CEASE ALL COLLECTION ACTIVITY until
you provide the requested validation. This includes ceasing any credit
bureau reporting of this alleged debt.

If you cannot validate this debt, you must cease collection and notify all
credit bureaus to delete any references to this alleged account.

WARNING: Any continued collection activity without validation, or any
report to a credit bureau without first validating this debt, may constitute
a violation of the FDCPA entitling me to statutory damages of up to $1,000
per violation, plus attorney fees and costs.

This notice is sent via Certified Mail as proof of delivery.

[YOUR FULL NAME]
[YOUR ADDRESS]
[YOUR CITY, STATE, ZIP]"""

    def _cfpb_complaint_template(self, account: str, acct_num: str, issue: str, today: str) -> str:
        return f"""CONSUMER FINANCIAL PROTECTION BUREAU COMPLAINT

Submitted: {today}
Re: {account} | Account: {acct_num}

Dear CFPB:

I am filing this complaint against [COMPANY NAME] for violations of federal
consumer protection laws regarding the account referenced above.

FACTS:
{issue}

VIOLATIONS:
- Continued reporting of unverified information in violation of FCRA § 611
- Failure to conduct a reasonable reinvestigation as required by FCRA § 611(a)
- [Add specific violations]

RELIEF REQUESTED:
1. Order the company to delete the inaccurate/unverified information
2. Provide written confirmation of deletion to all three credit bureaus
3. Cease any further violations of the FCRA

TIMELINE OF EVENTS:
[Date]: Discovered inaccurate information on credit report
[Date]: Sent initial dispute letter via certified mail
[Date]: Received response [or no response]

I have attached supporting documentation including my dispute letters,
certified mail receipts, and the company's response.

Thank you for your assistance in this matter.

Sincerely,
[YOUR FULL NAME]"""

    def _factual_dispute_letter(self, account: str, acct_num: str, issue: str, today: str) -> str:
        return f"""To Whom It May Concern:

FACTUAL CREDIT DISPUTE — FCRA § 611

I am disputing the following item based on FACTUAL INACCURACY:

    Account: {account} | #{acct_num}
    Inaccuracy: {issue}

EVIDENCE OF INACCURACY:
I have enclosed documentation proving that the reported information is
factually incorrect. Specifically: [DESCRIBE YOUR EVIDENCE]

Under FCRA § 611, you are required to delete information that cannot be
verified as accurate. Given the enclosed evidence, this item cannot be
accurately reported as currently shown.

I demand that you:
1. Investigate this dispute using the enclosed evidence
2. Correct or delete the inaccurate information within 30 days
3. Notify me in writing of the results of your investigation
4. Forward my dispute and evidence to the furnisher of this information

Sincerely,
[YOUR FULL NAME]
[YOUR ADDRESS]
[YOUR CITY, STATE, ZIP]"""

    def _procedural_dispute_letter(self, account: str, acct_num: str, today: str) -> str:
        return f"""To Whom It May Concern:

PROCEDURAL CREDIT DISPUTE — FCRA § 611

I am disputing the following item on procedural grounds:

    Account: {account} | #{acct_num}

The FCRA requires that consumer reporting agencies maintain "reasonable
procedures to assure maximum possible accuracy" of consumer information
(FCRA § 607(b)). The information currently reported does not meet this
standard because:

1. The reporting period may be incorrect under FCRA § 605's obsolescence rules
2. The information may not have been properly verified when originally added
3. [Add specific procedural defect]

I demand a full reinvestigation under FCRA § 611. If this information
cannot be verified through proper procedures, it must be deleted.

Please provide the method of verification upon completion of your
investigation as required by FCRA § 611(a)(6)(B)(iii).

Sincerely,
[YOUR FULL NAME]"""

    # ─────────────────────────────────────────────────────────────────────────
    # CREDIT REPAIR STRATEGY
    # ─────────────────────────────────────────────────────────────────────────

    def credit_repair_strategy(self, derogatory_items: List[dict]) -> CreditRepairPlan:
        """
        Create a comprehensive plan to repair derogatory credit items.

        Args:
            derogatory_items: List of dicts with keys: type, creditor, amount,
                              date_of_first_delinquency, state, balance

        Returns:
            CreditRepairPlan with prioritized strategies
        """
        items_with_strategy = []
        total_score_improvement = 0
        priority_actions = []

        # Prioritize by removal likelihood and score impact
        collection_items = [i for i in derogatory_items if i.get("type", "").lower() == "collection"]
        late_payments = [i for i in derogatory_items if i.get("type", "").lower() == "late_payment"]
        chargeoffs = [i for i in derogatory_items if i.get("type", "").lower() == "chargeoff"]
        bankruptcies = [i for i in derogatory_items if i.get("type", "").lower() == "bankruptcy"]

        # Strategy: Collections < $200 → dispute, never pay (SOL likely expired)
        for item in collection_items:
            amount = item.get("amount", 999)
            state = item.get("state", "CA")
            sol = self.state_sol.get(state, {}).get("years", 6)
            dfd = item.get("date_of_first_delinquency", "")

            strategy = self._collection_strategy(item, sol)
            items_with_strategy.append({
                "name": item.get("creditor", "Unknown Collector"),
                "type": "Collection",
                "amount": amount,
                "strategy": strategy["method"],
                "details": strategy["details"],
            })
            total_score_improvement += 25
            priority_actions.append(strategy["action"])

        for item in late_payments:
            items_with_strategy.append({
                "name": item.get("creditor", "Unknown Creditor"),
                "type": "Late Payment",
                "strategy": "Goodwill Letter to Original Creditor",
                "details": "Success rate 20-40%. Best for: Capital One, Discover, Amex",
            })
            total_score_improvement += 15
            priority_actions.append(f"Send goodwill letter to {item.get('creditor', 'creditor')}")

        for item in chargeoffs:
            items_with_strategy.append({
                "name": item.get("creditor", "Unknown"),
                "type": "Charge-off",
                "strategy": "Dispute for Inaccuracies → Pay-for-Delete if Accurate",
                "details": "Check all reported details for ANY error first",
            })
            total_score_improvement += 30
            priority_actions.append(f"Dispute charge-off with {item.get('creditor', 'creditor')} for inaccuracies")

        for item in bankruptcies:
            items_with_strategy.append({
                "name": "Bankruptcy",
                "type": "Public Record",
                "strategy": "Verify accurate reporting; dispute any court record inaccuracies",
                "details": "Ch.7 stays 10 years; Ch.13 stays 7 years from filing date",
            })
            priority_actions.append("Verify bankruptcy is correctly reported (chapter, dates, discharged accounts)")

        # Add standard priority actions
        if not priority_actions:
            priority_actions = ["Pull all 3 credit reports from AnnualCreditReport.com"]

        priority_actions.insert(0, "Pull all 3 bureau reports and document every derogatory item")
        priority_actions.append("Set up credit monitoring (Credit Karma, Experian free tier)")
        priority_actions.append("Document all disputes with certified mail tracking numbers")

        return CreditRepairPlan(
            total_derogatory_items=len(derogatory_items),
            items=items_with_strategy,
            estimated_score_improvement=min(total_score_improvement, 200),
            timeline_months=6 if len(derogatory_items) <= 3 else 12,
            total_cost_estimate=0.0,  # DIY approach
            priority_actions=priority_actions,
        )

    def _collection_strategy(self, item: dict, sol_years: int) -> dict:
        """Determine best strategy for a collection account."""
        amount = item.get("amount", 999)

        if amount < 100:
            return {
                "method": "Dispute — Too Small to Verify",
                "details": "Many collectors cannot verify small debts. Dispute inaccuracies.",
                "action": f"Dispute {item.get('creditor', 'collection')} — small balance, likely unverifiable",
            }
        elif amount < 500:
            return {
                "method": "Dispute First; Pay-for-Delete Fallback",
                "details": "Dispute any inaccuracy. If verified, offer 25-40 cents on dollar for deletion.",
                "action": f"Dispute {item.get('creditor', 'collection')} for inaccuracies before any payment",
            }
        else:
            return {
                "method": "Pay-for-Delete Negotiation",
                "details": (
                    "Script: 'I'm prepared to resolve this account today. I can offer a settlement of "
                    f"[30-50% of ${amount}] in exchange for complete deletion from all credit bureaus. "
                    "I will need this agreement in writing before any payment is made.' "
                    "Get the agreement in writing — email or letter on their letterhead. "
                    "Pay with money order for proof. Follow up to verify deletion within 30 days."
                ),
                "action": f"Negotiate pay-for-delete with {item.get('creditor', 'collector')} for ${amount:.0f}",
            }

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD CREDIT FROM ZERO
    # ─────────────────────────────────────────────────────────────────────────

    def build_credit_from_zero(self, facts: dict) -> CreditBuildingRoadmap:
        """
        Complete roadmap for building credit from scratch (0 → 700+ in 12–24 months).

        Args:
            facts: dict with age, income, has_checking_account, has_savings_account,
                   existing_debt, target_score, timeline_months

        Returns:
            CreditBuildingRoadmap with phased strategy
        """
        target = facts.get("target_score", 720)
        has_bank = facts.get("has_checking_account", True)

        phases = [
            {
                "phase": 1,
                "name": "Foundation (Months 1–3)",
                "start_month": 1,
                "end_month": 3,
                "actions": [
                    "Open a checking and savings account if not already done (needed for applications)",
                    "Apply for a secured credit card: Capital One Secured ($49/$200) or Discover it Secured",
                    "Apply for a Credit Builder Loan: Self Inc. ($25/mo) or local credit union",
                    "Become an authorized user on a family member's seasoned card (5+ years, <10% util)",
                    "Set up autopay on all accounts (never miss a payment — 35% of score)",
                    "Keep secured card utilization under 9% — pay BEFORE statement close date",
                ],
                "expected_score": 620,
            },
            {
                "phase": 2,
                "name": "Acceleration (Months 4–9)",
                "start_month": 4,
                "end_month": 9,
                "actions": [
                    "After 6 months of secured card: apply for starter unsecured card (Capital One Quicksilver)",
                    "Request secured card graduation to unsecured (Discover does this automatically)",
                    "Apply for a store card with easy approval (Amazon Store Card if Prime member)",
                    "Continue credit builder loan payments",
                    "Check credit report monthly for errors — dispute immediately",
                    "Keep total utilization under 6% for maximum score impact",
                ],
                "expected_score": 670,
            },
            {
                "phase": 3,
                "name": "Growth (Months 10–18)",
                "start_month": 10,
                "end_month": 18,
                "actions": [
                    "Apply for a rewards credit card (Chase Freedom, Citi Double Cash)",
                    "Request credit limit increases on all existing cards",
                    "Consider adding an auto loan if needed (adds installment credit)",
                    "Open a second credit builder account at a credit union",
                    "Optimize utilization: keep each card under 9%, total under 6%",
                    "Graduate secured cards to unsecured versions",
                ],
                "expected_score": 710,
            },
            {
                "phase": 4,
                "name": "Excellence (Months 19–24)",
                "start_month": 19,
                "end_month": 24,
                "actions": [
                    "Apply for premium rewards card (Chase Sapphire Preferred, Amex Gold)",
                    "Increase credit limits aggressively via soft-pull requests",
                    "Close credit builder loan after completion (it's been reporting positively)",
                    "Maintain 2–3 active credit cards with minimal balances",
                    "Do NOT close old accounts — age is crucial",
                    "Freeze credit between applications to protect from unauthorized inquiries",
                ],
                "expected_score": 740,
            },
        ]

        first_steps = [
            "Download your free credit reports at AnnualCreditReport.com",
            "Open a bank account if you don't have one (credit unions preferred)",
            "Apply for Capital One Secured Mastercard ($49 deposit, $200 limit)",
            "Apply for Self Inc. Credit Builder Loan ($25/month)",
            "Set up autopay on all accounts immediately",
            "Download Credit Karma for free credit monitoring",
        ]

        return CreditBuildingRoadmap(
            starting_score=None,
            target_score=target,
            timeline_months=24,
            phases=phases,
            estimated_monthly_cost=50.0,
            first_steps=first_steps,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BUSINESS CREDIT BUILDER
    # ─────────────────────────────────────────────────────────────────────────

    def business_credit_builder(self, business: dict) -> BusinessCreditRoadmap:
        """
        Build business credit completely separate from personal credit.
        Achieve EIN-only credit: Tier 1 → 2 → 3 → bank financing.

        Args:
            business: dict with business_name, ein, years_in_business,
                      revenue, entity_type, has_business_bank_account

        Returns:
            BusinessCreditRoadmap with complete vendor/lender progression
        """
        name = business.get("business_name", "Your Business")
        ein = business.get("ein", "XX-XXXXXXX")

        tiers = [
            {
                "name": "FOUNDATION (Pre-Tier 1) — Business Setup",
                "accounts_needed": 0,
                "vendors": [
                    "Incorporate as LLC or Corp (NOT sole prop — EIN-only credit requires entity)",
                    "Get EIN from IRS (free at irs.gov) — do NOT use SSN",
                    "Open dedicated business checking account (Chase, Bank of America, Relay, Mercury)",
                    "Get a DUNS number from Dun & Bradstreet (free at dnb.com, takes 1-2 weeks)",
                    "Register with Experian Business and Equifax Business",
                    "Get a business phone number listed in 411 (Google Voice works)",
                    "Set up business address (not PO Box — use virtual office if needed)",
                    "Get a business website and email with your domain (not Gmail)",
                    "Apply for business licenses and permits in your state",
                ],
                "paydex_target": None,
            },
            {
                "name": "TIER 1 — Starter Vendor Accounts (Net-30, No Personal Guarantee)",
                "accounts_needed": 5,
                "vendors": [
                    "Uline (uline.com) — shipping/office supplies, Net-30, reports to D&B",
                    "Quill (quill.com) — office supplies, Net-30, reports to D&B/Experian",
                    "Grainger (grainger.com) — industrial/safety, Net-30, reports to D&B",
                    "HD Supply (hdsupply.com) — facilities/maintenance, Net-30",
                    "Summa Office Supplies (summaofficesupplies.com) — reports all 3 bureaus",
                    "Crown Office Supplies — EIN-only approval",
                    "Newegg Business (neweggbusiness.com) — tech, Net-30",
                    "Laughlin Associates — registered agent services, Net-30",
                ],
                "paydex_target": 75,
            },
            {
                "name": "TIER 2 — Fleet, Store & Revolving Cards",
                "accounts_needed": 8,
                "vendors": [
                    "WEX Fleet Card — fuel, EIN-only, reports to D&B",
                    "Shell Fleet Card — fuel cards, Net-30",
                    "Home Depot Business Account — revolving, reports D&B/Equifax",
                    "Lowes Business Account — revolving",
                    "Staples Business Advantage — Net-30",
                    "Office Depot/Max Business — revolving credit",
                    "Sam's Club Business Mastercard — reports Equifax Business",
                    "Costco Business Card (Citi) — business revolving",
                ],
                "paydex_target": 80,
            },
            {
                "name": "TIER 3 — Business Credit Cards & Bank Lines",
                "accounts_needed": 10,
                "vendors": [
                    "Capital One Spark Business Cash Card — reports all business bureaus",
                    "Chase Ink Business Cash Card — reports business bureaus",
                    "American Express Business Gold Card — reports to SBFE",
                    "Brex Corporate Card (no personal guarantee for qualifying businesses)",
                    "Ramp (no personal guarantee for funded startups)",
                    "Navy Federal Business Mastercard",
                    "Local credit union business line of credit ($10K–$50K)",
                    "Business term loan through SBA-approved lender",
                ],
                "paydex_target": 80,
            },
        ]

        return BusinessCreditRoadmap(
            business_name=name,
            ein=ein,
            current_paydex=business.get("current_paydex"),
            target_paydex=80,
            tiers=tiers,
            timeline_months=12,
            vendor_recommendations=["Uline", "Quill", "Grainger"],
        )
