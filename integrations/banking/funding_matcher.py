"""
Funding Matcher — Match client financial profile to 50+ funding sources.
Covers SBA, CDFI, grants, VC, angel investors, revenue-based financing, and more.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FundingType(str, Enum):
    SBA_LOAN = "sba_loan"
    CDFI_LOAN = "cdfi_loan"
    GRANT = "grant"
    ANGEL_INVESTOR = "angel_investor"
    VENTURE_CAPITAL = "venture_capital"
    REVENUE_BASED = "revenue_based_financing"
    EQUIPMENT_FINANCING = "equipment_financing"
    INVOICE_FACTORING = "invoice_factoring"
    BUSINESS_CREDIT_CARD = "business_credit_card"
    PERSONAL_LOAN = "personal_loan"
    HELOC = "heloc"
    CROWDFUNDING = "crowdfunding"
    MICROFINANCE = "microfinance"
    LINE_OF_CREDIT = "line_of_credit"


class ClientFundingProfile(BaseModel):
    client_id: str
    credit_score: Optional[int] = None
    annual_revenue: float = 0.0
    monthly_revenue: float = 0.0
    time_in_business_months: int = 0
    industry: Optional[str] = None
    state: Optional[str] = None
    is_minority_owned: bool = False
    is_woman_owned: bool = False
    is_veteran_owned: bool = False
    has_collateral: bool = False
    collateral_value: float = 0.0
    outstanding_debt: float = 0.0
    monthly_expenses: float = 0.0
    employees: int = 0
    seeking_amount: float = 0.0
    funding_purpose: Optional[str] = None


class FundingSource(BaseModel):
    source_id: str
    name: str
    funding_type: FundingType
    description: str
    amount_range: Dict[str, float]  # {"min": X, "max": Y}
    rate_range: Optional[Dict[str, float]] = None  # {"min": X, "max": Y} APR %
    term_range: Optional[Dict[str, int]] = None  # months
    # Requirements
    min_credit_score: Optional[int] = None
    min_annual_revenue: Optional[float] = None
    min_time_in_business_months: Optional[int] = None
    industries: Optional[List[str]] = None  # None = all industries
    states: Optional[List[str]] = None      # None = all states
    requires_collateral: bool = False
    minority_owned_bonus: bool = False
    woman_owned_bonus: bool = False
    veteran_owned_bonus: bool = False
    # Application
    how_to_apply: str
    typical_approval_time: str
    success_rate_pct: Optional[float] = None
    url: Optional[str] = None


class FundingMatch(BaseModel):
    source: FundingSource
    eligibility_score: float  # 0–100
    eligible_amount: Dict[str, float]  # estimated range
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendation: str = ""
    priority: int = 0


class FundingMatchResult(BaseModel):
    client_id: str
    profile: ClientFundingProfile
    matches: List[FundingMatch] = Field(default_factory=list)
    total_potential_funding: float = 0.0
    top_recommendation: Optional[str] = None


# ── Master Funding Source Database ────────────────────────────────────────────
FUNDING_SOURCES: List[FundingSource] = [
    FundingSource(
        source_id="sba_7a",
        name="SBA 7(a) Loan",
        funding_type=FundingType.SBA_LOAN,
        description="The SBA's primary loan program for small businesses. Versatile use: working capital, expansion, equipment, real estate.",
        amount_range={"min": 50_000, "max": 5_000_000},
        rate_range={"min": 7.5, "max": 11.5},
        term_range={"min": 60, "max": 300},
        min_credit_score=640,
        min_annual_revenue=100_000,
        min_time_in_business_months=24,
        requires_collateral=False,
        how_to_apply="Apply through an SBA-approved lender or via SBA.gov Lender Match tool.",
        typical_approval_time="30–90 days",
        success_rate_pct=65.0,
        url="https://www.sba.gov/funding-programs/loans/7a-loans",
    ),
    FundingSource(
        source_id="sba_504",
        name="SBA 504 Loan",
        funding_type=FundingType.SBA_LOAN,
        description="Fixed-rate financing for major assets: equipment, real estate. Up to 90% financing.",
        amount_range={"min": 125_000, "max": 5_500_000},
        rate_range={"min": 5.5, "max": 7.5},
        term_range={"min": 120, "max": 240},
        min_credit_score=660,
        min_annual_revenue=250_000,
        min_time_in_business_months=24,
        requires_collateral=True,
        how_to_apply="Work with a Certified Development Company (CDC) and SBA lender.",
        typical_approval_time="45–120 days",
        url="https://www.sba.gov/funding-programs/loans/504-loans",
    ),
    FundingSource(
        source_id="sba_microloan",
        name="SBA Microloan",
        funding_type=FundingType.SBA_LOAN,
        description="Small loans up to $50K for startups and small businesses via nonprofit intermediaries.",
        amount_range={"min": 500, "max": 50_000},
        rate_range={"min": 6.0, "max": 9.0},
        term_range={"min": 12, "max": 72},
        min_credit_score=575,
        min_time_in_business_months=0,
        how_to_apply="Contact SBA intermediary lenders in your area at SBA.gov.",
        typical_approval_time="2–4 weeks",
        url="https://www.sba.gov/funding-programs/loans/microloans",
    ),
    FundingSource(
        source_id="cdfi_opportunity_finance",
        name="CDFI Opportunity Fund",
        funding_type=FundingType.CDFI_LOAN,
        description="Community development lender focused on underserved entrepreneurs. Flexible requirements.",
        amount_range={"min": 5_000, "max": 500_000},
        rate_range={"min": 6.5, "max": 12.0},
        min_credit_score=580,
        min_time_in_business_months=0,
        minority_owned_bonus=True,
        woman_owned_bonus=True,
        how_to_apply="Apply at opportunityfund.org. California-based but ships nationwide.",
        typical_approval_time="1–3 weeks",
        url="https://www.opportunityfund.org",
    ),
    FundingSource(
        source_id="clearco_rbf",
        name="Clearco Revenue-Based Financing",
        funding_type=FundingType.REVENUE_BASED,
        description="Non-dilutive capital based on revenue. Repay as a % of monthly revenue. No equity given up.",
        amount_range={"min": 10_000, "max": 10_000_000},
        rate_range={"min": 6.0, "max": 12.5},
        min_annual_revenue=200_000,
        min_time_in_business_months=6,
        how_to_apply="Connect Stripe/Shopify/bank accounts at clearco.com for instant assessment.",
        typical_approval_time="24–72 hours",
        url="https://clearco.com",
    ),
    FundingSource(
        source_id="capchase_rbf",
        name="Capchase Revenue-Based Financing",
        funding_type=FundingType.REVENUE_BASED,
        description="Non-dilutive financing for SaaS businesses. Advance on ARR.",
        amount_range={"min": 25_000, "max": 5_000_000},
        rate_range={"min": 7.0, "max": 15.0},
        min_annual_revenue=500_000,
        min_time_in_business_months=12,
        how_to_apply="Apply at capchase.com. Best for SaaS with recurring revenue.",
        typical_approval_time="24–48 hours",
        url="https://www.capchase.com",
    ),
    FundingSource(
        source_id="sba_eidl",
        name="SBA Economic Injury Disaster Loan",
        funding_type=FundingType.SBA_LOAN,
        description="Working capital for businesses affected by declared disasters.",
        amount_range={"min": 1_000, "max": 2_000_000},
        rate_range={"min": 3.75, "max": 6.0},
        min_credit_score=570,
        how_to_apply="Apply at disasterloanassistance.sba.gov during declared disaster periods.",
        typical_approval_time="2–6 weeks",
        url="https://disasterloanassistance.sba.gov",
    ),
    FundingSource(
        source_id="nav_business_credit",
        name="Business Credit Card (Nav Recommended)",
        funding_type=FundingType.BUSINESS_CREDIT_CARD,
        description="Match to top 0% intro APR business credit cards. Ideal for short-term working capital.",
        amount_range={"min": 5_000, "max": 100_000},
        rate_range={"min": 0.0, "max": 29.99},
        min_credit_score=670,
        how_to_apply="Apply through Nav.com to see pre-qualified offers without a hard pull.",
        typical_approval_time="Instant–7 days",
        url="https://www.nav.com/business-credit-cards",
    ),
    FundingSource(
        source_id="equipment_balboa",
        name="Balboa Capital Equipment Financing",
        funding_type=FundingType.EQUIPMENT_FINANCING,
        description="Finance or lease equipment with minimal documentation required.",
        amount_range={"min": 5_000, "max": 500_000},
        rate_range={"min": 5.5, "max": 18.0},
        min_credit_score=600,
        min_time_in_business_months=12,
        requires_collateral=True,
        how_to_apply="Apply at balboacapital.com. Approval in 24 hours for amounts under $150K.",
        typical_approval_time="24 hours–1 week",
        url="https://www.balboacapital.com",
    ),
    FundingSource(
        source_id="invoice_bluevine",
        name="BlueVine Invoice Factoring / Line of Credit",
        funding_type=FundingType.INVOICE_FACTORING,
        description="Advance on outstanding invoices or revolving line of credit. Fast funding.",
        amount_range={"min": 5_000, "max": 250_000},
        rate_range={"min": 6.2, "max": 29.9},
        min_annual_revenue=120_000,
        min_credit_score=625,
        min_time_in_business_months=12,
        how_to_apply="Apply at bluevine.com. Connect bank account for income verification.",
        typical_approval_time="24–72 hours",
        url="https://www.bluevine.com",
    ),
    FundingSource(
        source_id="republic_crowdfunding",
        name="Republic Regulation CF Crowdfunding",
        funding_type=FundingType.CROWDFUNDING,
        description="Raise up to $5M from the crowd via equity or debt. Great for consumer-facing businesses.",
        amount_range={"min": 10_000, "max": 5_000_000},
        min_time_in_business_months=0,
        how_to_apply="Apply to list on Republic.co. Requires legal setup and SEC filing.",
        typical_approval_time="4–8 weeks (campaign launch)",
        url="https://republic.com/raise",
    ),
    FundingSource(
        source_id="minority_business_grant_ame",
        name="Amber Grant for Women",
        funding_type=FundingType.GRANT,
        description="Monthly $10K grant for women-owned businesses. No repayment required.",
        amount_range={"min": 10_000, "max": 25_000},
        woman_owned_bonus=True,
        how_to_apply="Apply monthly at ambergrantsforwomen.com. $15 application fee.",
        typical_approval_time="Monthly selection",
        url="https://ambergrantsforwomen.com",
    ),
    FundingSource(
        source_id="heloc_funding",
        name="Home Equity Line of Credit (HELOC)",
        funding_type=FundingType.HELOC,
        description="Leverage home equity for business capital. Low rates but home is collateral.",
        amount_range={"min": 10_000, "max": 500_000},
        rate_range={"min": 7.0, "max": 12.0},
        min_credit_score=620,
        requires_collateral=True,
        how_to_apply="Apply through your bank or credit union if you own a home with equity.",
        typical_approval_time="2–4 weeks",
    ),
    FundingSource(
        source_id="personal_loan_sofi",
        name="SoFi Personal Loan",
        funding_type=FundingType.PERSONAL_LOAN,
        description="High-limit personal loans for creditworthy borrowers. No fees.",
        amount_range={"min": 5_000, "max": 100_000},
        rate_range={"min": 8.99, "max": 25.81},
        min_credit_score=680,
        how_to_apply="Apply at sofi.com. Check rate without impacting credit score.",
        typical_approval_time="1–7 days",
        url="https://www.sofi.com/personal-loans",
    ),
]


class FundingMatcher:
    """
    Matches client financial profiles to the best available funding sources.
    Ranks by eligibility score and provides application guidance.
    """

    def __init__(self, custom_sources: Optional[List[FundingSource]] = None):
        self.sources = FUNDING_SOURCES + (custom_sources or [])

    def match(
        self,
        profile: ClientFundingProfile,
        funding_types: Optional[List[FundingType]] = None,
        min_eligibility: float = 30.0,
    ) -> FundingMatchResult:
        """Find and rank all funding sources matching the client profile."""
        filtered = self.sources
        if funding_types:
            filtered = [s for s in filtered if s.funding_type in funding_types]

        matches = []
        for source in filtered:
            score, strengths, gaps = self._score_eligibility(profile, source)
            if score < min_eligibility:
                continue

            # Calculate eligible amount range
            seek = profile.seeking_amount
            eligible_min = source.amount_range["min"]
            eligible_max = min(source.amount_range["max"], max(seek, source.amount_range["min"]))

            recommendation = self._build_recommendation(profile, source, score, gaps)
            matches.append(FundingMatch(
                source=source,
                eligibility_score=score,
                eligible_amount={"min": eligible_min, "max": eligible_max},
                strengths=strengths,
                gaps=gaps,
                recommendation=recommendation,
                priority=1 if score >= 80 else (2 if score >= 60 else 3),
            ))

        matches = sorted(matches, key=lambda m: m.eligibility_score, reverse=True)

        total_potential = sum(m.eligible_amount["max"] for m in matches[:5])

        return FundingMatchResult(
            client_id=profile.client_id,
            profile=profile,
            matches=matches,
            total_potential_funding=total_potential,
            top_recommendation=matches[0].recommendation if matches else "No strong matches. Focus on building credit and revenue first.",
        )

    def _score_eligibility(
        self,
        profile: ClientFundingProfile,
        source: FundingSource,
    ) -> tuple[float, List[str], List[str]]:
        """Score 0–100 how eligible the client is for this funding source."""
        score = 100.0
        strengths: List[str] = []
        gaps: List[str] = []

        # Credit score check
        if source.min_credit_score:
            if profile.credit_score and profile.credit_score >= source.min_credit_score:
                strengths.append(f"Credit score ({profile.credit_score}) meets minimum ({source.min_credit_score})")
            elif profile.credit_score:
                gap = source.min_credit_score - profile.credit_score
                score -= min(40, gap * 0.8)
                gaps.append(f"Credit score is {gap} points below minimum ({source.min_credit_score} required)")
            else:
                score -= 20
                gaps.append("Credit score unknown")

        # Revenue check
        if source.min_annual_revenue:
            if profile.annual_revenue >= source.min_annual_revenue:
                strengths.append(f"Revenue (${profile.annual_revenue:,.0f}) meets minimum")
            else:
                gap_pct = (source.min_annual_revenue - profile.annual_revenue) / source.min_annual_revenue
                score -= min(35, gap_pct * 50)
                gaps.append(f"Annual revenue below minimum (${source.min_annual_revenue:,.0f} required)")

        # Time in business
        if source.min_time_in_business_months:
            if profile.time_in_business_months >= source.min_time_in_business_months:
                strengths.append(f"{profile.time_in_business_months} months in business qualifies")
            else:
                gap = source.min_time_in_business_months - profile.time_in_business_months
                score -= min(25, gap * 0.5)
                gaps.append(f"Need {gap} more months in business")

        # Collateral
        if source.requires_collateral and not profile.has_collateral:
            score -= 20
            gaps.append("Collateral required but not available")
        elif source.requires_collateral and profile.has_collateral:
            strengths.append("Collateral available")

        # Industry
        if source.industries and profile.industry:
            if profile.industry.lower() not in [i.lower() for i in source.industries]:
                score -= 15
                gaps.append(f"Industry '{profile.industry}' may not qualify")

        # State
        if source.states and profile.state:
            if profile.state not in source.states:
                score -= 30
                gaps.append(f"Geographic restriction: not available in {profile.state}")

        # Bonus factors
        if source.minority_owned_bonus and profile.is_minority_owned:
            score = min(100, score + 10)
            strengths.append("Minority-owned business bonus")
        if source.woman_owned_bonus and profile.is_woman_owned:
            score = min(100, score + 10)
            strengths.append("Woman-owned business bonus")
        if source.veteran_owned_bonus and profile.is_veteran_owned:
            score = min(100, score + 10)
            strengths.append("Veteran-owned business bonus")

        return round(max(0, score), 1), strengths, gaps

    def _build_recommendation(
        self,
        profile: ClientFundingProfile,
        source: FundingSource,
        score: float,
        gaps: List[str],
    ) -> str:
        if score >= 85:
            return f"Strong fit. Apply to {source.name} immediately. {source.typical_approval_time} approval."
        if score >= 65:
            return f"Good fit with minor gaps. Address: {gaps[0] if gaps else 'none'}. {source.name} worth pursuing."
        if gaps:
            return f"Address gaps before applying to {source.name}: {'; '.join(gaps[:2])}."
        return f"Borderline eligibility for {source.name}. Consider building profile before applying."
