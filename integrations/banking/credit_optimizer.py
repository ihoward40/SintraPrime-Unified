"""
Credit Optimizer — Actionable credit score improvement plans with rapid rescore strategies.
Targets mortgage approval, credit card upgrades, and rate reduction.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .credit_intelligence import CreditReport, CreditAccount

logger = logging.getLogger(__name__)


class OptimizationGoal(str, Enum):
    MORTGAGE_APPROVAL = "mortgage_approval"
    AUTO_LOAN_BEST_RATE = "auto_loan_best_rate"
    CREDIT_CARD_UPGRADE = "credit_card_upgrade"
    PERSONAL_LOAN = "personal_loan"
    GENERAL_IMPROVEMENT = "general_improvement"
    RAPID_RESCORE = "rapid_rescore"


class CreditAction(BaseModel):
    priority: int
    action_type: str
    title: str
    description: str
    estimated_point_gain: str
    timeline_days: int
    difficulty: str  # "easy", "moderate", "difficult"
    cost: str  # "free", "low", "moderate"
    is_rapid_rescore_eligible: bool = False


class BalanceTransferOpportunity(BaseModel):
    from_card_name: str
    from_apr: float
    from_balance: float
    to_offer: str
    to_intro_apr: float
    to_intro_months: int
    transfer_fee_pct: float
    interest_savings: float
    net_benefit: float
    recommended: bool


class CreditOptimizationPlan(BaseModel):
    client_id: str
    current_score: Optional[int]
    goal: OptimizationGoal
    target_score: int
    estimated_days_to_target: int
    actions: List[CreditAction] = Field(default_factory=list)
    balance_transfers: List[BalanceTransferOpportunity] = Field(default_factory=list)
    rapid_rescore_eligible: bool = False
    rapid_rescore_actions: List[str] = Field(default_factory=list)
    authorized_user_strategy: Optional[str] = None
    dispute_strategy: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Benchmark scores for goals
GOAL_TARGET_SCORES = {
    OptimizationGoal.MORTGAGE_APPROVAL: 740,
    OptimizationGoal.AUTO_LOAN_BEST_RATE: 700,
    OptimizationGoal.CREDIT_CARD_UPGRADE: 720,
    OptimizationGoal.PERSONAL_LOAN: 680,
    OptimizationGoal.GENERAL_IMPROVEMENT: 750,
    OptimizationGoal.RAPID_RESCORE: 700,
}


class CreditOptimizer:
    """
    Generates precise, prioritized credit score improvement plans.
    """

    def create_plan(
        self,
        client_id: str,
        report: CreditReport,
        goal: OptimizationGoal = OptimizationGoal.GENERAL_IMPROVEMENT,
    ) -> CreditOptimizationPlan:
        """Generate an optimized credit improvement plan for a specific goal."""
        current = report.credit_score or 620
        target = GOAL_TARGET_SCORES.get(goal, 750)
        gap = max(0, target - current)

        actions = self._build_actions(report, goal, current, target)
        balance_transfers = self._identify_balance_transfers(
            [a for a in report.accounts if a.account_type == "credit_card"]
        )

        # Rapid rescore eligibility (typically used before mortgage closing)
        is_rapid_eligible = goal == OptimizationGoal.MORTGAGE_APPROVAL and current >= 620
        rapid_actions = self._rapid_rescore_actions(report) if is_rapid_eligible else []

        # Estimated timeline
        max_monthly_gain = 25  # realistic max without rapid rescore
        if goal == OptimizationGoal.RAPID_RESCORE:
            days_to_target = 30
        else:
            days_to_target = int((gap / max_monthly_gain) * 30) if gap > 0 else 0

        return CreditOptimizationPlan(
            client_id=client_id,
            current_score=current,
            goal=goal,
            target_score=target,
            estimated_days_to_target=days_to_target,
            actions=actions,
            balance_transfers=balance_transfers,
            rapid_rescore_eligible=is_rapid_eligible,
            rapid_rescore_actions=rapid_actions,
            authorized_user_strategy=self._authorized_user_strategy(report, current),
            dispute_strategy=self._dispute_strategy(report),
        )

    def _build_actions(
        self,
        report: CreditReport,
        goal: OptimizationGoal,
        current: int,
        target: int,
    ) -> List[CreditAction]:
        actions = []
        priority = 1

        # 1. Pay down utilization — biggest bang for buck
        high_util_cards = [
            a for a in report.accounts
            if a.account_type == "credit_card" and (a.utilization or 0) > 0.30
        ]
        if high_util_cards or report.total_utilization > 0.30:
            actions.append(CreditAction(
                priority=priority,
                action_type="reduce_utilization",
                title="Pay down credit card balances to below 10%",
                description=(
                    f"Your total utilization is {report.total_utilization*100:.0f}%. "
                    f"Dropping below 10% is worth 20–50 points. "
                    f"Pay the highest-utilization cards first."
                ),
                estimated_point_gain="+20–50 points",
                timeline_days=30,
                difficulty="moderate",
                cost="free",
                is_rapid_rescore_eligible=True,
            ))
            priority += 1

        # 2. Set up autopay
        if report.total_missed_payments > 0:
            actions.append(CreditAction(
                priority=priority,
                action_type="autopay",
                title="Set up autopay for all accounts",
                description="Payment history is 35% of your score. One missed payment can drop your score 60–110 points. Enable autopay for at least the minimum payment.",
                estimated_point_gain="+5–15 points per on-time payment month",
                timeline_days=7,
                difficulty="easy",
                cost="free",
            ))
            priority += 1

        # 3. Request credit limit increases
        if report.total_utilization > 0.20:
            actions.append(CreditAction(
                priority=priority,
                action_type="credit_limit_increase",
                title="Request credit limit increases",
                description=(
                    "Call each credit card issuer and request a limit increase. "
                    "Higher limits reduce your utilization ratio instantly (if you don't spend more). "
                    "Best results if you've had the card 6+ months and have good payment history."
                ),
                estimated_point_gain="+10–30 points",
                timeline_days=14,
                difficulty="easy",
                cost="free",
                is_rapid_rescore_eligible=True,
            ))
            priority += 1

        # 4. Dispute errors
        if report.derogatory_marks > 0:
            actions.append(CreditAction(
                priority=priority,
                action_type="dispute_errors",
                title="Dispute inaccurate negative items",
                description=(
                    "Under the FCRA, you can dispute any inaccurate item. "
                    "Bureaus must investigate within 30 days. "
                    "Unverifiable items must be removed — even legitimate negatives sometimes get deleted."
                ),
                estimated_point_gain="+20–100 points per removal",
                timeline_days=45,
                difficulty="moderate",
                cost="free",
                is_rapid_rescore_eligible=False,
            ))
            priority += 1

        # 5. Don't close old accounts
        if report.average_account_age_months < 60:
            actions.append(CreditAction(
                priority=priority,
                action_type="preserve_old_accounts",
                title="Keep oldest accounts open",
                description=(
                    "Closing old accounts reduces your average credit age and available credit. "
                    "Even a $0-balance card should stay open if it has no annual fee. "
                    "Use it for a small purchase every few months to keep it active."
                ),
                estimated_point_gain="+5–20 points over 12 months",
                timeline_days=365,
                difficulty="easy",
                cost="free",
            ))
            priority += 1

        # 6. Mortgage-specific: Get inquiry clustering right
        if goal == OptimizationGoal.MORTGAGE_APPROVAL:
            actions.append(CreditAction(
                priority=priority,
                action_type="mortgage_prep",
                title="Shop mortgage rates within 14-day window",
                description=(
                    "Multiple mortgage inquiries within 14–45 days count as a single inquiry in FICO. "
                    "Compare rates from 3–5 lenders in one week. "
                    "Also: do NOT open or close any accounts in the 3 months before closing."
                ),
                estimated_point_gain="Prevents -5 to -10 per inquiry",
                timeline_days=14,
                difficulty="easy",
                cost="free",
            ))
            priority += 1

        # 7. Become an authorized user
        if current < 680:
            actions.append(CreditAction(
                priority=priority,
                action_type="authorized_user",
                title="Become authorized user on a family member's old, low-utilization card",
                description=(
                    "You inherit the account history as an authorized user. "
                    "Find a family member with a 5+ year account, perfect payment history, and <10% utilization. "
                    "You don't even need the physical card."
                ),
                estimated_point_gain="+10–40 points",
                timeline_days=60,
                difficulty="easy",
                cost="free",
            ))
            priority += 1

        return sorted(actions, key=lambda a: a.priority)

    def _identify_balance_transfers(
        self, cc_accounts: List[CreditAccount]
    ) -> List[BalanceTransferOpportunity]:
        """Identify beneficial balance transfer opportunities."""
        high_rate_cards = [
            a for a in cc_accounts
            if (a.apr or 0) > 0.18 and a.current_balance > 500
        ]
        opportunities = []
        for card in high_rate_cards:
            # Standard 0% intro BT offer (18 months, 3% fee)
            intro_months = 18
            transfer_fee = card.current_balance * 0.03
            interest_at_current = card.current_balance * (card.apr or 0.22) * (intro_months / 12)
            net_benefit = interest_at_current - transfer_fee

            opportunities.append(BalanceTransferOpportunity(
                from_card_name=card.name,
                from_apr=(card.apr or 0.22),
                from_balance=card.current_balance,
                to_offer="Wells Fargo Reflect / Citi Diamond Preferred (0% intro)",
                to_intro_apr=0.0,
                to_intro_months=intro_months,
                transfer_fee_pct=0.03,
                interest_savings=round(interest_at_current, 2),
                net_benefit=round(net_benefit, 2),
                recommended=net_benefit > 100,
            ))
        return [o for o in opportunities if o.recommended]

    def _rapid_rescore_actions(self, report: CreditReport) -> List[str]:
        """Actions for rapid rescore (30-day turnaround for mortgage closings)."""
        actions = []
        for acct in report.accounts:
            if acct.account_type == "credit_card" and (acct.utilization or 0) > 0.10:
                target = (acct.credit_limit or 0) * 0.09
                paydown = max(0, acct.current_balance - target)
                actions.append(
                    f"Pay ${paydown:,.0f} on {acct.name} → ask lender to rapid rescore once confirmed paid."
                )
        actions.append("Request rapid rescore through your mortgage officer after each paydown. Cost: ~$25–50 per bureau per account.")
        actions.append("Target: complete all paydowns in one cycle for maximum impact before closing date.")
        return actions[:5]

    def _authorized_user_strategy(
        self, report: CreditReport, current_score: int
    ) -> Optional[str]:
        if current_score >= 720:
            return None
        return (
            "Authorized User Strategy: Ask a parent, sibling, or spouse with an account older than 5 years, "
            "utilization below 10%, and a perfect payment record to add you as an authorized user. "
            "You'll likely see a 10–40 point gain within 1–2 statement cycles. "
            "You don't need to use or even receive the physical card."
        )

    def _dispute_strategy(self, report: CreditReport) -> Optional[str]:
        if report.derogatory_marks == 0:
            return None
        return (
            "Dispute Strategy: Pull your free credit reports from AnnualCreditReport.com. "
            "Identify any errors, outdated items (>7 years old), or unverifiable accounts. "
            "File disputes online at Equifax.com, Experian.com, and TransUnion.com. "
            "Bureaus have 30 days to investigate. If unverifiable, items must be removed. "
            "For collection accounts, request 'pay-for-delete' agreements in writing before paying."
        )
