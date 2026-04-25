"""
Business Banking — Business account analysis, cash flow management, and financial health for SMBs.
"""

import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from .plaid_client import PlaidClient, Transaction
from .transaction_engine import EnrichedTransaction, MasterCategory

logger = logging.getLogger(__name__)


class BusinessAccountType(str, Enum):
    OPERATING = "operating"
    PAYROLL = "payroll"
    TAX_RESERVE = "tax_reserve"
    SAVINGS = "savings"
    CREDIT_LINE = "credit_line"
    MERCHANT = "merchant"


class RevenueStream(BaseModel):
    name: str
    monthly_average: float
    monthly_trend: str  # "growing", "stable", "declining"
    percentage_of_total: float
    transaction_count: int
    reliability: str  # "recurring", "variable", "one-time"


class OperatingExpenseItem(BaseModel):
    category: str
    monthly_average: float
    percentage_of_revenue: float
    is_fixed: bool
    trend: str


class BusinessCashFlowMetrics(BaseModel):
    period_start: date
    period_end: date
    gross_revenue: float = 0.0
    cost_of_goods_sold: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    operating_expenses: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    net_margin_pct: float = 0.0
    operating_cash_flow: float = 0.0
    average_daily_balance: float = 0.0
    burn_rate: Optional[float] = None
    runway_months: Optional[float] = None


class BusinessHealthReport(BaseModel):
    business_id: str
    business_name: Optional[str] = None
    period_months: int
    accounts: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_streams: List[RevenueStream] = Field(default_factory=list)
    operating_expenses: List[OperatingExpenseItem] = Field(default_factory=list)
    cash_flow_metrics: Optional[BusinessCashFlowMetrics] = None
    monthly_snapshots: List[Dict[str, Any]] = Field(default_factory=list)
    financial_ratios: Dict[str, float] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessBanking:
    """
    Business banking analytics for SintraPrime SMB clients.
    Analyzes revenue, expenses, cash flow, and business health metrics.
    """

    REVENUE_INDICATORS = [
        "stripe", "square", "shopify", "paypal", "invoice", "customer payment",
        "sales", "revenue", "pos sale", "ach credit", "wire credit",
        "venmo business", "clover", "lightspeed",
    ]

    COGS_INDICATORS = [
        "inventory", "supplier", "wholesale", "manufacturing", "raw material",
        "product cost", "cogs", "cost of goods",
    ]

    OPERATING_CATEGORIES = {
        "payroll": ["gusto", "adp", "paychex", "payroll", "wages"],
        "rent": ["rent", "lease", "property"],
        "utilities": ["electric", "gas", "water", "internet", "phone"],
        "software": ["saas", "software", "subscription", "aws", "google cloud", "azure"],
        "marketing": ["google ads", "facebook ads", "marketing", "advertising"],
        "insurance": ["insurance", "business insurance"],
        "professional": ["attorney", "accountant", "cpa", "consultant"],
        "supplies": ["office depot", "staples", "amazon business", "supplies"],
    }

    def __init__(self, plaid_client: Optional[PlaidClient] = None):
        self.client = plaid_client

    def analyze(
        self,
        business_id: str,
        transactions: List[EnrichedTransaction],
        accounts: Optional[List[Dict[str, Any]]] = None,
        business_name: Optional[str] = None,
        period_months: int = 12,
    ) -> BusinessHealthReport:
        """Full business financial health analysis."""
        report = BusinessHealthReport(
            business_id=business_id,
            business_name=business_name,
            period_months=period_months,
            accounts=accounts or [],
        )

        # Filter to business period
        cutoff = date.today() - timedelta(days=period_months * 30)
        txns = [t for t in transactions if t.date >= cutoff]

        if not txns:
            return report

        # Classify transactions
        revenue_txns = self._identify_revenue(txns)
        cogs_txns = self._identify_cogs(txns)
        opex_txns = self._identify_opex(txns)

        report.revenue_streams = self._analyze_revenue_streams(revenue_txns)
        report.operating_expenses = self._analyze_opex(opex_txns, period_months)

        # Monthly snapshots
        monthly = self._build_monthly_snapshots(txns, revenue_txns, cogs_txns, opex_txns)
        report.monthly_snapshots = monthly

        # Aggregate metrics
        total_revenue = sum(abs(t.amount) for t in revenue_txns)
        total_cogs = sum(t.amount for t in cogs_txns)
        total_opex = sum(t.amount for t in opex_txns)
        gross_profit = total_revenue - total_cogs
        ebitda = gross_profit - total_opex
        avg_revenue = total_revenue / max(period_months, 1)

        report.cash_flow_metrics = BusinessCashFlowMetrics(
            period_start=cutoff,
            period_end=date.today(),
            gross_revenue=round(total_revenue, 2),
            cost_of_goods_sold=round(total_cogs, 2),
            gross_profit=round(gross_profit, 2),
            gross_margin_pct=round((gross_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
            operating_expenses=round(total_opex, 2),
            ebitda=round(ebitda, 2),
            net_income=round(ebitda, 2),  # simplified (no D&A, taxes)
            net_margin_pct=round((ebitda / total_revenue * 100) if total_revenue > 0 else 0, 2),
            operating_cash_flow=round(ebitda, 2),
            burn_rate=round(total_opex / period_months, 2) if ebitda < 0 else None,
            runway_months=self._calculate_runway(accounts, total_opex / period_months) if ebitda < 0 else None,
        )

        # Financial ratios
        report.financial_ratios = {
            "gross_margin": round((gross_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "net_margin": round((ebitda / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "expense_ratio": round((total_opex / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "monthly_revenue_avg": round(avg_revenue, 2),
            "revenue_growth_rate": self._calc_growth_rate(monthly),
        }

        report.insights = self._generate_insights(report)
        report.alerts = self._generate_alerts(report)
        return report

    def _identify_revenue(
        self, transactions: List[EnrichedTransaction]
    ) -> List[EnrichedTransaction]:
        """Identify revenue transactions."""
        result = []
        for t in transactions:
            if t.is_income and not t.is_transfer:
                result.append(t)
                continue
            name_lower = (t.name + " " + (t.merchant_name or "")).lower()
            if any(indicator in name_lower for indicator in self.REVENUE_INDICATORS):
                result.append(t)
        return result

    def _identify_cogs(
        self, transactions: List[EnrichedTransaction]
    ) -> List[EnrichedTransaction]:
        """Identify cost-of-goods transactions."""
        result = []
        for t in transactions:
            if not t.is_expense:
                continue
            name_lower = (t.name + " " + (t.merchant_name or "")).lower()
            if any(ind in name_lower for ind in self.COGS_INDICATORS):
                result.append(t)
        return result

    def _identify_opex(
        self, transactions: List[EnrichedTransaction]
    ) -> List[EnrichedTransaction]:
        """Identify operating expense transactions."""
        return [
            t for t in transactions
            if t.is_expense and t.master_category in (
                MasterCategory.BUSINESS, MasterCategory.UTILITIES,
                MasterCategory.HOUSING, MasterCategory.LEGAL,
            )
        ]

    def _analyze_revenue_streams(
        self, revenue_txns: List[EnrichedTransaction]
    ) -> List[RevenueStream]:
        """Group revenue by source and compute monthly averages."""
        source_map: Dict[str, List[float]] = defaultdict(list)
        for t in revenue_txns:
            key = t.merchant_name or t.name
            source_map[key].append(abs(t.amount))

        total_revenue = sum(abs(t.amount) for t in revenue_txns)
        streams = []
        for name, amounts in source_map.items():
            avg = statistics.mean(amounts)
            reliability = "recurring" if len(amounts) >= 3 else ("variable" if len(amounts) >= 2 else "one-time")
            trend = "stable"
            if len(amounts) >= 4:
                first_half = statistics.mean(amounts[:len(amounts)//2])
                second_half = statistics.mean(amounts[len(amounts)//2:])
                trend = "growing" if second_half > first_half * 1.05 else ("declining" if second_half < first_half * 0.95 else "stable")

            streams.append(RevenueStream(
                name=name,
                monthly_average=round(avg, 2),
                monthly_trend=trend,
                percentage_of_total=round(sum(amounts) / total_revenue * 100, 2) if total_revenue else 0,
                transaction_count=len(amounts),
                reliability=reliability,
            ))

        return sorted(streams, key=lambda s: s.monthly_average, reverse=True)

    def _analyze_opex(
        self,
        opex_txns: List[EnrichedTransaction],
        months: int,
    ) -> List[OperatingExpenseItem]:
        """Compute operating expense breakdown."""
        total_revenue_est = 1  # placeholder
        cat_totals: Dict[str, float] = defaultdict(float)
        for t in opex_txns:
            cat_totals[t.master_category.value] += t.amount

        items = []
        total_opex = sum(cat_totals.values())
        for cat, total in cat_totals.items():
            monthly_avg = total / max(months, 1)
            items.append(OperatingExpenseItem(
                category=cat,
                monthly_average=round(monthly_avg, 2),
                percentage_of_revenue=0.0,  # needs revenue context
                is_fixed=cat in ("housing", "insurance"),
                trend="stable",
            ))
        return sorted(items, key=lambda i: i.monthly_average, reverse=True)

    def _build_monthly_snapshots(
        self,
        all_txns: List[EnrichedTransaction],
        revenue_txns: List[EnrichedTransaction],
        cogs_txns: List[EnrichedTransaction],
        opex_txns: List[EnrichedTransaction],
    ) -> List[Dict[str, Any]]:
        """Build month-by-month financial snapshots."""
        snapshots: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(
            lambda: {"revenue": 0.0, "cogs": 0.0, "opex": 0.0}
        )
        for t in revenue_txns:
            snapshots[(t.date.year, t.date.month)]["revenue"] += abs(t.amount)
        for t in cogs_txns:
            snapshots[(t.date.year, t.date.month)]["cogs"] += t.amount
        for t in opex_txns:
            snapshots[(t.date.year, t.date.month)]["opex"] += t.amount

        result = []
        for (year, month), data in sorted(snapshots.items()):
            gross_profit = data["revenue"] - data["cogs"]
            net_income = gross_profit - data["opex"]
            result.append({
                "year": year,
                "month": month,
                "revenue": round(data["revenue"], 2),
                "cogs": round(data["cogs"], 2),
                "gross_profit": round(gross_profit, 2),
                "opex": round(data["opex"], 2),
                "net_income": round(net_income, 2),
                "gross_margin_pct": round((gross_profit / data["revenue"] * 100) if data["revenue"] else 0, 1),
            })
        return result

    def _calc_growth_rate(self, monthly_snapshots: List[Dict[str, Any]]) -> float:
        """Calculate revenue growth rate from first to last period."""
        if len(monthly_snapshots) < 2:
            return 0.0
        first_rev = monthly_snapshots[0].get("revenue", 0)
        last_rev = monthly_snapshots[-1].get("revenue", 0)
        if first_rev <= 0:
            return 0.0
        return round((last_rev - first_rev) / first_rev * 100, 2)

    def _calculate_runway(
        self, accounts: Optional[List[Dict]], monthly_burn: float
    ) -> Optional[float]:
        if not accounts or monthly_burn <= 0:
            return None
        total_cash = sum(
            a.get("balances", {}).get("current", 0) or 0
            for a in accounts
            if str(a.get("type", "")).lower() == "depository"
        )
        return round(total_cash / monthly_burn, 1)

    def _generate_insights(self, report: BusinessHealthReport) -> List[str]:
        insights = []
        metrics = report.cash_flow_metrics
        if not metrics:
            return insights

        if metrics.gross_margin_pct > 60:
            insights.append(f"Strong gross margin of {metrics.gross_margin_pct:.0f}% — excellent product economics.")
        elif metrics.gross_margin_pct < 30:
            insights.append(f"Gross margin of {metrics.gross_margin_pct:.0f}% is low. Review COGS for reduction opportunities.")

        if metrics.net_margin_pct > 20:
            insights.append(f"Healthy net margin of {metrics.net_margin_pct:.0f}%. Business is highly profitable.")
        elif metrics.net_margin_pct < 0:
            insights.append(f"Business is operating at a loss ({metrics.net_margin_pct:.0f}% margin). Immediate cost review needed.")

        growth = report.financial_ratios.get("revenue_growth_rate", 0)
        if growth > 20:
            insights.append(f"Revenue growing at {growth:.0f}% — strong trajectory. Consider raising capital to accelerate.")
        elif growth < -10:
            insights.append(f"Revenue declining {abs(growth):.0f}% — investigate customer churn and market fit.")

        if metrics.runway_months and metrics.runway_months < 6:
            insights.append(f"Warning: Only {metrics.runway_months:.0f} months of runway at current burn rate. Fundraise immediately.")

        return insights

    def _generate_alerts(self, report: BusinessHealthReport) -> List[str]:
        alerts = []
        metrics = report.cash_flow_metrics
        if not metrics:
            return alerts

        if metrics.ebitda < 0:
            alerts.append(f"ALERT: Business is cash-flow negative. Monthly burn: ${abs(metrics.burn_rate or 0):,.0f}.")
        if metrics.runway_months and metrics.runway_months < 3:
            alerts.append("CRITICAL: Less than 3 months runway. Secure emergency funding immediately.")
        if metrics.gross_margin_pct < 20:
            alerts.append("Gross margin is critically low. Review pricing and supplier costs.")

        return alerts
