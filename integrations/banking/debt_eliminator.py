"""
Debt Eliminator — Avalanche, snowball, and hybrid debt payoff strategies with
side-by-side comparisons, impact analysis, and consolidation recommendations.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DebtStrategy(str, Enum):
    AVALANCHE = "avalanche"   # Highest interest rate first (mathematically optimal)
    SNOWBALL = "snowball"     # Lowest balance first (psychologically motivating)
    HYBRID = "hybrid"        # Snowball for small debts, avalanche for large


class DebtItem(BaseModel):
    debt_id: str
    name: str
    current_balance: float
    apr: float  # as decimal, e.g., 0.19 = 19%
    minimum_payment: float
    account_type: str = "credit_card"  # credit_card, auto, student, personal, mortgage
    lender: Optional[str] = None


class DebtPaymentMonth(BaseModel):
    month: int
    debt_id: str
    debt_name: str
    payment_applied: float
    principal_paid: float
    interest_paid: float
    balance_after: float
    is_payoff_month: bool = False


class DebtPayoffPlan(BaseModel):
    strategy: DebtStrategy
    total_months: int
    payoff_date: date
    total_interest_paid: float
    total_amount_paid: float
    debt_payoff_order: List[str]
    monthly_schedule: List[List[DebtPaymentMonth]] = Field(default_factory=list)  # grouped by month
    milestones: List[Dict[str, Any]] = Field(default_factory=list)


class StrategyComparison(BaseModel):
    avalanche: DebtPayoffPlan
    snowball: DebtPayoffPlan
    hybrid: Optional[DebtPayoffPlan] = None
    recommended_strategy: DebtStrategy
    interest_difference: float
    months_difference: int
    recommendation_reason: str


class ExtraPaymentImpact(BaseModel):
    extra_monthly: float
    months_saved: int
    interest_saved: float
    new_payoff_date: date


class ConsolidationAnalysis(BaseModel):
    current_weighted_apr: float
    current_total_monthly: float
    new_consolidated_apr: float
    new_monthly_payment: float
    monthly_savings: float
    interest_savings: float
    break_even_months: int
    recommended: bool
    notes: str


class DebtEliminationReport(BaseModel):
    client_id: str
    debts: List[DebtItem]
    total_debt: float
    weighted_average_apr: float
    minimum_monthly_total: float
    comparison: StrategyComparison
    extra_payment_impacts: List[ExtraPaymentImpact] = Field(default_factory=list)
    consolidation: Optional[ConsolidationAnalysis] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DebtEliminator:
    """
    Comprehensive debt payoff engine with multiple strategies and analysis tools.
    """

    def __init__(self):
        pass

    def analyze(
        self,
        client_id: str,
        debts: List[DebtItem],
        extra_monthly_payment: float = 0.0,
        analyze_consolidation: bool = True,
    ) -> DebtEliminationReport:
        """Generate full debt elimination analysis."""
        if not debts:
            raise ValueError("No debts provided")

        total_debt = sum(d.current_balance for d in debts)
        total_minimum = sum(d.minimum_payment for d in debts)
        weighted_apr = sum(d.current_balance * d.apr for d in debts) / total_debt if total_debt > 0 else 0

        monthly_payment = total_minimum + extra_monthly_payment

        avalanche = self._calculate_plan(debts, monthly_payment, DebtStrategy.AVALANCHE)
        snowball = self._calculate_plan(debts, monthly_payment, DebtStrategy.SNOWBALL)
        hybrid = self._calculate_plan(debts, monthly_payment, DebtStrategy.HYBRID)

        recommended, reason = self._recommend_strategy(avalanche, snowball, debts)

        comparison = StrategyComparison(
            avalanche=avalanche,
            snowball=snowball,
            hybrid=hybrid,
            recommended_strategy=recommended,
            interest_difference=round(snowball.total_interest_paid - avalanche.total_interest_paid, 2),
            months_difference=snowball.total_months - avalanche.total_months,
            recommendation_reason=reason,
        )

        # Extra payment impact analysis
        extra_impacts = []
        for extra in [100, 200, 500]:
            impact = self._extra_payment_impact(debts, monthly_payment, extra, recommended)
            extra_impacts.append(impact)

        # Consolidation analysis
        consolidation = None
        if analyze_consolidation and len(debts) >= 2:
            # Estimate consolidation rate as weighted APR - 4% (market discount)
            consolidation_apr = max(0.06, weighted_apr - 0.04)
            consolidation = self._analyze_consolidation(debts, total_debt, weighted_apr, consolidation_apr)

        return DebtEliminationReport(
            client_id=client_id,
            debts=debts,
            total_debt=round(total_debt, 2),
            weighted_average_apr=round(weighted_apr, 4),
            minimum_monthly_total=round(total_minimum, 2),
            comparison=comparison,
            extra_payment_impacts=extra_impacts,
            consolidation=consolidation,
        )

    def _calculate_plan(
        self,
        debts: List[DebtItem],
        total_monthly_payment: float,
        strategy: DebtStrategy,
    ) -> DebtPayoffPlan:
        """Simulate debt payoff for a given strategy."""
        # Sort debts by strategy
        sorted_debts = self._sort_debts(debts, strategy)

        # Working copies
        balances = {d.debt_id: d.current_balance for d in sorted_debts}
        minimums = {d.debt_id: d.minimum_payment for d in sorted_debts}
        rates = {d.debt_id: d.apr / 12 for d in sorted_debts}  # monthly rate

        payoff_order = []
        total_interest = 0.0
        total_paid = 0.0
        month = 0
        max_months = 600

        while any(b > 0.01 for b in balances.values()) and month < max_months:
            month += 1
            # Identify target debt (first in sorted order still with balance)
            active_sorted = [d for d in sorted_debts if balances.get(d.debt_id, 0) > 0.01]
            target = active_sorted[0] if active_sorted else None

            # Calculate minimum payments for all active debts
            monthly_interest = {
                did: balances[did] * rates[did]
                for did in balances if balances[did] > 0.01
            }
            total_minimums_this_month = sum(
                max(minimums[did], monthly_interest[did] + 0.01)
                for did in balances if balances[did] > 0.01
            )

            extra = max(0, total_monthly_payment - total_minimums_this_month)

            for debt in active_sorted:
                did = debt.debt_id
                balance = balances[did]
                if balance <= 0.01:
                    continue

                interest = balance * rates[did]
                total_interest += interest

                if target and did == target.debt_id:
                    payment = min(balance + interest, minimums[did] + extra)
                else:
                    payment = min(balance + interest, minimums[did])

                principal = payment - interest
                balances[did] = max(0, balance - principal)
                total_paid += payment

                if balances[did] < 0.01 and did not in payoff_order:
                    payoff_order.append(debt.name)
                    balances[did] = 0

        # Calculate payoff date
        payoff_month = date.today()
        from datetime import timedelta
        payoff_date = date(
            payoff_month.year + (payoff_month.month + month - 1) // 12,
            (payoff_month.month + month - 1) % 12 + 1,
            1,
        )

        milestones = [
            {"event": f"Paid off: {name}", "month": i * (month // max(len(payoff_order), 1))}
            for i, name in enumerate(payoff_order, 1)
        ]

        return DebtPayoffPlan(
            strategy=strategy,
            total_months=month,
            payoff_date=payoff_date,
            total_interest_paid=round(total_interest, 2),
            total_amount_paid=round(total_paid, 2),
            debt_payoff_order=payoff_order,
            milestones=milestones,
        )

    def _sort_debts(self, debts: List[DebtItem], strategy: DebtStrategy) -> List[DebtItem]:
        """Sort debts by the target strategy."""
        if strategy == DebtStrategy.AVALANCHE:
            return sorted(debts, key=lambda d: d.apr, reverse=True)
        if strategy == DebtStrategy.SNOWBALL:
            return sorted(debts, key=lambda d: d.current_balance)
        if strategy == DebtStrategy.HYBRID:
            # Snowball for balances < $2,000, avalanche for the rest
            small = sorted([d for d in debts if d.current_balance < 2_000], key=lambda d: d.current_balance)
            large = sorted([d for d in debts if d.current_balance >= 2_000], key=lambda d: d.apr, reverse=True)
            return small + large
        return debts

    def _recommend_strategy(
        self, avalanche: DebtPayoffPlan, snowball: DebtPayoffPlan, debts: List[DebtItem]
    ) -> Tuple[DebtStrategy, str]:
        """Recommend optimal strategy based on debt profile."""
        interest_diff = snowball.total_interest_paid - avalanche.total_interest_paid
        months_diff = snowball.total_months - avalanche.total_months

        small_debts = [d for d in debts if d.current_balance < 1_500]
        if len(small_debts) >= 2 and interest_diff < 500:
            return (
                DebtStrategy.SNOWBALL,
                f"Multiple small debts to knock out quickly. Interest difference is only ${interest_diff:,.0f} — the psychological wins from snowball are worth it.",
            )
        return (
            DebtStrategy.AVALANCHE,
            f"Avalanche saves ${interest_diff:,.0f} in interest and {months_diff} months vs snowball. Mathematically optimal for your debt profile.",
        )

    def _extra_payment_impact(
        self,
        debts: List[DebtItem],
        base_monthly: float,
        extra: float,
        strategy: DebtStrategy,
    ) -> ExtraPaymentImpact:
        """Calculate impact of adding extra monthly payment."""
        base_plan = self._calculate_plan(debts, base_monthly, strategy)
        extra_plan = self._calculate_plan(debts, base_monthly + extra, strategy)

        months_saved = base_plan.total_months - extra_plan.total_months
        interest_saved = base_plan.total_interest_paid - extra_plan.total_interest_paid

        return ExtraPaymentImpact(
            extra_monthly=extra,
            months_saved=max(0, months_saved),
            interest_saved=round(max(0, interest_saved), 2),
            new_payoff_date=extra_plan.payoff_date,
        )

    def _analyze_consolidation(
        self,
        debts: List[DebtItem],
        total_balance: float,
        current_weighted_apr: float,
        new_apr: float,
    ) -> ConsolidationAnalysis:
        """Analyze if consolidating debts is beneficial."""
        # Current scenario
        current_monthly = sum(d.minimum_payment for d in debts)

        # New consolidated payment (10-year term)
        n = 120  # months
        monthly_rate = new_apr / 12
        if monthly_rate > 0:
            new_payment = total_balance * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
        else:
            new_payment = total_balance / n

        current_total_interest = sum(
            d.current_balance * d.apr / 12 * 120 for d in debts  # simplified
        )
        new_total_interest = (new_payment * n) - total_balance
        interest_savings = current_total_interest - new_total_interest
        monthly_savings = current_monthly - new_payment

        closing_costs = total_balance * 0.01  # estimate 1% origination fee
        break_even = int(closing_costs / max(monthly_savings, 1)) if monthly_savings > 0 else 999

        return ConsolidationAnalysis(
            current_weighted_apr=round(current_weighted_apr, 4),
            current_total_monthly=round(current_monthly, 2),
            new_consolidated_apr=new_apr,
            new_monthly_payment=round(new_payment, 2),
            monthly_savings=round(monthly_savings, 2),
            interest_savings=round(interest_savings, 2),
            break_even_months=break_even,
            recommended=interest_savings > 0 and break_even < 36,
            notes=(
                f"Consolidating at {new_apr*100:.1f}% APR saves ${interest_savings:,.0f} over the life of the loan "
                f"with a break-even at {break_even} months."
                if interest_savings > 0 else
                "Current rates are already competitive. Consolidation not recommended."
            ),
        )
