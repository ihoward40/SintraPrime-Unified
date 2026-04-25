"""
Credit Intelligence — Deep credit score analysis, improvement plans, and monitoring.
Pulls Plaid credit report data and generates actionable optimization strategies.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .plaid_client import PlaidClient

logger = logging.getLogger(__name__)


class CreditScoreTier(str, Enum):
    EXCEPTIONAL = "exceptional"   # 800+
    VERY_GOOD = "very_good"       # 740–799
    GOOD = "good"                 # 670–739
    FAIR = "fair"                 # 580–669
    POOR = "poor"                 # 300–579


class CreditScoreComponent(BaseModel):
    """Also known as CreditComponent."""
    name: str
    weight: float  # percentage weight in score
    current_score: float  # 0–100 sub-score
    status: str  # "excellent", "good", "fair", "poor"
    impact: str  # "high", "medium", "low"
    detail: str
    recommendation: Optional[str] = None


# Alias for backward compatibility
CreditComponent = CreditScoreComponent


class UtilizationTarget(BaseModel):
    account_name: str
    current_balance: float
    credit_limit: float
    target_balance: float
    paydown_needed: float


class CreditAccount(BaseModel):
    account_id: str
    name: str
    account_type: str  # "credit_card", "mortgage", "auto", "student", etc.
    current_balance: float
    credit_limit: Optional[float] = None
    utilization: Optional[float] = None  # 0.0–1.0
    payment_status: str  # "current", "late_30", "late_60", "late_90", "collection"
    open_date: Optional[date] = None
    last_payment_date: Optional[date] = None
    last_payment_amount: Optional[float] = None
    minimum_payment: Optional[float] = None
    apr: Optional[float] = None
    account_age_months: int = 0
    is_derogatory: bool = False


class CreditReport(BaseModel):
    client_id: str = "default"

    @model_validator(mode='after')
    def _compute_score_tier(self):
        """Auto-compute score_tier from credit_score."""
        if self.credit_score is not None:
            for low, high, tier in [
                (800, 850, CreditScoreTier.EXCEPTIONAL),
                (740, 799, CreditScoreTier.VERY_GOOD),
                (670, 739, CreditScoreTier.GOOD),
                (580, 669, CreditScoreTier.FAIR),
                (300, 579, CreditScoreTier.POOR),
            ]:
                if low <= self.credit_score <= high:
                    self.score_tier = tier
                    break
        return self
    credit_score: Optional[int] = None
    score_model: str = "FICO 8"
    score_tier: Optional[CreditScoreTier] = None
    accounts: List[CreditAccount] = Field(default_factory=list)
    total_utilization: float = 0.0
    oldest_account_age_months: int = 0
    average_account_age_months: float = 0.0
    total_missed_payments: int = 0
    recent_inquiries: int = 0  # last 24 months
    account_mix_score: float = 0.0
    components: List[CreditScoreComponent] = Field(default_factory=list)
    derogatory_marks: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CreditImprovementAction(BaseModel):
    priority: int  # 1 = highest
    action: str
    expected_impact: str  # "+20–30 points", etc.
    timeline: str  # "30 days", "3 months", etc.
    effort: str  # "easy", "moderate", "difficult"
    detail: str


class CreditImprovementPlan(BaseModel):
    current_score: Optional[int]
    target_score: int
    estimated_months: int
    actions: List[CreditImprovementAction] = Field(default_factory=list)
    balance_optimization: List[Dict[str, Any]] = Field(default_factory=list)
    dispute_items: List[Dict[str, Any]] = Field(default_factory=list)
    authorized_user_recommendation: Optional[str] = None


class CreditMonitoringAlert(BaseModel):
    alert_type: str  # "score_change", "new_inquiry", "late_payment_risk", etc.
    severity: str  # "info", "warning", "critical"
    message: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    account_id: Optional[str] = None
    recommended_action: Optional[str] = None


class CreditIntelligence:
    """
    Credit score analysis engine for SintraPrime.
    Ingests Plaid credit/liability data to produce actionable credit improvement plans.
    """

    SCORE_TIER_RANGES = [
        (800, 850, CreditScoreTier.EXCEPTIONAL),
        (740, 799, CreditScoreTier.VERY_GOOD),
        (670, 739, CreditScoreTier.GOOD),
        (580, 669, CreditScoreTier.FAIR),
        (300, 579, CreditScoreTier.POOR),
    ]

    def __init__(self, plaid_client: Optional[PlaidClient] = None):
        self.client = plaid_client

    # ── Score Analysis ─────────────────────────────────────────────────────

    def _get_score_tier(self, score: int) -> CreditScoreTier:
        for low, high, tier in self.SCORE_TIER_RANGES:
            if low <= score <= high:
                return tier
        return CreditScoreTier.POOR

    def analyze_report(
        self,
        client_id: str,
        credit_score: Optional[int],
        plaid_liabilities: Dict[str, Any],
    ) -> CreditReport:
        """Build a full CreditReport from Plaid liabilities data."""
        accounts: List[CreditAccount] = []
        credit_accounts = plaid_liabilities.get("credit", [])
        mortgage_accounts = plaid_liabilities.get("mortgage", [])
        student_accounts = plaid_liabilities.get("student", [])
        all_raw_accounts = plaid_liabilities.get("accounts", [])

        # Map account_id → account name from accounts list
        acct_name_map = {a["account_id"]: a.get("name", "Unknown") for a in all_raw_accounts}

        # Credit cards
        for cc in credit_accounts:
            bal = cc.get("last_statement_balance") or 0.0
            limit = cc.get("credit_limit") or 0.0
            util = (bal / limit) if limit > 0 else 0.0
            last_payment = cc.get("last_payment_amount", 0)
            is_late = bal > 0 and not last_payment
            acct = CreditAccount(
                account_id=cc.get("account_id", ""),
                name=acct_name_map.get(cc.get("account_id", ""), "Credit Card"),
                account_type="credit_card",
                current_balance=bal,
                credit_limit=limit,
                utilization=round(util, 3),
                payment_status="current" if not is_late else "late_30",
                last_payment_amount=last_payment,
                minimum_payment=cc.get("minimum_payment_amount"),
                apr=cc.get("aprs", [{}])[0].get("apr_percentage") if cc.get("aprs") else None,
            )
            accounts.append(acct)

        # Mortgages
        for mort in mortgage_accounts:
            accounts.append(CreditAccount(
                account_id=mort.get("account_id", ""),
                name=acct_name_map.get(mort.get("account_id", ""), "Mortgage"),
                account_type="mortgage",
                current_balance=mort.get("current_outstanding_principal_balance") or 0.0,
                payment_status="current",
                last_payment_date=mort.get("last_payment_date"),
                last_payment_amount=mort.get("last_payment_amount"),
                minimum_payment=mort.get("next_monthly_payment"),
                open_date=mort.get("origination_date"),
            ))

        # Student loans
        for sl in student_accounts:
            accounts.append(CreditAccount(
                account_id=sl.get("account_id", ""),
                name=acct_name_map.get(sl.get("account_id", ""), "Student Loan"),
                account_type="student",
                current_balance=sl.get("outstanding_interest_amount", 0) + sl.get("principal_balance", {}).get("amount", 0),
                payment_status="current",
                minimum_payment=sl.get("minimum_payment_amount"),
            ))

        # Calculate aggregate metrics
        cc_accts = [a for a in accounts if a.account_type == "credit_card"]
        total_balance = sum(a.current_balance for a in cc_accts)
        total_limit = sum(a.credit_limit or 0 for a in cc_accts)
        total_utilization = (total_balance / total_limit) if total_limit > 0 else 0.0
        missed_payments = sum(1 for a in accounts if a.payment_status != "current")
        derogatory = sum(1 for a in accounts if a.is_derogatory)

        # Age calculations (simplified without full tradeline data)
        oldest_age = 120  # placeholder: 10 years
        avg_age = 60      # placeholder: 5 years

        components = self._analyze_components(
            score=credit_score,
            utilization=total_utilization,
            missed_payments=missed_payments,
            oldest_age_months=oldest_age,
            average_age_months=avg_age,
            account_types=list({a.account_type for a in accounts}),
            recent_inquiries=0,
        )

        report = CreditReport(
            client_id=client_id,
            credit_score=credit_score,
            score_tier=self._get_score_tier(credit_score) if credit_score else None,
            accounts=accounts,
            total_utilization=round(total_utilization, 3),
            oldest_account_age_months=oldest_age,
            average_account_age_months=avg_age,
            total_missed_payments=missed_payments,
            recent_inquiries=0,
            derogatory_marks=derogatory,
            components=components,
        )
        return report

    def _analyze_components(
        self,
        score: Optional[int],
        utilization: float,
        missed_payments: int,
        oldest_age_months: int,
        average_age_months: float,
        account_types: List[str],
        recent_inquiries: int,
    ) -> List[CreditScoreComponent]:
        """Analyze each FICO component and produce sub-scores."""
        components = []

        # 1. Payment history (35%)
        ph_score = max(0, 100 - (missed_payments * 30))
        components.append(CreditScoreComponent(
            name="Payment History",
            weight=35.0,
            current_score=ph_score,
            status="excellent" if ph_score >= 90 else ("good" if ph_score >= 70 else ("fair" if ph_score >= 50 else "poor")),
            impact="high",
            detail=f"{missed_payments} missed payment(s) detected",
            recommendation="Set up autopay for all accounts to prevent missed payments" if missed_payments > 0 else None,
        ))

        # 2. Credit utilization (30%)
        util_pct = utilization * 100
        util_score = max(0, 100 - max(0, (util_pct - 10) * 2))
        components.append(CreditScoreComponent(
            name="Credit Utilization",
            weight=30.0,
            current_score=round(util_score, 1),
            status="excellent" if util_pct < 10 else ("good" if util_pct < 30 else ("fair" if util_pct < 50 else "poor")),
            impact="high",
            detail=f"Current utilization: {util_pct:.1f}% (target < 10%)",
            recommendation="Pay down balances to below 10% per card" if util_pct >= 10 else None,
        ))

        # 3. Credit age (15%)
        age_score = min(100, (oldest_age_months / 240) * 100)  # max at 20 years
        components.append(CreditScoreComponent(
            name="Credit Age",
            weight=15.0,
            current_score=round(age_score, 1),
            status="excellent" if oldest_age_months >= 120 else ("good" if oldest_age_months >= 60 else "fair"),
            impact="medium",
            detail=f"Oldest account: {oldest_age_months // 12}yr {oldest_age_months % 12}mo | Average age: {average_age_months:.0f}mo",
            recommendation="Do not close old accounts; they extend your average age" if average_age_months < 48 else None,
        ))

        # 4. Credit mix (10%)
        mix_types = len(account_types)
        mix_score = min(100, mix_types * 25)
        components.append(CreditScoreComponent(
            name="Credit Mix",
            weight=10.0,
            current_score=mix_score,
            status="excellent" if mix_types >= 4 else ("good" if mix_types >= 2 else "fair"),
            impact="low",
            detail=f"Account types: {', '.join(account_types) or 'none detected'}",
            recommendation="A healthy mix includes credit cards, auto, and installment loans" if mix_types < 2 else None,
        ))

        # 5. New credit / inquiries (10%)
        inq_score = max(0, 100 - (recent_inquiries * 10))
        components.append(CreditScoreComponent(
            name="New Credit",
            weight=10.0,
            current_score=inq_score,
            status="excellent" if recent_inquiries == 0 else ("good" if recent_inquiries <= 2 else "fair"),
            impact="low",
            detail=f"{recent_inquiries} hard inquiry(ies) in last 24 months",
            recommendation="Avoid applying for new credit for the next 6 months" if recent_inquiries >= 3 else None,
        ))

        return components

    # ── Improvement Plan ───────────────────────────────────────────────────

    def create_improvement_plan(
        self,
        report: CreditReport,
        target_score: int = 750,
    ) -> CreditImprovementPlan:
        """Generate a prioritized credit improvement plan."""
        current = report.credit_score or 600
        gap = max(0, target_score - current)
        actions: List[CreditImprovementAction] = []
        priority = 1

        # Utilization actions
        if report.total_utilization > 0.10:
            cc_accts = sorted(
                [a for a in report.accounts if a.account_type == "credit_card"],
                key=lambda a: a.utilization or 0,
                reverse=True,
            )
            for cc in cc_accts[:3]:
                if (cc.utilization or 0) > 0.10:
                    target_balance = (cc.credit_limit or 0) * 0.09
                    paydown = max(0, cc.current_balance - target_balance)
                    actions.append(CreditImprovementAction(
                        priority=priority,
                        action=f"Pay down {cc.name} by ${paydown:,.0f}",
                        expected_impact="+15–25 points",
                        timeline="30 days",
                        effort="moderate",
                        detail=f"Current utilization: {(cc.utilization or 0)*100:.0f}%. Target: 9%",
                    ))
                    priority += 1

        # Payment history
        if report.total_missed_payments > 0:
            actions.append(CreditImprovementAction(
                priority=priority,
                action="Set up autopay on all accounts",
                expected_impact="+10–40 points over 6 months",
                timeline="Immediate",
                effort="easy",
                detail="Payment history is 35% of your FICO score. Consistent on-time payments are critical.",
            ))
            priority += 1

        # Derogatory marks
        if report.derogatory_marks > 0:
            actions.append(CreditImprovementAction(
                priority=priority,
                action="Dispute inaccurate derogatory marks",
                expected_impact="+20–60 points per removal",
                timeline="30–60 days (dispute process)",
                effort="moderate",
                detail="Submit disputes to Equifax, Experian, and TransUnion via their online portals.",
            ))
            priority += 1

        # Credit age
        if report.average_account_age_months < 36:
            actions.append(CreditImprovementAction(
                priority=priority,
                action="Become an authorized user on a trusted family member's old account",
                expected_impact="+10–20 points",
                timeline="30–60 days",
                effort="easy",
                detail="You inherit the account age and payment history as an authorized user.",
            ))
            priority += 1

        # General improvement actions if gap exists and no specific actions yet
        if not actions and gap > 0:
            actions.append(CreditImprovementAction(
                priority=priority,
                action="Review and dispute any errors on your credit reports",
                expected_impact="+5–20 points",
                timeline="30–60 days",
                effort="easy",
                detail="Request free reports from AnnualCreditReport.com and check for inaccuracies.",
            ))
            priority += 1
            actions.append(CreditImprovementAction(
                priority=priority,
                action="Keep all credit card utilization below 10%",
                expected_impact="+10–30 points",
                timeline="30 days",
                effort="moderate",
                detail="Pay down balances before statement close dates.",
            ))
            priority += 1

        # Balance optimization for quick wins
        balance_opt = self._optimize_card_balances(
            [a for a in report.accounts if a.account_type == "credit_card"]
        )

        estimated_months = max(1, gap // 15)  # rough estimate: ~15 pts/month achievable

        return CreditImprovementPlan(
            current_score=current,
            target_score=target_score,
            estimated_months=estimated_months,
            actions=actions,
            balance_optimization=balance_opt,
            authorized_user_recommendation=(
                "Ask a family member with 10+ year accounts, low utilization, and perfect payment history "
                "to add you as an authorized user. This is one of the fastest legitimate ways to boost your score."
                if report.average_account_age_months < 48 else None
            ),
        )

    def _optimize_card_balances(
        self, cc_accounts: List[CreditAccount]
    ) -> List[Dict[str, Any]]:
        """Recommend optimal balance distribution across credit cards."""
        return [
            {
                "account": a.name,
                "current_balance": a.current_balance,
                "current_utilization": f"{(a.utilization or 0)*100:.0f}%",
                "target_balance": round((a.credit_limit or 0) * 0.09, 2),
                "paydown_needed": round(max(0, a.current_balance - (a.credit_limit or 0) * 0.09), 2),
                "impact": "high" if (a.utilization or 0) > 0.50 else "medium",
            }
            for a in cc_accounts
            if (a.utilization or 0) > 0.09
        ]

    # ── Monitoring Alerts ──────────────────────────────────────────────────

    def generate_alerts(
        self,
        current_report: CreditReport,
        previous_report: Optional[CreditReport] = None,
    ) -> List[str]:
        """Generate credit monitoring alerts."""
        alerts: List[CreditMonitoringAlert] = []

        # Score change alert
        if previous_report and current_report.credit_score and previous_report.credit_score:
            delta = current_report.credit_score - previous_report.credit_score
            if abs(delta) >= 10:
                alerts.append(CreditMonitoringAlert(
                    alert_type="score_change",
                    severity="warning" if delta < 0 else "info",
                    message=f"Credit score changed {'+' if delta > 0 else ''}{delta} points to {current_report.credit_score}",
                    recommended_action="Review recent credit activity for the cause of this change." if delta < 0 else None,
                ))

        # High utilization alert
        for acct in current_report.accounts:
            if acct.account_type == "credit_card" and (acct.utilization or 0) > 0.80:
                alerts.append(CreditMonitoringAlert(
                    alert_type="high_utilization",
                    severity="critical",
                    message=f"{acct.name} is at {(acct.utilization or 0)*100:.0f}% utilization — critical impact on score",
                    account_id=acct.account_id,
                    recommended_action="Pay down this card immediately to below 30%, ideally below 10%.",
                ))

        # Missed payments
        if current_report.total_missed_payments and current_report.total_missed_payments > 0:
            alerts.append(CreditMonitoringAlert(
                alert_type="missed_payment",
                severity="critical",
                message=f"{current_report.total_missed_payments} missed payment(s) detected — this severely impacts your score",
                recommended_action="Set up autopay immediately and contact creditors about removing late marks.",
            ))

        # Late payment risk
        for acct in current_report.accounts:
            if acct.minimum_payment and acct.minimum_payment > 0 and not acct.last_payment_date:
                alerts.append(CreditMonitoringAlert(
                    alert_type="late_payment_risk",
                    severity="warning",
                    message=f"No recent payment detected on {acct.name}",
                    account_id=acct.account_id,
                    recommended_action="Make at least the minimum payment immediately to avoid a 30-day late mark.",
                ))

        # New inquiry — only alert when we have a previous report to compare against
        if previous_report and current_report.recent_inquiries > previous_report.recent_inquiries:
            alerts.append(CreditMonitoringAlert(
                alert_type="new_inquiry",
                severity="info",
                message=f"New hard inquiry detected. Total: {current_report.recent_inquiries}",
                recommended_action="If this inquiry was not authorized, file a dispute with the bureaus.",
            ))

        return [a.message for a in alerts]

    def generate_dispute_letter(
        self,
        client_name: str,
        dispute_item: str,
        creditor_name: str,
        account_number: str,
    ) -> str:
        """Generate a credit dispute letter template."""
        today = date.today().strftime("%B %d, %Y")
        return f"""
{client_name}
[Your Address]
[City, State, ZIP]
{today}

Credit Reporting Agency
[Address]

Re: Request for Investigation — Account #{account_number}

Dear Sir or Madam,

I am writing to dispute the following inaccurate information appearing on my credit report.
The account listed below is inaccurate and I request that it be investigated and corrected:

Creditor: {creditor_name}
Account Number: {account_number}
Dispute Reason: {dispute_item}

Please investigate this matter and provide me with a written response within 30 days as required
by the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681i. If you cannot verify this
information, please delete it from my credit report.

Enclosed: Copy of government-issued ID, utility bill (proof of address)

Sincerely,
{client_name}
""".strip()

    def compute_components(self, report: CreditReport) -> List[CreditScoreComponent]:
        """Wrapper around _analyze_components that takes a CreditReport."""
        account_types = list(set(a.account_type for a in report.accounts if a.account_type))
        return self._analyze_components(
            score=report.credit_score,
            utilization=report.total_utilization or 0,
            missed_payments=report.total_missed_payments or 0,
            oldest_age_months=report.oldest_account_age_months or 0,
            average_age_months=report.average_account_age_months or 0,
            account_types=account_types,
            recent_inquiries=report.recent_inquiries or 0,
        )

    def build_improvement_plan(self, report: CreditReport, target_score: int = 750) -> CreditImprovementPlan:
        """Alias for create_improvement_plan."""
        return self.create_improvement_plan(report, target_score)

    def utilization_optimizer(self, report: CreditReport, target_utilization: float = 0.10) -> List[UtilizationTarget]:
        """Optimize credit utilization across accounts."""
        results = []
        for a in report.accounts:
            if a.account_type == "credit_card" and a.credit_limit and (a.utilization or 0) > target_utilization:
                target_bal = round(a.credit_limit * target_utilization, 2)
                results.append(UtilizationTarget(
                    account_name=a.name,
                    current_balance=a.current_balance,
                    credit_limit=a.credit_limit,
                    target_balance=target_bal,
                    paydown_needed=round(max(0, a.current_balance - target_bal), 2),
                ))
        return results

