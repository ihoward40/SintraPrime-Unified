"""
Cash Flow Analyzer — Monthly income/expense patterns, trends, and 6-month forecasting.
Identifies seasonality, income sources, fixed vs variable expenses.
"""

import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from .transaction_engine import EnrichedTransaction, MasterCategory

logger = logging.getLogger(__name__)


class IncomeSource(BaseModel):
    source: str
    category: str
    monthly_average: float
    frequency: str  # "monthly", "biweekly", "irregular"
    last_received: Optional[date] = None
    is_primary: bool = False
    annual_total: float = 0.0
    reliability: str  # "stable", "variable", "irregular"


class ExpenseBucket(BaseModel):
    category: str
    label: str
    is_fixed: bool
    monthly_average: float
    monthly_min: float
    monthly_max: float
    trend: str  # "stable", "increasing", "decreasing"
    annual_total: float = 0.0


class MonthlySnapshot(BaseModel):
    year: int
    month: int
    total_income: float = 0.0
    total_expenses: float = 0.0
    net_cash_flow: float = 0.0
    fixed_expenses: float = 0.0
    variable_expenses: float = 0.0
    savings: float = 0.0
    by_category: Dict[str, float] = Field(default_factory=dict)


class CashFlowForecast(BaseModel):
    forecast_months: int
    starting_balance: float
    monthly_projections: List[Dict[str, Any]] = Field(default_factory=list)
    projected_end_balance: float = 0.0
    months_until_zero: Optional[int] = None
    risk_level: str = "low"  # "low", "medium", "high", "critical"
    recommendations: List[str] = Field(default_factory=list)


class CashFlowReport(BaseModel):
    client_id: str
    period_months: int
    income_sources: List[IncomeSource] = Field(default_factory=list)
    expense_buckets: List[ExpenseBucket] = Field(default_factory=list)
    monthly_snapshots: List[MonthlySnapshot] = Field(default_factory=list)
    average_monthly_income: float = 0.0
    average_monthly_expenses: float = 0.0
    average_monthly_net: float = 0.0
    savings_rate: float = 0.0
    fixed_expense_ratio: float = 0.0
    income_stability_score: float = 0.0  # 0–100
    expense_control_score: float = 0.0   # 0–100
    forecast: Optional[CashFlowForecast] = None


FIXED_CATEGORIES = {
    MasterCategory.HOUSING, MasterCategory.INSURANCE, MasterCategory.FINANCIAL
}


class CashFlowAnalyzer:
    """
    Analyzes income and expense patterns to generate cash flow insights and forecasts.
    """

    def __init__(self):
        pass

    def analyze(
        self,
        client_id: str,
        transactions: List[EnrichedTransaction],
        current_balance: float = 0.0,
        forecast_months: int = 6,
    ) -> CashFlowReport:
        """Full cash flow analysis over the transaction history."""
        # Group by month
        monthly: Dict[Tuple[int, int], List[EnrichedTransaction]] = defaultdict(list)
        for txn in transactions:
            key = (txn.date.year, txn.date.month)
            monthly[key].append(txn)

        snapshots = [self._build_snapshot(ym, txns) for ym, txns in sorted(monthly.items())]
        period_months = len(snapshots)

        income_sources = self._identify_income_sources(transactions)
        expense_buckets = self._identify_expense_buckets(snapshots, transactions)

        incomes = [s.total_income for s in snapshots]
        expenses = [s.total_expenses for s in snapshots]
        nets = [s.net_cash_flow for s in snapshots]

        avg_income = statistics.mean(incomes) if incomes else 0.0
        avg_expenses = statistics.mean(expenses) if expenses else 0.0
        avg_net = statistics.mean(nets) if nets else 0.0

        savings_rate = (avg_net / avg_income) if avg_income > 0 else 0.0

        fixed_total = sum(
            b.monthly_average for b in expense_buckets if b.is_fixed
        )
        fixed_ratio = (fixed_total / avg_expenses) if avg_expenses > 0 else 0.0

        income_stability = self._score_stability(incomes)
        expense_control = self._score_expense_control(expenses, avg_expenses)

        forecast = self._forecast(
            snapshots, current_balance, forecast_months, avg_income, avg_expenses
        )

        return CashFlowReport(
            client_id=client_id,
            period_months=period_months,
            income_sources=income_sources,
            expense_buckets=expense_buckets,
            monthly_snapshots=snapshots,
            average_monthly_income=round(avg_income, 2),
            average_monthly_expenses=round(avg_expenses, 2),
            average_monthly_net=round(avg_net, 2),
            savings_rate=round(savings_rate, 4),
            fixed_expense_ratio=round(fixed_ratio, 4),
            income_stability_score=income_stability,
            expense_control_score=expense_control,
            forecast=forecast,
        )

    def _build_snapshot(
        self,
        ym: Tuple[int, int],
        transactions: List[EnrichedTransaction],
    ) -> MonthlySnapshot:
        year, month = ym
        by_cat: Dict[str, float] = defaultdict(float)
        income = expenses = fixed_exp = variable_exp = 0.0

        for txn in transactions:
            if txn.is_transfer:
                continue
            cat = txn.master_category.value
            if txn.is_income:
                income += abs(txn.amount)
            elif txn.is_expense:
                expenses += txn.amount
                by_cat[cat] += txn.amount
                if txn.master_category in FIXED_CATEGORIES or txn.is_recurring:
                    fixed_exp += txn.amount
                else:
                    variable_exp += txn.amount

        return MonthlySnapshot(
            year=year,
            month=month,
            total_income=round(income, 2),
            total_expenses=round(expenses, 2),
            net_cash_flow=round(income - expenses, 2),
            fixed_expenses=round(fixed_exp, 2),
            variable_expenses=round(variable_exp, 2),
            savings=round(max(0, income - expenses), 2),
            by_category={k: round(v, 2) for k, v in by_cat.items()},
        )

    def _identify_income_sources(
        self, transactions: List[EnrichedTransaction]
    ) -> List[IncomeSource]:
        """Identify distinct income streams and their characteristics."""
        income_txns = [t for t in transactions if t.is_income and not t.is_transfer]
        source_map: Dict[str, List[EnrichedTransaction]] = defaultdict(list)
        for t in income_txns:
            key = t.merchant_name or t.name
            source_map[key].append(t)

        sources = []
        for name, txns in source_map.items():
            amounts = [abs(t.amount) for t in txns]
            monthly_avg = statistics.mean(amounts) if amounts else 0.0
            cv = (statistics.stdev(amounts) / monthly_avg) if len(amounts) > 1 and monthly_avg > 0 else 0.0
            reliability = "stable" if cv < 0.1 else ("variable" if cv < 0.3 else "irregular")
            sources.append(IncomeSource(
                source=name,
                category=txns[0].sub_category or "general",
                monthly_average=round(monthly_avg, 2),
                frequency="monthly",
                last_received=max(t.date for t in txns),
                is_primary=monthly_avg > 3000,
                annual_total=round(monthly_avg * 12, 2),
                reliability=reliability,
            ))

        return sorted(sources, key=lambda s: s.monthly_average, reverse=True)

    def _identify_expense_buckets(
        self,
        snapshots: List[MonthlySnapshot],
        transactions: List[EnrichedTransaction],
    ) -> List[ExpenseBucket]:
        """Categorize expenses into fixed and variable buckets with trend analysis."""
        cat_monthly: Dict[str, List[float]] = defaultdict(list)
        for snap in snapshots:
            for cat, amount in snap.by_category.items():
                cat_monthly[cat].append(amount)

        buckets = []
        for cat, amounts in cat_monthly.items():
            avg = statistics.mean(amounts) if amounts else 0.0
            mn = min(amounts) if amounts else 0.0
            mx = max(amounts) if amounts else 0.0

            # Trend detection (simple linear)
            if len(amounts) >= 3:
                first_half = statistics.mean(amounts[:len(amounts)//2])
                second_half = statistics.mean(amounts[len(amounts)//2:])
                trend = "increasing" if second_half > first_half * 1.05 else (
                    "decreasing" if second_half < first_half * 0.95 else "stable"
                )
            else:
                trend = "stable"

            try:
                master_cat = MasterCategory(cat)
            except ValueError:
                master_cat = MasterCategory.OTHER

            buckets.append(ExpenseBucket(
                category=cat,
                label=cat.replace("_", " ").title(),
                is_fixed=master_cat in FIXED_CATEGORIES,
                monthly_average=round(avg, 2),
                monthly_min=round(mn, 2),
                monthly_max=round(mx, 2),
                trend=trend,
                annual_total=round(avg * 12, 2),
            ))

        return sorted(buckets, key=lambda b: b.monthly_average, reverse=True)

    def _score_stability(self, monthly_values: List[float]) -> float:
        """Income stability score 0–100 based on coefficient of variation."""
        if not monthly_values or len(monthly_values) < 2:
            return 50.0
        mean = statistics.mean(monthly_values)
        if mean == 0:
            return 0.0
        cv = statistics.stdev(monthly_values) / mean
        return round(max(0, min(100, 100 - (cv * 200))), 1)

    def _score_expense_control(
        self, expenses: List[float], avg: float
    ) -> float:
        """Expense control score — lower variance = higher control."""
        if not expenses or len(expenses) < 2 or avg == 0:
            return 50.0
        cv = statistics.stdev(expenses) / avg
        return round(max(0, min(100, 100 - (cv * 150))), 1)

    def _forecast(
        self,
        snapshots: List[MonthlySnapshot],
        current_balance: float,
        forecast_months: int,
        avg_income: float,
        avg_expenses: float,
    ) -> CashFlowForecast:
        """Simple forward-looking cash flow forecast."""
        projections = []
        balance = current_balance
        months_until_zero = None

        for i in range(1, forecast_months + 1):
            net = avg_income - avg_expenses
            balance += net
            projections.append({
                "month": i,
                "projected_income": round(avg_income, 2),
                "projected_expenses": round(avg_expenses, 2),
                "projected_net": round(net, 2),
                "projected_balance": round(balance, 2),
            })
            if balance <= 0 and months_until_zero is None:
                months_until_zero = i

        risk = "low"
        if months_until_zero and months_until_zero <= 2:
            risk = "critical"
        elif months_until_zero and months_until_zero <= 4:
            risk = "high"
        elif avg_income < avg_expenses:
            risk = "medium"

        recommendations = []
        if avg_income < avg_expenses:
            recommendations.append("Expenses exceed income — identify top 3 expense categories to cut immediately.")
        if current_balance < avg_expenses * 3:
            recommendations.append("Emergency fund is below 3 months of expenses. Build it up before other goals.")
        if avg_income > avg_expenses * 1.2:
            recommendations.append("Strong cash flow! Route surplus to high-yield savings and investments.")

        return CashFlowForecast(
            forecast_months=forecast_months,
            starting_balance=round(current_balance, 2),
            monthly_projections=projections,
            projected_end_balance=round(balance, 2),
            months_until_zero=months_until_zero,
            risk_level=risk,
            recommendations=recommendations,
        )
