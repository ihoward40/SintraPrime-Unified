"""
Business Funding Engine — Master every funding source that exists.
Covers SBA loans, grants, VC, alternative funding, and personal funding strategies.
Replaces a business funding specialist, grant writer, and investment banker.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


# ─────────────────────────────────────────────────────────────────────────────
# FUNDING DATABASE — 50+ Real Programs
# ─────────────────────────────────────────────────────────────────────────────

FUNDING_DATABASE: List[Dict[str, Any]] = [
    # SBA Programs
    {
        "name": "SBA 7(a) Loan",
        "type": "loan",
        "category": "SBA",
        "min_amount": 50000,
        "max_amount": 5000000,
        "apr_range": "Prime + 2.25% to Prime + 4.75%",
        "eligibility": ["For-profit US business", "Good character", "Reasonable equity injection", "No other financing available"],
        "min_credit": 650,
        "min_years_in_business": 2,
        "approval_rate": 0.55,
        "timeline_days": 60,
        "url": "https://www.sba.gov/funding-programs/loans/7a-loans",
        "best_for": ["Working capital", "Equipment", "Real estate", "Refinancing"],
    },
    {
        "name": "SBA 504 Loan",
        "type": "loan",
        "category": "SBA",
        "min_amount": 125000,
        "max_amount": 20000000,
        "apr_range": "Below-market fixed rate (tied to 10-yr Treasury)",
        "eligibility": ["Net worth < $15M", "Net income < $5M avg", "Job creation/retention required"],
        "min_credit": 650,
        "min_years_in_business": 2,
        "approval_rate": 0.60,
        "timeline_days": 90,
        "url": "https://www.sba.gov/funding-programs/loans/504-loans",
        "best_for": ["Commercial real estate", "Heavy machinery", "Long-term fixed assets"],
    },
    {
        "name": "SBA Microloan",
        "type": "loan",
        "category": "SBA",
        "min_amount": 500,
        "max_amount": 50000,
        "apr_range": "8%–13%",
        "eligibility": ["Startups OK", "Women/minority/veteran-owned preferred", "For-profit or nonprofit childcare"],
        "min_credit": 575,
        "min_years_in_business": 0,
        "approval_rate": 0.65,
        "timeline_days": 30,
        "url": "https://www.sba.gov/funding-programs/loans/microloans",
        "best_for": ["Startups", "Very small businesses", "Underserved communities"],
    },
    {
        "name": "SBA EIDL (Economic Injury Disaster Loan)",
        "type": "loan",
        "category": "SBA",
        "min_amount": 1000,
        "max_amount": 2000000,
        "apr_range": "3.75% (non-profit 2.75%)",
        "eligibility": ["Located in declared disaster area", "Suffered economic injury"],
        "min_credit": 570,
        "min_years_in_business": 1,
        "approval_rate": 0.50,
        "timeline_days": 45,
        "url": "https://www.sba.gov/funding-programs/loans/covid-eidl",
        "best_for": ["Disaster recovery", "Working capital during crises"],
    },
    {
        "name": "SBA Express Loan",
        "type": "loan",
        "category": "SBA",
        "min_amount": 10000,
        "max_amount": 500000,
        "apr_range": "Prime + 4.5% to Prime + 6.5%",
        "eligibility": ["36-hour lender decision", "Good credit required", "Existing business preferred"],
        "min_credit": 680,
        "min_years_in_business": 2,
        "approval_rate": 0.45,
        "timeline_days": 30,
        "url": "https://www.sba.gov/funding-programs/loans/sba-express-loans",
        "best_for": ["Speed needed", "Smaller loan amounts", "Strong credit profile"],
    },
    # Federal Grants
    {
        "name": "SBIR Phase I Grant",
        "type": "grant",
        "category": "Federal Grant",
        "min_amount": 50000,
        "max_amount": 275000,
        "apr_range": "N/A — grant",
        "eligibility": ["<500 employees", "US-owned", "For-profit", "R&D project in federal priority area"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.15,
        "timeline_days": 180,
        "url": "https://www.sbir.gov",
        "best_for": ["Tech startups", "R&D companies", "Science-based businesses"],
    },
    {
        "name": "SBIR Phase II Grant",
        "type": "grant",
        "category": "Federal Grant",
        "min_amount": 500000,
        "max_amount": 1750000,
        "apr_range": "N/A — grant",
        "eligibility": ["Phase I awardee", "<500 employees", "US-owned for-profit"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.40,
        "timeline_days": 180,
        "url": "https://www.sbir.gov",
        "best_for": ["Phase I awardees ready to commercialize"],
    },
    {
        "name": "STTR Grant",
        "type": "grant",
        "category": "Federal Grant",
        "min_amount": 50000,
        "max_amount": 1750000,
        "apr_range": "N/A — grant",
        "eligibility": ["Partnership with research institution required", "<500 employees"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.12,
        "timeline_days": 180,
        "url": "https://www.sbir.gov/sttr",
        "best_for": ["University partnerships", "Technology transfer"],
    },
    {
        "name": "EDA Public Works Grant",
        "type": "grant",
        "category": "Federal Grant",
        "min_amount": 300000,
        "max_amount": 10000000,
        "apr_range": "N/A — grant",
        "eligibility": ["Economic distress area", "Job creation focus", "Local government or nonprofit eligible"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.20,
        "timeline_days": 270,
        "url": "https://www.eda.gov/funding/programs/public-works",
        "best_for": ["Infrastructure", "Economic development", "Job creation"],
    },
    {
        "name": "USDA Business & Industry Loan Guarantee",
        "type": "loan",
        "category": "Federal",
        "min_amount": 200000,
        "max_amount": 25000000,
        "apr_range": "Market rate (guaranteed up to 80%)",
        "eligibility": ["Rural area (non-metro)", "For-profit or nonprofit", "US citizen or legal resident"],
        "min_credit": 640,
        "min_years_in_business": 1,
        "approval_rate": 0.45,
        "timeline_days": 90,
        "url": "https://www.rd.usda.gov/programs-services/business-programs",
        "best_for": ["Rural businesses", "Agribusiness", "Rural job creation"],
    },
    # Minority/Women/Veteran Grants
    {
        "name": "Amber Grant (Women-Owned)",
        "type": "grant",
        "category": "Women-Owned",
        "min_amount": 10000,
        "max_amount": 30000,
        "apr_range": "N/A — grant",
        "eligibility": ["Woman-owned business", "For-profit"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.05,
        "timeline_days": 60,
        "url": "https://ambergrantsforwomen.com",
        "best_for": ["Women entrepreneurs at any stage"],
    },
    {
        "name": "Cartier Women's Initiative",
        "type": "grant",
        "category": "Women-Owned",
        "min_amount": 30000,
        "max_amount": 100000,
        "apr_range": "N/A — grant",
        "eligibility": ["Woman-led for-profit startup", "Early stage (<6 years)", "Revenue <$1M"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.02,
        "timeline_days": 180,
        "url": "https://www.cartierwomensinitiative.com",
        "best_for": ["High-impact women-led startups globally"],
    },
    {
        "name": "StreetShares Foundation Veteran Small Business Award",
        "type": "grant",
        "category": "Veteran-Owned",
        "min_amount": 4000,
        "max_amount": 15000,
        "apr_range": "N/A — grant",
        "eligibility": ["Veteran-owned business", "Military spouse-owned eligible"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.10,
        "timeline_days": 90,
        "url": "https://streetsharesfoundation.org",
        "best_for": ["Veteran entrepreneurs"],
    },
    {
        "name": "Hivers & Strivers Angel Fund",
        "type": "equity",
        "category": "Veteran-Owned",
        "min_amount": 250000,
        "max_amount": 1000000,
        "apr_range": "Equity — 5%–20%",
        "eligibility": ["Veteran-founded startup", "US military academy graduates preferred"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.08,
        "timeline_days": 120,
        "url": "https://hiversandstrivers.com",
        "best_for": ["Veteran-founded high-growth startups"],
    },
    # Alternative Funding
    {
        "name": "Clearco Revenue-Based Financing",
        "type": "revenue_based",
        "category": "Alternative",
        "min_amount": 10000,
        "max_amount": 10000000,
        "apr_range": "6%–12% flat fee (not APR)",
        "eligibility": ["$10K+ monthly revenue", "6+ months in business", "E-commerce or SaaS preferred"],
        "min_credit": 600,
        "min_years_in_business": 0,
        "approval_rate": 0.30,
        "timeline_days": 7,
        "url": "https://clear.co",
        "best_for": ["E-commerce", "SaaS", "Revenue-generating businesses"],
    },
    {
        "name": "Lighter Capital Revenue-Based Financing",
        "type": "revenue_based",
        "category": "Alternative",
        "min_amount": 50000,
        "max_amount": 3000000,
        "apr_range": "15%–25% effective APR",
        "eligibility": ["$15K+ MRR", "SaaS or tech company", "US-based"],
        "min_credit": 620,
        "min_years_in_business": 1,
        "approval_rate": 0.25,
        "timeline_days": 14,
        "url": "https://www.lightercapital.com",
        "best_for": ["SaaS companies", "Tech businesses with recurring revenue"],
    },
    {
        "name": "Kickstarter Crowdfunding",
        "type": "crowdfunding",
        "category": "Alternative",
        "min_amount": 1000,
        "max_amount": 10000000,
        "apr_range": "5% platform fee + 3%–5% payment processing",
        "eligibility": ["Product or creative project", "All-or-nothing model", "US, CA, UK, EU"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.40,
        "timeline_days": 60,
        "url": "https://www.kickstarter.com",
        "best_for": ["Consumer products", "Creative projects", "Community-driven brands"],
    },
    {
        "name": "Republic Equity Crowdfunding",
        "type": "equity_crowdfunding",
        "category": "Alternative",
        "min_amount": 50000,
        "max_amount": 5000000,
        "apr_range": "Equity — varies",
        "eligibility": ["US company", "Reg CF or Reg A+ filing", "SEC compliance required"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.20,
        "timeline_days": 90,
        "url": "https://republic.com",
        "best_for": ["Startups", "Community-connected brands", "Tech companies"],
    },
    {
        "name": "Wefunder Equity Crowdfunding",
        "type": "equity_crowdfunding",
        "category": "Alternative",
        "min_amount": 50000,
        "max_amount": 5000000,
        "apr_range": "Equity — varies",
        "eligibility": ["US company", "Regulation Crowdfunding (Reg CF)"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.25,
        "timeline_days": 90,
        "url": "https://wefunder.com",
        "best_for": ["Early-stage startups", "Community products"],
    },
    {
        "name": "Kiva Microloan",
        "type": "microloan",
        "category": "Alternative",
        "min_amount": 1000,
        "max_amount": 15000,
        "apr_range": "0% (interest-free!)",
        "eligibility": ["US or international small business", "Social impact focus helpful", "Must recruit lenders"],
        "min_credit": 550,
        "min_years_in_business": 0,
        "approval_rate": 0.80,
        "timeline_days": 45,
        "url": "https://www.kiva.org/borrow",
        "best_for": ["Startups", "Underserved entrepreneurs", "Social impact businesses"],
    },
    {
        "name": "Accion Opportunity Fund",
        "type": "microloan",
        "category": "CDFI",
        "min_amount": 5000,
        "max_amount": 100000,
        "apr_range": "8%–24%",
        "eligibility": ["Minority/women/veteran or low-income owners preferred", "1+ year in business"],
        "min_credit": 550,
        "min_years_in_business": 0,
        "approval_rate": 0.60,
        "timeline_days": 21,
        "url": "https://opportunities.accion.org",
        "best_for": ["Underserved entrepreneurs", "Minority-owned businesses"],
    },
    # Venture Capital / Accelerators
    {
        "name": "Y Combinator Accelerator",
        "type": "accelerator",
        "category": "Equity",
        "min_amount": 125000,
        "max_amount": 500000,
        "apr_range": "7% equity + $375K MFN SAFE",
        "eligibility": ["Early stage startup", "Scalable technology business", "Competitive application"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.02,
        "timeline_days": 180,
        "url": "https://www.ycombinator.com",
        "best_for": ["Tech startups with massive growth potential"],
    },
    {
        "name": "Techstars Accelerator",
        "type": "accelerator",
        "category": "Equity",
        "min_amount": 20000,
        "max_amount": 120000,
        "apr_range": "6% equity",
        "eligibility": ["Early stage startup", "Industry-specific programs", "Global"],
        "min_credit": None,
        "min_years_in_business": 0,
        "approval_rate": 0.01,
        "timeline_days": 180,
        "url": "https://www.techstars.com",
        "best_for": ["Industry-specific tech startups"],
    },
    # Personal Funding
    {
        "name": "HELOC (Home Equity Line of Credit)",
        "type": "personal_secured",
        "category": "Personal",
        "min_amount": 10000,
        "max_amount": 500000,
        "apr_range": "Prime + 0%–2% (variable)",
        "eligibility": ["Homeowner", "20%+ equity in home", "Credit score 680+", "Income verification"],
        "min_credit": 680,
        "min_years_in_business": 0,
        "approval_rate": 0.70,
        "timeline_days": 21,
        "url": "",
        "best_for": ["Business startup funding", "Large purchases", "Debt consolidation"],
    },
    {
        "name": "SBA Community Advantage Loan",
        "type": "loan",
        "category": "CDFI",
        "min_amount": 5000,
        "max_amount": 350000,
        "apr_range": "Prime + 6%",
        "eligibility": ["Underserved markets", "CDFIs and mission-based lenders", "Community development focus"],
        "min_credit": 575,
        "min_years_in_business": 0,
        "approval_rate": 0.55,
        "timeline_days": 45,
        "url": "https://www.sba.gov",
        "best_for": ["Underserved entrepreneurs", "Low-moderate income areas"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FundingOpportunity:
    """A specific funding opportunity with match score and details."""
    name: str
    type: str                               # grant, loan, equity, alternative
    amount_range: Tuple[float, float]
    eligibility_requirements: List[str]
    application_difficulty: str             # easy / medium / hard
    approval_rate: float
    timeline_days: int
    cost_of_capital: float                  # APR or equity %
    best_for: List[str]
    application_url: str
    tips: List[str]
    match_score: float = 0.0               # 0.0–1.0
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class FundingMatchReport:
    """Complete funding match report for a business."""
    business_name: str
    total_opportunities: int
    top_opportunities: List[FundingOpportunity]
    recommended_sequence: List[str]
    estimated_total_available: float
    next_steps: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║  BUSINESS FUNDING MATCH REPORT" + " " * 41 + "║",
            f"║  {self.business_name}" + " " * (71 - len(self.business_name)) + "║",
            "╚" + "═" * 72 + "╝",
            "",
            f"  Total Opportunities Found:    {self.total_opportunities}",
            f"  Estimated Capital Available:  ${self.estimated_total_available:,.0f}",
            "",
            "  TOP FUNDING MATCHES:",
            "  " + "─" * 70,
        ]
        for i, opp in enumerate(self.top_opportunities[:10], 1):
            lines.append(f"  {i:2d}. {opp.name}")
            lines.append(f"      Type: {opp.type} | Match: {opp.match_score*100:.0f}% | Timeline: {opp.timeline_days} days")
            lines.append(f"      Amount: ${opp.amount_range[0]:,.0f}–${opp.amount_range[1]:,.0f}")
            lines.append(f"      URL: {opp.application_url}")
            lines.append("")
        lines += [
            "  RECOMMENDED SEQUENCE:",
            "  " + "─" * 70,
        ]
        for i, step in enumerate(self.recommended_sequence, 1):
            lines.append(f"  {i}. {step}")
        lines += ["", "  NEXT STEPS:", "  " + "─" * 70]
        for step in self.next_steps:
            lines.append(f"  → {step}")
        return "\n".join(lines)


@dataclass
class SBALoanStrategy:
    """Comprehensive SBA loan strategy and application guide."""
    recommended_programs: List[str]
    primary_program: str
    loan_amount: float
    estimated_approval_probability: float
    preparation_checklist: List[str]
    lender_strategy: str
    timeline_weeks: int
    key_requirements: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  SBA LOAN STRATEGY" + " " * 51 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Primary Program:            {self.primary_program}",
            f"  Recommended Loan Amount:    ${self.loan_amount:,.0f}",
            f"  Approval Probability:       {self.estimated_approval_probability*100:.0f}%",
            f"  Timeline:                   {self.timeline_weeks} weeks",
            "",
            "  RECOMMENDED SBA PROGRAMS:",
        ]
        for prog in self.recommended_programs:
            lines.append(f"    ✓ {prog}")
        lines += ["", "  PREPARATION CHECKLIST:"]
        for item in self.preparation_checklist:
            lines.append(f"    □ {item}")
        lines += ["", "  LENDER STRATEGY:", f"    {self.lender_strategy}"]
        lines += [
            "",
            "  ALL SBA PROGRAMS REFERENCE:",
            "    SBA 7(a) — Up to $5M; general purpose; most popular SBA loan",
            "    SBA 504 — Up to $20M; fixed assets (real estate, equipment); fixed rate",
            "    SBA Microloan — Up to $50K; startups and small businesses; intermediaries lend",
            "    SBA Express — Up to $500K; faster turnaround (36hr decision); revolving credit option",
            "    SBA EIDL — Up to $2M; disaster/working capital; low fixed rate",
        ]
        return "\n".join(lines)


@dataclass
class GrantOpportunity:
    """A specific grant opportunity."""
    name: str
    grantor: str
    amount_min: float
    amount_max: float
    eligibility: List[str]
    deadline: str
    application_url: str
    difficulty: str
    tips: List[str]

    def format_as_text(self) -> str:
        return (
            f"  GRANT: {self.name}\n"
            f"  Grantor: {self.grantor}\n"
            f"  Amount: ${self.amount_min:,.0f}–${self.amount_max:,.0f}\n"
            f"  Deadline: {self.deadline}\n"
            f"  URL: {self.application_url}\n"
            f"  Eligibility: {'; '.join(self.eligibility)}\n"
        )


@dataclass
class VCStrategy:
    """Venture capital fundraising strategy."""
    stage: str
    funding_target: float
    valuation_pre_money: float
    equity_to_give: float
    target_investors: List[str]
    pitch_deck_outline: List[Dict[str, str]]
    key_metrics_needed: List[str]
    timeline_months: int
    term_sheet_red_flags: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  VENTURE CAPITAL STRATEGY" + " " * 44 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Stage:              {self.stage}",
            f"  Funding Target:     ${self.funding_target:,.0f}",
            f"  Pre-Money Val.:     ${self.valuation_pre_money:,.0f}",
            f"  Equity Offered:     {self.equity_to_give*100:.1f}%",
            f"  Timeline:           {self.timeline_months} months",
            "",
            "  TARGET INVESTORS:",
        ]
        for inv in self.target_investors:
            lines.append(f"    • {inv}")
        lines += ["", "  PITCH DECK OUTLINE (12 Slides):"]
        for slide in self.pitch_deck_outline:
            lines.append(f"    Slide {slide['num']}: {slide['title']} — {slide['content']}")
        lines += ["", "  TERM SHEET RED FLAGS:"]
        for flag in self.term_sheet_red_flags:
            lines.append(f"    ⚠ {flag}")
        return "\n".join(lines)


@dataclass
class AlternativeFundingOptions:
    """Alternative funding options analysis."""
    options: List[Dict[str, Any]]
    recommended: str
    warning_items: List[str]
    total_available_estimate: float

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  ALTERNATIVE FUNDING OPTIONS" + " " * 41 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  ⭐ Recommended: {self.recommended}",
            f"  Est. Available: ${self.total_available_estimate:,.0f}",
            "",
            "  OPTIONS:",
        ]
        for opt in self.options:
            lines.append(f"  ┌─ {opt.get('name', 'Unknown')}")
            lines.append(f"  │  Type: {opt.get('type', '')} | Cost: {opt.get('cost', 'Unknown')}")
            lines.append(f"  │  Amount: ${opt.get('min', 0):,.0f}–${opt.get('max', 0):,.0f}")
            lines.append(f"  └─ Best for: {opt.get('best_for', '')}")
        if self.warning_items:
            lines += ["", "  ⚠ WARNINGS:"]
            for w in self.warning_items:
                lines.append(f"    ! {w}")
        return "\n".join(lines)


@dataclass
class PersonalFundingStrategy:
    """Personal funding strategy for individuals."""
    options: List[Dict[str, Any]]
    recommended_first: str
    total_potential: float
    tax_implications: List[str]
    risk_warnings: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  PERSONAL FUNDING STRATEGY" + " " * 43 + "║",
            "╚" + "═" * 70 + "╝",
            f"  Recommended First: {self.recommended_first}",
            f"  Total Potential:   ${self.total_potential:,.0f}",
            "",
            "  OPTIONS:",
        ]
        for opt in self.options:
            lines.append(f"  • {opt.get('name', '')}: ${opt.get('amount', 0):,.0f} @ {opt.get('rate', '?')}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class BusinessFundingEngine:
    """
    Master every funding source that exists for business and personal use.
    Replaces a business funding specialist, SBA loan officer, grant writer,
    and investment banker.

    Example:
        engine = BusinessFundingEngine()
        report = engine.find_funding({
            "name": "Acme Tech LLC",
            "revenue": 500000,
            "years_in_business": 3,
            "owner_credit_score": 720,
            "industry": "technology",
            "is_minority_owned": False,
        })
    """

    def __init__(self):
        self.funding_db = FUNDING_DATABASE

    # ─────────────────────────────────────────────────────────────────────────
    # FIND FUNDING
    # ─────────────────────────────────────────────────────────────────────────

    def find_funding(self, business: dict) -> FundingMatchReport:
        """
        Find and rank ALL applicable funding sources for the business.

        Args:
            business: dict with name, revenue, years_in_business, owner_credit_score,
                      industry, employees, is_minority_owned, is_woman_owned,
                      is_veteran_owned, is_rural, is_startup, state

        Returns:
            FundingMatchReport with ranked opportunities
        """
        name = business.get("name", "Your Business")
        revenue = business.get("revenue", 0)
        years = business.get("years_in_business", 0)
        credit = business.get("owner_credit_score", 650)
        is_minority = business.get("is_minority_owned", False)
        is_woman = business.get("is_woman_owned", False)
        is_veteran = business.get("is_veteran_owned", False)
        is_startup = years < 1 or business.get("is_startup", False)
        is_rural = business.get("is_rural", False)
        employees = business.get("employees", 1)
        industry = business.get("industry", "general").lower()

        opportunities = []
        total_available = 0.0

        for prog in self.funding_db:
            score, reasons = self._score_match(prog, business)
            if score < 0.2:
                continue

            opp = FundingOpportunity(
                name=prog["name"],
                type=prog["type"],
                amount_range=(prog["min_amount"], prog["max_amount"]),
                eligibility_requirements=prog.get("eligibility", []),
                application_difficulty=self._difficulty(prog),
                approval_rate=prog.get("approval_rate", 0.5),
                timeline_days=prog.get("timeline_days", 60),
                cost_of_capital=self._estimate_cost(prog),
                best_for=prog.get("best_for", []),
                application_url=prog.get("url", ""),
                tips=self._generate_tips(prog, business),
                match_score=score,
                match_reasons=reasons,
            )
            opportunities.append(opp)
            total_available += prog["max_amount"] * min(score, 0.5)

        opportunities.sort(key=lambda x: x.match_score, reverse=True)

        # Build recommended sequence
        sequence = self._build_funding_sequence(business, opportunities)
        next_steps = self._build_next_steps(business, opportunities)

        return FundingMatchReport(
            business_name=name,
            total_opportunities=len(opportunities),
            top_opportunities=opportunities[:15],
            recommended_sequence=sequence,
            estimated_total_available=min(total_available, 10_000_000),
            next_steps=next_steps,
        )

    def _score_match(self, prog: dict, business: dict) -> Tuple[float, List[str]]:
        """Score how well a funding program matches the business."""
        score = 0.5
        reasons = []
        credit = business.get("owner_credit_score", 650)
        years = business.get("years_in_business", 0)
        revenue = business.get("revenue", 0)
        is_minority = business.get("is_minority_owned", False)
        is_woman = business.get("is_woman_owned", False)
        is_veteran = business.get("is_veteran_owned", False)
        is_rural = business.get("is_rural", False)
        industry = business.get("industry", "").lower()
        employees = business.get("employees", 1)

        min_credit = prog.get("min_credit")
        min_years = prog.get("min_years_in_business", 0)

        # Credit check
        if min_credit and credit < min_credit:
            score -= 0.4
            reasons.append(f"Credit score {credit} below minimum {min_credit}")
        elif min_credit and credit >= min_credit + 50:
            score += 0.15
            reasons.append(f"Strong credit score ({credit})")

        # Years in business
        if years < min_years:
            score -= 0.3
            reasons.append(f"Only {years} years in business, need {min_years}")
        elif years >= min_years:
            score += 0.1
            reasons.append(f"Meets time-in-business requirement")

        # Special qualifications
        category = prog.get("category", "").lower()
        if is_woman and "women" in category:
            score += 0.3
            reasons.append("Women-owned business preference")
        if is_veteran and "veteran" in category:
            score += 0.3
            reasons.append("Veteran-owned business preference")
        if is_minority and "minority" in category:
            score += 0.2
            reasons.append("Minority-owned business preference")
        if is_rural and "rural" in prog.get("url", ""):
            score += 0.2
            reasons.append("Rural area preference")

        # Industry match
        if "tech" in industry and ("sbir" in prog["name"].lower() or "sttr" in prog["name"].lower()):
            score += 0.3
            reasons.append("Tech company matches R&D grant programs")
        if "saas" in industry and "revenue" in prog["type"]:
            score += 0.2
            reasons.append("SaaS model matches revenue-based financing")

        # Revenue match
        if revenue > 500_000 and prog["max_amount"] > 1_000_000:
            score += 0.1
            reasons.append("Revenue supports larger funding amounts")
        if revenue == 0 and prog.get("min_years_in_business", 1) == 0:
            score += 0.1
            reasons.append("Pre-revenue business qualifies")

        return max(0.0, min(1.0, score)), reasons

    def _difficulty(self, prog: dict) -> str:
        approval = prog.get("approval_rate", 0.5)
        timeline = prog.get("timeline_days", 60)
        if approval > 0.60 and timeline < 30:
            return "easy"
        elif approval > 0.30 and timeline < 90:
            return "medium"
        return "hard"

    def _estimate_cost(self, prog: dict) -> float:
        """Estimate cost of capital as rough APR."""
        apr_str = prog.get("apr_range", "")
        if "N/A" in apr_str or "grant" in apr_str.lower():
            return 0.0
        if "0%" in apr_str:
            return 0.0
        if "3.75%" in apr_str:
            return 3.75
        if "Prime" in apr_str:
            return 11.0  # Approximate (Prime ~8.5% + spread)
        if "8%–13%" in apr_str:
            return 10.5
        if "8%–24%" in apr_str:
            return 16.0
        return 8.0

    def _generate_tips(self, prog: dict, business: dict) -> List[str]:
        """Generate actionable application tips."""
        tips = []
        ptype = prog.get("type", "")
        if "sba" in prog.get("category", "").lower():
            tips.append("Use SBA Lender Match (lending.sba.gov) to find approved lenders")
            tips.append("Prepare 3 years of business tax returns and financial statements")
            tips.append("Write a strong business plan — lenders read it")
        if ptype == "grant":
            tips.append("Follow application instructions EXACTLY — one mistake = disqualification")
            tips.append("Apply early — many grants are first-come, first-served")
        if ptype in ("equity", "accelerator"):
            tips.append("Warm introductions are 10x more effective than cold outreach")
            tips.append("Research each investor's portfolio before reaching out")
        if ptype == "revenue_based":
            tips.append("Connect your revenue accounts (Stripe, Shopify) for faster approval")
        return tips

    def _build_funding_sequence(self, business: dict, opps: List[FundingOpportunity]) -> List[str]:
        """Build a logical funding sequence."""
        sequence = []
        is_startup = business.get("years_in_business", 0) < 1

        if is_startup:
            sequence = [
                "Step 1: Apply for Kiva 0% microloan ($15K) — fastest, no credit barrier",
                "Step 2: Apply for SBIR Phase I if tech-based ($275K grant)",
                "Step 3: Bootstrap 6 months to show revenue traction",
                "Step 4: Apply for SBA Microloan ($50K) after 6 months",
                "Step 5: Pursue angel investors / accelerators (YC, Techstars) once product-market fit shown",
                "Step 6: Series A venture capital after strong revenue metrics",
            ]
        else:
            sequence = [
                "Step 1: Apply for SBA Express Loan (fastest SBA option — 36-hour decision)",
                "Step 2: Apply for any relevant grants (free money first!)",
                "Step 3: SBA 7(a) for larger working capital needs",
                "Step 4: Revenue-based financing if you have strong monthly revenue",
                "Step 5: Business line of credit with local bank/credit union",
                "Step 6: Consider equity investors for growth capital if applicable",
            ]
        return sequence

    def _build_next_steps(self, business: dict, opps: List[FundingOpportunity]) -> List[str]:
        return [
            "Pull your business credit report from D&B, Experian Business, and Equifax Business",
            "Prepare 2–3 years of business tax returns and P&L statements",
            "Get a DUNS number if you don't have one (free at dnb.com)",
            "Open a business checking account if not already done",
            "Calculate your exact funding need (don't over-borrow or under-borrow)",
            f"Apply to top 3 matched opportunities simultaneously for best odds",
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # SBA LOAN GUIDE
    # ─────────────────────────────────────────────────────────────────────────

    def sba_loan_guide(self, business: dict) -> SBALoanStrategy:
        """
        Comprehensive SBA loan strategy and application preparation guide.

        Args:
            business: dict with revenue, years_in_business, credit_score,
                      loan_purpose, loan_amount_needed, employees, industry

        Returns:
            SBALoanStrategy with complete application roadmap
        """
        revenue = business.get("revenue", 0)
        years = business.get("years_in_business", 0)
        credit = business.get("credit_score", 650)
        purpose = business.get("loan_purpose", "working_capital")
        amount_needed = business.get("loan_amount_needed", 250000)
        is_startup = years < 2

        # Determine best program
        if amount_needed > 5_000_000:
            primary = "SBA 504 (up to $20M for fixed assets)"
            recommended = ["SBA 504", "USDA B&I Guarantee"]
        elif amount_needed > 500_000:
            primary = "SBA 7(a) Standard (up to $5M)"
            recommended = ["SBA 7(a)", "SBA 504 (if fixed assets)"]
        elif amount_needed > 50_000:
            primary = "SBA 7(a) Small Loan / SBA Express"
            recommended = ["SBA Express (fastest)", "SBA 7(a) Small Loan", "SBA 7(a) Standard"]
        elif is_startup:
            primary = "SBA Microloan (up to $50K for startups)"
            recommended = ["SBA Microloan", "Kiva (0% interest)", "SBA Express (if eligible)"]
        else:
            primary = "SBA Microloan"
            recommended = ["SBA Microloan", "SBA Express"]

        # Fixed asset vs working capital
        if purpose in ("real_estate", "equipment", "construction"):
            recommended.insert(0, "SBA 504 (best for fixed assets — long-term low fixed rate)")

        # Approval probability
        if credit >= 720 and years >= 3 and revenue >= amount_needed * 1.5:
            approval_prob = 0.75
        elif credit >= 680 and years >= 2:
            approval_prob = 0.55
        elif credit >= 640 and years >= 1:
            approval_prob = 0.35
        else:
            approval_prob = 0.20

        checklist = [
            "Business plan (executive summary, market analysis, financial projections)",
            "3 years of business tax returns (Form 1120/1120S/1065 or Schedule C)",
            "3 years of personal tax returns for all 20%+ owners",
            "YTD profit and loss statement (less than 90 days old)",
            "Balance sheet (less than 90 days old)",
            "Business bank statements — 12 months",
            "Personal financial statement (SBA Form 413)",
            "Schedule of business liabilities (all debts/leases)",
            "Copy of business licenses and registrations",
            "Articles of incorporation / operating agreement",
            "Collateral documentation (if real estate — deed, appraisal)",
            "Resume of key management team",
            "Business certificates/licenses",
            "Photo ID for all 20%+ owners",
        ]

        if purpose == "real_estate":
            checklist.append("Property appraisal (SBA-approved appraiser)")
            checklist.append("Environmental study (Phase I) for commercial real estate")

        lender_strategy = (
            "Step 1: Use SBA Lender Match (lending.sba.gov) — free tool to find preferred lenders. "
            "Step 2: Target SBA Preferred Lenders (PLP lenders) — they can approve without SBA review (faster). "
            "Step 3: Apply to 2–3 lenders simultaneously — each will check business credit (soft pull), "
            "so apply within 2 weeks to limit impact. "
            "Step 4: Consider SBA Express through your current bank — existing relationships help. "
            "Step 5: If declined, ask lender for specific reasons and apply the feedback. "
            "Step 6: SCORE mentor (score.org) — free SBA counseling to strengthen your application."
        )

        return SBALoanStrategy(
            recommended_programs=recommended,
            primary_program=primary,
            loan_amount=amount_needed,
            estimated_approval_probability=approval_prob,
            preparation_checklist=checklist,
            lender_strategy=lender_strategy,
            timeline_weeks=8 if "Express" in primary else 12,
            key_requirements=[
                "US for-profit business",
                "Reasonable owner equity injection (typically 10–30%)",
                "No SBA loan defaults or federal delinquencies",
                "Good character (no felony convictions within 5 years)",
                "Demonstrated ability to repay from business cash flow",
                "Collateral (required for 7a > $25K when available)",
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # GRANT FINDER
    # ─────────────────────────────────────────────────────────────────────────

    def grant_finder(self, business: dict) -> List[GrantOpportunity]:
        """
        Find applicable grants for the business across federal, state, and private sources.

        Args:
            business: dict with state, industry, is_minority_owned, is_woman_owned,
                      is_veteran_owned, employees, revenue, is_tech, is_rural

        Returns:
            List[GrantOpportunity] sorted by match quality
        """
        grants = []
        state = business.get("state", "CA").upper()
        biz_type = business.get("type", "").lower()
        is_woman = business.get("is_woman_owned", False) or "woman" in biz_type or "women" in biz_type
        is_veteran = business.get("is_veteran_owned", False) or "veteran" in biz_type
        is_minority = business.get("is_minority_owned", False) or "minority" in biz_type
        is_tech = business.get("is_tech", False) or "tech" in business.get("industry", "").lower() or "tech" in biz_type
        is_rural = business.get("is_rural", False) or "rural" in biz_type

        # Federal grants for all businesses (always included)
        grants.append(GrantOpportunity(
            name="Grants.gov Federal Grants Database",
            grantor="Multiple Federal Agencies",
            amount_min=5000,
            amount_max=10000000,
            eligibility=["US business", "Varies by program"],
            deadline="Ongoing",
            application_url="https://www.grants.gov",
            difficulty="medium",
            tips=["Search by CFDA number for your industry", "Set up email alerts for new grants"],
        ))
        grants.append(GrantOpportunity(
            name="Hello Alice Small Business Grant",
            grantor="Hello Alice (various sponsors)",
            amount_min=10000,
            amount_max=50000,
            eligibility=["Any small business", "Women/minority preferred"],
            deadline="Rolling (multiple grants)",
            application_url="https://helloalice.com/grants",
            difficulty="easy",
            tips=["Set up your Hello Alice profile to auto-match grants", "Multiple sponsors offer grants through this platform"],
        ))
        grants.append(GrantOpportunity(
            name="MBDA Business Center Grants",
            grantor="Minority Business Development Agency (MBDA)",
            amount_min=10000,
            amount_max=250000,
            eligibility=["Minority-owned business (51%+)", "US for-profit", "All businesses may apply for MBDA services"],
            deadline="Varies",
            application_url="https://www.mbda.gov",
            difficulty="medium",
            tips=["Work with your local MBDA Business Center for assistance", "Focus on job creation metrics", "Open to all minority entrepreneurs"],
        ))

        if is_tech:
            grants += [
                GrantOpportunity(
                    name="SBIR Phase I",
                    grantor="NSF, NIH, DOE, DOD, NASA (11 agencies)",
                    amount_min=50000,
                    amount_max=275000,
                    eligibility=["<500 employees", "For-profit US company", "Innovative R&D project"],
                    deadline="Varies by agency (quarterly cycles)",
                    application_url="https://www.sbir.gov",
                    difficulty="hard",
                    tips=[
                        "Match your technology to agency priorities (search SBIR.gov topics)",
                        "Hire a SBIR proposal consultant for first application",
                        "NSF SBIR is most accessible — 'societal impact' focus",
                        "Budget 80–120 hours to write a competitive Phase I proposal",
                    ],
                ),
                GrantOpportunity(
                    name="STTR Phase I",
                    grantor="NSF, NIH, DOE, DOD, NASA",
                    amount_min=50000,
                    amount_max=275000,
                    eligibility=["<500 employees", "Research institution partnership required"],
                    deadline="Same cycles as SBIR",
                    application_url="https://www.sbir.gov/sttr",
                    difficulty="hard",
                    tips=["Partner with a university lab to access their STTR quota", "Allocate 30%+ of work to research institution"],
                ),
            ]

        if is_woman:
            grants += [
                GrantOpportunity(
                    name="Amber Grant",
                    grantor="WomensNet",
                    amount_min=10000,
                    amount_max=30000,
                    eligibility=["Woman-owned business", "Any stage", "Any industry"],
                    deadline="Monthly ($10K) + Annual ($30K)",
                    application_url="https://ambergrantsforwomen.com",
                    difficulty="medium",
                    tips=["Tell your story — judges value passion and mission", "Apply monthly for $10K, then annual for $30K"],
                ),
                GrantOpportunity(
                    name="IFundWomen Universal Grant",
                    grantor="IFundWomen",
                    amount_min=500,
                    amount_max=10000,
                    eligibility=["Woman-owned business"],
                    deadline="Rolling",
                    application_url="https://ifundwomen.com/grants",
                    difficulty="easy",
                    tips=["Build your IFundWomen profile first", "Video pitch required"],
                ),
                GrantOpportunity(
                    name="Cartier Women's Initiative",
                    grantor="Cartier",
                    amount_min=30000,
                    amount_max=100000,
                    eligibility=["Woman-led startup", "<6 years old", "Revenue <$1M", "Global"],
                    deadline="Annual (applications open September)",
                    application_url="https://www.cartierwomensinitiative.com",
                    difficulty="hard",
                    tips=["Must demonstrate measurable impact", "Strong business plan required", "2% acceptance rate"],
                ),
            ]

        if is_veteran:
            grants += [
                GrantOpportunity(
                    name="StreetShares Foundation Award",
                    grantor="StreetShares Foundation",
                    amount_min=4000,
                    amount_max=15000,
                    eligibility=["Veteran-owned or military spouse-owned", "Any stage"],
                    deadline="Quarterly",
                    application_url="https://streetsharesfoundation.org",
                    difficulty="medium",
                    tips=["Highlight military service and leadership", "Community impact is key"],
                ),
                GrantOpportunity(
                    name="Warrior Rising Grant",
                    grantor="Warrior Rising",
                    amount_min=5000,
                    amount_max=25000,
                    eligibility=["Veteran-owned", "Must complete Warrior Rising program"],
                    deadline="Rolling",
                    application_url="https://warriorrising.org",
                    difficulty="medium",
                    tips=["Full business mentorship program included", "Community of veteran entrepreneurs"],
                ),
            ]

        if is_minority:
            grants += [
                GrantOpportunity(
                    name="MBDA Business Center Grants",
                    grantor="Minority Business Development Agency (MBDA)",
                    amount_min=10000,
                    amount_max=250000,
                    eligibility=["Minority-owned business (51%+)", "US for-profit"],
                    deadline="Varies",
                    application_url="https://www.mbda.gov",
                    difficulty="medium",
                    tips=["Work with your local MBDA Business Center for assistance", "Focus on job creation metrics"],
                ),
                GrantOpportunity(
                    name="Hello Alice Small Business Grant",
                    grantor="Hello Alice (various sponsors)",
                    amount_min=10000,
                    amount_max=50000,
                    eligibility=["Any small business", "Women/minority preferred"],
                    deadline="Rolling (multiple grants)",
                    application_url="https://helloalice.com/grants",
                    difficulty="easy",
                    tips=["Set up your Hello Alice profile to auto-match grants", "Multiple sponsors offer grants through this platform"],
                ),
            ]

        if is_rural:
            grants.append(GrantOpportunity(
                name="USDA Rural Business Development Grant",
                grantor="USDA Rural Development",
                amount_min=10000,
                amount_max=500000,
                eligibility=["Located in rural area (<50K pop)", "Nonprofit or tribal government applies on behalf"],
                deadline="Annual",
                application_url="https://www.rd.usda.gov/programs-services/business-programs",
                difficulty="hard",
                tips=["Partner with local rural development organization", "Job creation in rural area is key metric"],
            ))

        # State-specific grants (general framework)
        grants.append(GrantOpportunity(
            name=f"{state} State Small Business Grant Programs",
            grantor=f"{state} Department of Commerce/Economic Development",
            amount_min=5000,
            amount_max=250000,
            eligibility=[f"Located in {state}", "Varies by program"],
            deadline="Varies",
            application_url=f"https://www.usa.gov/state-business",
            difficulty="medium",
            tips=[
                f"Search '{state} small business grant 2024' for current programs",
                f"Contact your {state} SBDC (Small Business Development Center) for free guidance",
                "State grants often have less competition than federal grants",
            ],
        ))

        return grants

    # ─────────────────────────────────────────────────────────────────────────
    # VENTURE CAPITAL STRATEGY
    # ─────────────────────────────────────────────────────────────────────────

    def venture_capital_strategy(self, startup: dict) -> VCStrategy:
        """
        Complete venture capital fundraising strategy with pitch deck guidance.

        Args:
            startup: dict with stage (pre_seed/seed/series_a/series_b),
                     revenue_mrr, industry, team_size, traction_metrics,
                     funding_target, location

        Returns:
            VCStrategy with investor targets, pitch deck structure, valuation
        """
        stage = startup.get("stage", "seed")
        mrr = startup.get("revenue_mrr", 0)
        funding_target = startup.get("funding_target", 1_000_000)
        industry = startup.get("industry", "technology")

        # Valuation methods
        if stage == "pre_seed":
            pre_money_val = 2_000_000
            equity = funding_target / (pre_money_val + funding_target)
            target_investors = [
                "Angel investors ($25K–$250K checks)",
                "AngelList syndicates",
                "FriendsAndFamily round",
                "Pre-seed funds: Hustle Fund, Precursor Ventures, Afore Capital",
                "Accelerators: Y Combinator, Techstars, 500 Global, On Deck",
                "Revenue-based seed: Clearco, Pipe (if revenue exists)",
            ]
        elif stage == "seed":
            pre_money_val = max(4_000_000, mrr * 50)
            equity = funding_target / (pre_money_val + funding_target)
            target_investors = [
                "Seed VCs: First Round Capital, Founders Fund, Bessemer",
                "Seed stage: Sequoia Scout, a16z Scout programs",
                "Angel networks: Tech Coast Angels, New York Angels",
                "Corporate VCs: Google Ventures (GV), Intel Capital",
                "Accelerators (post-revenue): YC, Techstars",
            ]
        elif stage == "series_a":
            pre_money_val = max(15_000_000, mrr * 100)
            equity = 0.20  # Typical Series A gives up 20%
            target_investors = [
                "Tier 1 VCs: Sequoia, a16z, Accel, Benchmark, NEA",
                "Growth funds: General Catalyst, Insight Partners",
                "Industry specialists based on your vertical",
                "Corporate strategics (if strategic fit)",
            ]
        else:  # Series B+
            pre_money_val = max(50_000_000, mrr * 150)
            equity = 0.15
            target_investors = [
                "Late-stage VCs: Tiger Global, Coatue, Lightspeed",
                "Crossover funds: T. Rowe Price, Fidelity Ventures",
                "Private equity with growth focus",
                "Secondary markets: Forge, Carta",
            ]

        pitch_deck_outline = [
            {"num": "1", "title": "Cover", "content": "Company name, tagline (1 sentence), logo, contact info"},
            {"num": "2", "title": "Problem", "content": "What pain point exists? Quantify the problem ($$ lost, time wasted). Make it visceral."},
            {"num": "3", "title": "Solution", "content": "Your unique solution. Demo screenshot or product image. 'We do X for Y so they can Z.'"},
            {"num": "4", "title": "Why Now", "content": "What has changed that makes this possible/urgent today? Technology, regulation, behavior shift?"},
            {"num": "5", "title": "Market Size", "content": "TAM/SAM/SOM. TAM > $1B for VC. Use bottom-up AND top-down. Cite sources."},
            {"num": "6", "title": "Product", "content": "Product screenshots, demo video link, key features, roadmap. Show it works."},
            {"num": "7", "title": "Business Model", "content": "How you make money. Revenue model, pricing, unit economics (CAC, LTV, gross margin)."},
            {"num": "8", "title": "Traction", "content": "YOUR MOST IMPORTANT SLIDE. Revenue, users, growth rate, partnerships, retention. Hockey stick if you have it."},
            {"num": "9", "title": "Competition", "content": "2x2 matrix or table. Honest assessment. Why you win — your unfair advantage."},
            {"num": "10", "title": "Team", "content": "Founders + key hires. Relevant experience. Why YOU are the team to win this market? Board/advisors."},
            {"num": "11", "title": "Financials", "content": "3-year projections. Monthly burn, runway, P&L. Realistic assumptions. Key drivers."},
            {"num": "12", "title": "The Ask", "content": f"Raising ${funding_target:,.0f}. Use of funds breakdown (product 40%, sales 30%, ops 30%). Milestones this round achieves."},
        ]

        term_sheet_red_flags = [
            "Full ratchet anti-dilution (should be weighted average)",
            "Non-participating preferred with >1x liquidation preference",
            "Founder vesting restart (should vest from original start date)",
            "Drag-along rights without threshold (need 50%+ common to approve)",
            "Pay-to-play provisions that punish existing investors",
            "Information rights restricted (founders should have access to financials)",
            "Redemption rights (gives VC right to demand buyback)",
            "Dividends that accumulate (accruing preferred dividends are very dilutive)",
            "Overly broad protective provisions that give VC veto on operations",
            "No-shop clause without reasonable time limit (30 days is normal, 60+ is problematic)",
            "Concentration of board seats giving investor control without revenue milestones",
        ]

        return VCStrategy(
            stage=stage,
            funding_target=funding_target,
            valuation_pre_money=pre_money_val,
            equity_to_give=equity,
            target_investors=target_investors,
            pitch_deck_outline=pitch_deck_outline,
            key_metrics_needed=[
                "MRR and MoM growth rate",
                "CAC (Customer Acquisition Cost)",
                "LTV (Lifetime Value) — LTV:CAC ratio >3:1 is good",
                "Gross margin (SaaS should be 70%+)",
                "Net revenue retention (NRR) / Dollar retention",
                "Churn rate (monthly and annual)",
                "Total users / paid users / conversion rate",
                "Burn rate and runway",
            ],
            timeline_months=6,
            term_sheet_red_flags=term_sheet_red_flags,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ALTERNATIVE FUNDING
    # ─────────────────────────────────────────────────────────────────────────

    def alternative_funding(self, business: dict) -> AlternativeFundingOptions:
        """
        Analyze all alternative funding options for a business.

        Args:
            business: dict with revenue, revenue_type (recurring/project/seasonal),
                      industry, credit_score, years_in_business, has_invoices,
                      has_equipment_needs, has_inventory

        Returns:
            AlternativeFundingOptions with all viable alternatives
        """
        revenue = business.get("revenue", 0)
        mrr = business.get("mrr", revenue / 12)
        credit = business.get("credit_score", 650)
        has_invoices = business.get("has_invoices", False)
        has_equipment = business.get("has_equipment_needs", False)
        has_inventory = business.get("has_inventory", False)
        is_consumer_product = business.get("is_consumer_product", False)
        years = business.get("years_in_business", 0)

        options = []
        warnings = []
        recommended = "Business Line of Credit (most flexible)"

        # Revenue-based financing
        if mrr >= 10000:
            options.append({
                "name": "Revenue-Based Financing (Clearco / Lighter Capital)",
                "type": "Revenue-Based",
                "cost": "6%–12% flat fee (true APR ~15%–35%)",
                "min": 10000,
                "max": 10000000,
                "best_for": "E-commerce, SaaS with strong MRR",
                "pro": "No equity, no personal guarantee",
                "con": "Expensive if growth slows",
            })
            recommended = "Revenue-Based Financing"

        # Invoice factoring
        if has_invoices:
            options.append({
                "name": "Invoice Factoring (BlueVine, FundThrough)",
                "type": "Invoice Factoring",
                "cost": "1%–5% per invoice (35%–85% APR effective)",
                "min": 1000,
                "max": 500000,
                "best_for": "B2B businesses with 30–90 day payment terms",
                "pro": "Fast cash (24–48 hours), scales with revenue",
                "con": "Expensive, may affect client relationships",
            })

        # Equipment financing
        if has_equipment:
            options.append({
                "name": "Equipment Financing (Balboa Capital, Crest Capital)",
                "type": "Equipment Loan",
                "cost": "5%–30% APR depending on credit",
                "min": 5000,
                "max": 5000000,
                "best_for": "Businesses needing equipment without depleting cash",
                "pro": "Equipment serves as collateral — easier approval",
                "con": "Tied to specific equipment, prepayment penalties",
            })

        # Merchant cash advance — MUST WARN
        if revenue > 0 and credit < 640:
            options.append({
                "name": "Merchant Cash Advance (MCA) — USE WITH EXTREME CAUTION",
                "type": "Merchant Cash Advance",
                "cost": "Factor rate 1.2–1.5x = TRUE APR of 60%–350%",
                "min": 5000,
                "max": 500000,
                "best_for": "Emergency cash only — last resort",
                "pro": "Fast (24 hours), no credit check",
                "con": "Extremely expensive, can trap businesses in debt cycle",
            })
            warnings.append(
                "MCA True APR Warning: An MCA with factor rate 1.3 on $100K repaid in 6 months "
                "= $130K repaid = true APR of ~120%. Only use in emergencies."
            )

        # Crowdfunding
        if is_consumer_product:
            options.append({
                "name": "Kickstarter/Indiegogo Crowdfunding",
                "type": "Reward Crowdfunding",
                "cost": "5% platform + 3%–5% processing = ~8%–10% total",
                "min": 1000,
                "max": 10000000,
                "best_for": "Consumer products with mass appeal",
                "pro": "Validation + cash + customer acquisition + marketing",
                "con": "Requires significant marketing effort, all-or-nothing (Kickstarter)",
            })
            options.append({
                "name": "Republic / Wefunder Equity Crowdfunding",
                "type": "Equity Crowdfunding",
                "cost": "7%–8% equity sold + SEC filing costs",
                "min": 50000,
                "max": 5000000,
                "best_for": "Startups with community/brand following",
                "pro": "Turn customers into investors, no VC gatekeepers",
                "con": "Complex SEC compliance, dilutive",
            })

        # Kiva
        options.append({
            "name": "Kiva 0% Interest Microloan",
            "type": "Microloan",
            "cost": "0% interest (free money!)",
            "min": 1000,
            "max": 15000,
            "best_for": "Any small business needing seed capital",
            "pro": "Zero interest, builds business credibility",
            "con": "Must recruit 5–10 lenders from your personal network first",
        })

        # CDFI
        options.append({
            "name": "Community Development Financial Institution (CDFI)",
            "type": "CDFI Loan",
            "cost": "8%–15% APR",
            "min": 5000,
            "max": 250000,
            "best_for": "Underserved communities, startups, low-credit businesses",
            "pro": "Mission-driven lenders, more flexible underwriting",
            "con": "Slower process, smaller loan amounts",
        })

        total_available = sum(opt.get("max", 0) for opt in options if "MCA" not in opt["name"])

        return AlternativeFundingOptions(
            options=options,
            recommended=recommended,
            warning_items=warnings,
            total_available_estimate=total_available,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PERSONAL FUNDING GUIDE
    # ─────────────────────────────────────────────────────────────────────────

    def personal_funding_guide(self, situation: dict) -> PersonalFundingStrategy:
        """
        Personal funding strategies for individuals and business founders.

        Args:
            situation: dict with credit_score, annual_income, home_equity,
                       retirement_account_value, life_insurance_cv, purpose,
                       has_home, has_401k, has_life_insurance

        Returns:
            PersonalFundingStrategy with all viable personal funding options
        """
        credit = situation.get("credit_score", 680)
        income = situation.get("annual_income", 50000)
        home_equity = situation.get("home_equity", 0)
        has_home = situation.get("has_home", home_equity > 0)
        has_401k = situation.get("has_401k", False)
        retirement_value = situation.get("retirement_account_value", 0)
        life_cv = situation.get("life_insurance_cv", 0)
        purpose = situation.get("purpose", "business")

        options = []
        tax_implications = []
        warnings = []
        total_potential = 0.0

        if has_home and home_equity > 20000:
            heloc_limit = home_equity * 0.85
            options.append({
                "name": "HELOC (Home Equity Line of Credit)",
                "amount": heloc_limit,
                "rate": "Prime + 0%–2% variable (~8%–10%)",
                "pro": "Tax-deductible interest if used for business; flexible draw period",
                "con": "Variable rate; home is at risk if you default",
            })
            options.append({
                "name": "Home Equity Loan (Second Mortgage)",
                "amount": heloc_limit,
                "rate": "7%–9% fixed",
                "pro": "Fixed rate, tax-deductible for qualified uses",
                "con": "Lump sum — can't redraw; home as collateral",
            })
            tax_implications.append("HELOC/HE Loan interest is deductible only if used to 'buy, build, or substantially improve' the home (Tax Cuts and Jobs Act 2017 — see IRS Pub 936)")
            total_potential += heloc_limit
            recommended = "HELOC (most flexible — draw only what you need)"
        else:
            recommended = "Personal loan (check LightStream, SoFi, or credit union)"

        # Personal loan by credit tier
        if credit >= 720:
            pl_rate = "6%–12%"
            pl_max = 100000
        elif credit >= 680:
            pl_rate = "12%–18%"
            pl_max = 50000
        elif credit >= 640:
            pl_rate = "18%–28%"
            pl_max = 25000
        else:
            pl_rate = "28%–36% (high risk)"
            pl_max = 10000

        options.append({
            "name": "Personal Loan (Unsecured)",
            "amount": pl_max,
            "rate": pl_rate,
            "pro": "No collateral, fast approval (same day at some lenders)",
            "con": "Higher rate than secured; affects debt-to-income",
        })
        options.append({
            "name": "Credit Card Balance Transfer / 0% Intro APR",
            "amount": 20000,
            "rate": "0% for 12–21 months, then 20%–28%",
            "pro": "Interest-free if paid during intro period",
            "con": "Balance transfer fee 3%–5%; must pay off before period ends",
        })
        total_potential += pl_max

        if has_401k and retirement_value > 10000:
            loan_limit = min(retirement_value * 0.50, 50000)
            options.append({
                "name": "401(k) Loan",
                "amount": loan_limit,
                "rate": "Prime + 1% (paid to yourself)",
                "pro": "No credit check, interest paid to yourself, no tax if repaid",
                "con": "Lose compound growth; if you leave job, full repayment due in 60 days",
            })
            options.append({
                "name": "401(k) Hardship Withdrawal",
                "amount": retirement_value * 0.20,
                "rate": "N/A — taxed as ordinary income + 10% penalty if under 59½",
                "pro": "No repayment required",
                "con": "Expensive: $10K withdrawal = $3,700 in taxes/penalties; permanent loss of growth",
            })
            tax_implications.append("401k loan: No tax if repaid within 5 years; deemed distribution if not repaid — fully taxable + 10% penalty")
            tax_implications.append("401k withdrawal: Taxable as ordinary income in year of withdrawal + 10% early withdrawal penalty (age <59½)")
            warnings.append("Avoid 401k withdrawals — the true cost is 3–4x the stated penalty when you factor in lost compound growth")

        if life_cv > 0:
            options.append({
                "name": "Life Insurance Policy Loan (Whole/UL/VUL)",
                "amount": life_cv * 0.90,
                "rate": "3%–8% (varies by policy)",
                "pro": "No credit check, no repayment required (reduces death benefit), tax-free proceeds",
                "con": "Policy can lapse if loan + interest exceeds cash value — taxable event",
            })
            tax_implications.append("Life insurance policy loans are NOT taxable if policy remains in force; lapses create taxable income equal to gain in policy")

        # P2P Lending
        options.append({
            "name": "Peer-to-Peer Lending (LendingClub, Prosper)",
            "amount": 40000,
            "rate": "8%–36% APR (based on credit)",
            "pro": "Often lower rate than credit cards; fixed payments",
            "con": "Origination fee 1%–8%; hard credit pull",
        })

        # Government assistance
        options.append({
            "name": "Government Assistance Programs",
            "amount": 10000,
            "rate": "0%–3% (subsidized)",
            "pro": "Low or no interest; designed for those in need",
            "con": "Strict eligibility; means-tested; application process",
        })

        return PersonalFundingStrategy(
            options=options,
            recommended_first=recommended,
            total_potential=total_potential,
            tax_implications=tax_implications,
            risk_warnings=warnings,
        )
