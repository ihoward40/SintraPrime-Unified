"""
Wealth Builder — Personalized wealth-building roadmap with milestone tracking.
Generates staged action plans based on current financial position.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WealthStage(str, Enum):
    SURVIVE = "survive"          # Paycheck to paycheck, negative cash flow
    STABILIZE = "stabilize"      # Breaking even, building emergency fund
    GROW = "grow"                # Positive savings, starting to invest
    ACCELERATE = "accelerate"    # Debt free (non-mortgage), aggressively investing
    PRESERVE = "preserve"        # High net worth, wealth preservation focus
    LEGACY = "legacy"            # Estate planning, generational wealth


class WealthMilestone(BaseModel):
    milestone_id: str
    stage: WealthStage
    title: str
    description: str
    target_metric: str
    current_value: float
    target_value: float
    completion_pct: float = 0.0
    is_complete: bool = False
    estimated_months: Optional[int] = None
    actions: List[str] = Field(default_factory=list)


class WealthRoadmap(BaseModel):
    client_id: str
    current_stage: WealthStage
    stage_description: str
    current_net_worth: float
    current_monthly_surplus: float
    milestones: List[WealthMilestone] = Field(default_factory=list)
    next_3_actions: List[str] = Field(default_factory=list)
    projected_net_worth_5yr: float = 0.0
    projected_net_worth_10yr: float = 0.0
    wealth_velocity: float = 0.0  # Monthly net worth growth rate
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WealthBuilder:
    """
    Generates a personalized, stage-based wealth-building roadmap.
    """

    STAGE_THRESHOLDS = [
        (WealthStage.SURVIVE, float("-inf"), 0),
        (WealthStage.STABILIZE, 0, 1_000),
        (WealthStage.GROW, 1_000, 50_000),
        (WealthStage.ACCELERATE, 50_000, 500_000),
        (WealthStage.PRESERVE, 500_000, 2_000_000),
        (WealthStage.LEGACY, 2_000_000, float("inf")),
    ]

    STAGE_DESCRIPTIONS = {
        WealthStage.SURVIVE: "You're covering essentials but have little margin. Focus: stop bleeding, create margin.",
        WealthStage.STABILIZE: "You have basic stability. Focus: emergency fund, eliminate high-interest debt.",
        WealthStage.GROW: "Positive cash flow. Focus: invest consistently, eliminate all consumer debt.",
        WealthStage.ACCELERATE: "Debt-free momentum. Focus: max investment accounts, increase income streams.",
        WealthStage.PRESERVE: "Significant net worth. Focus: diversify, protect assets, optimize taxes.",
        WealthStage.LEGACY: "Financial independence achieved. Focus: estate planning, generational wealth.",
    }

    def build_roadmap(
        self,
        client_id: str,
        net_worth: float,
        monthly_income: float,
        monthly_expenses: float,
        monthly_debt_payments: float,
        emergency_fund_months: float,
        high_interest_debt: float,
        consumer_debt: float,
        retirement_balance: float,
        age: int,
    ) -> WealthRoadmap:
        """Generate a personalized wealth-building roadmap."""
        monthly_surplus = monthly_income - monthly_expenses
        stage = self._determine_stage(net_worth, monthly_surplus)

        milestones = self._build_milestones(
            stage=stage,
            net_worth=net_worth,
            monthly_income=monthly_income,
            monthly_surplus=monthly_surplus,
            emergency_fund_months=emergency_fund_months,
            high_interest_debt=high_interest_debt,
            consumer_debt=consumer_debt,
            retirement_balance=retirement_balance,
            age=age,
        )

        next_actions = self._immediate_actions(stage, milestones)

        # Project net worth growth (simplified: compound at 7% investments + surplus)
        nw_5yr = self._project_net_worth(net_worth, monthly_surplus, years=5)
        nw_10yr = self._project_net_worth(net_worth, monthly_surplus, years=10)

        return WealthRoadmap(
            client_id=client_id,
            current_stage=stage,
            stage_description=self.STAGE_DESCRIPTIONS[stage],
            current_net_worth=net_worth,
            current_monthly_surplus=monthly_surplus,
            milestones=milestones,
            next_3_actions=next_actions[:3],
            projected_net_worth_5yr=nw_5yr,
            projected_net_worth_10yr=nw_10yr,
            wealth_velocity=monthly_surplus,
        )

    def _determine_stage(self, net_worth: float, monthly_surplus: float) -> WealthStage:
        if monthly_surplus < 0:
            return WealthStage.SURVIVE
        if net_worth >= 2_000_000:
            return WealthStage.LEGACY
        if net_worth >= 500_000:
            return WealthStage.PRESERVE
        if net_worth >= 50_000:
            return WealthStage.ACCELERATE
        if monthly_surplus > 0 and net_worth >= 1_000:
            return WealthStage.GROW
        if monthly_surplus >= 0:
            return WealthStage.STABILIZE
        return WealthStage.SURVIVE

    def _build_milestones(self, **kwargs) -> List[WealthMilestone]:
        stage = kwargs["stage"]
        net_worth = kwargs["net_worth"]
        monthly_income = kwargs["monthly_income"]
        monthly_surplus = kwargs["monthly_surplus"]
        ef_months = kwargs["emergency_fund_months"]
        hi_debt = kwargs["high_interest_debt"]
        consumer_debt = kwargs["consumer_debt"]
        retirement = kwargs["retirement_balance"]
        age = kwargs["age"]

        milestones = []

        # M1: $1,000 emergency starter
        m1_done = net_worth >= 1_000 and ef_months > 0
        milestones.append(WealthMilestone(
            milestone_id="M1",
            stage=WealthStage.STABILIZE,
            title="$1,000 Emergency Starter Fund",
            description="Your first safety net. Stops the cycle of debt for emergencies.",
            target_metric="emergency_fund_dollars",
            current_value=min(net_worth, 1_000) if net_worth > 0 else 0,
            target_value=1_000,
            completion_pct=min(100, max(0, (min(net_worth, 1_000) / 1_000 * 100)) if net_worth > 0 else 0),
            is_complete=m1_done,
            estimated_months=int(1_000 / max(monthly_surplus, 1)) if not m1_done else 0,
            actions=["Open a separate high-yield savings account.", "Auto-transfer $100/week until you reach $1,000."],
        ))

        # M2: Kill high-interest debt
        m2_done = hi_debt <= 0
        milestones.append(WealthMilestone(
            milestone_id="M2",
            stage=WealthStage.STABILIZE,
            title="Eliminate High-Interest Debt (>15% APR)",
            description="High-interest debt is the #1 wealth destroyer. Kill it with prejudice.",
            target_metric="high_interest_debt",
            current_value=hi_debt,
            target_value=0,
            completion_pct=100 if m2_done else 0,
            is_complete=m2_done,
            estimated_months=int(hi_debt / max(monthly_surplus * 0.7, 1)) if not m2_done else 0,
            actions=["List all debts over 15% APR.", "Use avalanche method — pay minimums on all, attack highest rate first."],
        ))

        # M3: Full emergency fund (6 months)
        monthly_expenses = monthly_income - monthly_surplus
        ef_target = monthly_expenses * 6
        ef_current = ef_months * monthly_expenses
        m3_done = ef_months >= 6
        milestones.append(WealthMilestone(
            milestone_id="M3",
            stage=WealthStage.GROW,
            title="6-Month Emergency Fund",
            description="Full financial safety net. Protects against job loss, medical crisis, car breakdown.",
            target_metric="emergency_fund_months",
            current_value=ef_months,
            target_value=6.0,
            completion_pct=min(100, ef_months / 6 * 100),
            is_complete=m3_done,
            estimated_months=int((ef_target - ef_current) / max(monthly_surplus * 0.5, 1)) if not m3_done else 0,
            actions=["Auto-transfer 10% of each paycheck to emergency savings.", "Keep in high-yield savings (4%+ APY)."],
        ))

        # M4: Invest 15% of income
        inv_rate = (monthly_surplus * 0.75 / monthly_income) if monthly_income > 0 else 0
        m4_done = inv_rate >= 0.15
        milestones.append(WealthMilestone(
            milestone_id="M4",
            stage=WealthStage.GROW,
            title="Invest 15% of Income",
            description="Consistent investing is the engine of wealth. Time in market beats timing the market.",
            target_metric="investment_rate_pct",
            current_value=round(inv_rate * 100, 1),
            target_value=15.0,
            completion_pct=min(100, inv_rate / 0.15 * 100),
            is_complete=m4_done,
            actions=["Max employer 401k match first.", "Open Roth IRA and invest in low-cost index funds (VTSAX, VTI, SPY)."],
        ))

        # M5: Pay off all consumer debt
        m5_done = consumer_debt <= 0
        milestones.append(WealthMilestone(
            milestone_id="M5",
            stage=WealthStage.ACCELERATE,
            title="Eliminate All Consumer Debt",
            description="Zero consumer debt = full paycheck available to build wealth.",
            target_metric="consumer_debt",
            current_value=consumer_debt,
            target_value=0,
            completion_pct=100 if m5_done else 0,
            is_complete=m5_done,
            estimated_months=int(consumer_debt / max(monthly_surplus * 0.8, 1)) if not m5_done else 0,
            actions=["Snowball small debts for momentum.", "Direct all 'found money' (bonuses, tax refunds) to debt."],
        ))

        # M6: $100K net worth
        m6_done = net_worth >= 100_000
        milestones.append(WealthMilestone(
            milestone_id="M6",
            stage=WealthStage.ACCELERATE,
            title="$100,000 Net Worth",
            description="The first $100K is the hardest. Compound interest begins working seriously for you.",
            target_metric="net_worth",
            current_value=net_worth,
            target_value=100_000,
            completion_pct=min(100, max(0, net_worth / 100_000 * 100)),
            is_complete=m6_done,
            actions=["Max out 401k and Roth IRA annually.", "Keep lifestyle inflation below income growth."],
        ))

        # M7: Retirement on track (rule of thumb: 1x salary by 30, 3x by 40, etc.)
        salary_multiplier = max(0, (age - 20) / 10)
        ret_target = monthly_income * 12 * salary_multiplier
        m7_done = retirement >= ret_target
        milestones.append(WealthMilestone(
            milestone_id="M7",
            stage=WealthStage.ACCELERATE,
            title="Retirement on Track (Fidelity Guideline)",
            description=f"Target: {salary_multiplier:.0f}x annual salary in retirement accounts by age {age}.",
            target_metric="retirement_balance",
            current_value=retirement,
            target_value=ret_target,
            completion_pct=min(100, (retirement / ret_target * 100) if ret_target > 0 else 100),
            is_complete=m7_done,
            actions=["Max 401k ($23,000/yr) + IRA ($7,000/yr) = $30,000/year toward retirement.", "Catch-up contributions available at age 50."],
        ))

        return milestones

    def _immediate_actions(
        self, stage: WealthStage, milestones: List[WealthMilestone]
    ) -> List[str]:
        incomplete = [m for m in milestones if not m.is_complete]
        actions = []
        for m in incomplete[:2]:
            actions.extend(m.actions[:2])
        return actions[:3]

    def _project_net_worth(
        self, current_nw: float, monthly_surplus: float, years: int
    ) -> float:
        """Project net worth with compound growth on investments + surplus savings."""
        annual_growth_rate = 0.07
        months = years * 12
        # FV of existing portfolio
        portfolio = max(0, current_nw) * ((1 + annual_growth_rate) ** years)
        # FV of monthly surplus invested (annuity)
        if annual_growth_rate > 0:
            monthly_rate = annual_growth_rate / 12
            fv_contributions = monthly_surplus * ((((1 + monthly_rate) ** months) - 1) / monthly_rate)
        else:
            fv_contributions = monthly_surplus * months
        return round(portfolio + fv_contributions, 2)
