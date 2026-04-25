"""
Net Worth Calculator — Real-time net worth across all asset and liability categories.
Includes historical trends, benchmarks, and FIRE calculator.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    CASH = "cash"
    CHECKING = "checking"
    SAVINGS = "savings"
    BROKERAGE = "brokerage"
    RETIREMENT_401K = "401k"
    RETIREMENT_IRA = "ira"
    RETIREMENT_ROTH = "roth_ira"
    REAL_ESTATE = "real_estate"
    BUSINESS_EQUITY = "business_equity"
    VEHICLE = "vehicle"
    CRYPTO = "crypto"
    OTHER_ASSET = "other_asset"


class LiabilityType(str, Enum):
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    STUDENT_LOAN = "student_loan"
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    BUSINESS_DEBT = "business_debt"
    HELOC = "heloc"
    OTHER_LIABILITY = "other_liability"


class Asset(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    current_value: float
    acquisition_cost: Optional[float] = None
    acquired_date: Optional[date] = None
    is_liquid: bool = True
    currency: str = "USD"
    source: str = "plaid"  # "plaid", "manual", "estimated"
    notes: Optional[str] = None


class LiabilityItem(BaseModel):
    liability_id: str
    name: str
    liability_type: LiabilityType
    current_balance: float
    apr: Optional[float] = None
    monthly_payment: Optional[float] = None
    payoff_date: Optional[date] = None
    source: str = "plaid"


class NetWorthSnapshot(BaseModel):
    snapshot_date: date
    total_assets: float
    total_liabilities: float
    net_worth: float
    liquid_assets: float
    illiquid_assets: float


class NetWorthReport(BaseModel):
    client_id: str
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

    # Assets
    assets: List[Asset] = Field(default_factory=list)
    total_cash: float = 0.0
    total_investments: float = 0.0
    total_retirement: float = 0.0
    total_real_estate: float = 0.0
    total_other_assets: float = 0.0
    total_assets: float = 0.0
    liquid_assets: float = 0.0

    # Liabilities
    liabilities: List[LiabilityItem] = Field(default_factory=list)
    total_mortgage: float = 0.0
    total_auto_loans: float = 0.0
    total_student_loans: float = 0.0
    total_credit_card_debt: float = 0.0
    total_other_debt: float = 0.0
    total_liabilities: float = 0.0

    # Net worth
    net_worth: float = 0.0
    net_worth_growth_12m: Optional[float] = None
    net_worth_growth_pct: Optional[float] = None

    # Context
    age: Optional[int] = None
    peer_benchmark: Optional[Dict[str, Any]] = None
    historical_snapshots: List[NetWorthSnapshot] = Field(default_factory=list)
    fire_analysis: Optional[Dict[str, Any]] = None


# Median net worth by age group (Federal Reserve Survey of Consumer Finances, approximate)
AGE_BENCHMARKS = {
    (18, 24): {"median": 8_000,    "mean": 76_000},
    (25, 34): {"median": 39_000,   "mean": 176_000},
    (35, 44): {"median": 135_000,  "mean": 436_000},
    (45, 54): {"median": 247_000,  "mean": 834_000},
    (55, 64): {"median": 364_000,  "mean": 1_175_000},
    (65, 74): {"median": 410_000,  "mean": 1_217_000},
    (75, 99): {"median": 335_000,  "mean": 977_000},
}

LIQUID_TYPES = {AssetType.CASH, AssetType.CHECKING, AssetType.SAVINGS, AssetType.BROKERAGE, AssetType.CRYPTO}


class NetWorthCalculator:
    """
    Computes comprehensive net worth with peer benchmarks, trend analysis, and FIRE calculations.
    """

    def __init__(self):
        pass

    def calculate(
        self,
        client_id: str,
        assets: List[Asset],
        liabilities: List[LiabilityItem],
        age: Optional[int] = None,
        historical_snapshots: Optional[List[NetWorthSnapshot]] = None,
        annual_expenses: Optional[float] = None,
    ) -> NetWorthReport:
        """Compute full net worth report."""
        report = NetWorthReport(
            client_id=client_id,
            assets=assets,
            liabilities=liabilities,
            age=age,
            historical_snapshots=historical_snapshots or [],
        )

        # Asset totals
        cash_types = {AssetType.CASH, AssetType.CHECKING, AssetType.SAVINGS}
        investment_types = {AssetType.BROKERAGE, AssetType.CRYPTO}
        retirement_types = {AssetType.RETIREMENT_401K, AssetType.RETIREMENT_IRA, AssetType.RETIREMENT_ROTH}

        for asset in assets:
            v = asset.current_value
            if asset.asset_type in cash_types:
                report.total_cash += v
            elif asset.asset_type in investment_types:
                report.total_investments += v
            elif asset.asset_type in retirement_types:
                report.total_retirement += v
            elif asset.asset_type == AssetType.REAL_ESTATE:
                report.total_real_estate += v
            else:
                report.total_other_assets += v

            if asset.asset_type in LIQUID_TYPES:
                report.liquid_assets += v

        report.total_assets = round(
            report.total_cash + report.total_investments + report.total_retirement +
            report.total_real_estate + report.total_other_assets, 2
        )
        report.liquid_assets = round(report.liquid_assets, 2)

        # Liability totals
        for liab in liabilities:
            b = liab.current_balance
            if liab.liability_type == LiabilityType.MORTGAGE:
                report.total_mortgage += b
            elif liab.liability_type == LiabilityType.AUTO_LOAN:
                report.total_auto_loans += b
            elif liab.liability_type == LiabilityType.STUDENT_LOAN:
                report.total_student_loans += b
            elif liab.liability_type == LiabilityType.CREDIT_CARD:
                report.total_credit_card_debt += b
            else:
                report.total_other_debt += b

        report.total_liabilities = round(
            report.total_mortgage + report.total_auto_loans + report.total_student_loans +
            report.total_credit_card_debt + report.total_other_debt, 2
        )

        report.net_worth = round(report.total_assets - report.total_liabilities, 2)

        # Growth trend
        if historical_snapshots and len(historical_snapshots) >= 2:
            oldest = historical_snapshots[0].net_worth
            if oldest != 0:
                report.net_worth_growth_12m = round(report.net_worth - oldest, 2)
                report.net_worth_growth_pct = round(
                    (report.net_worth - oldest) / abs(oldest) * 100, 2
                )

        # Benchmarks
        if age:
            report.peer_benchmark = self._get_benchmark(age, report.net_worth)

        # FIRE analysis
        if annual_expenses:
            report.fire_analysis = self._fire_analysis(
                report.net_worth,
                report.total_retirement + report.total_investments,
                annual_expenses,
                age,
            )

        return report

    def _get_benchmark(self, age: int, net_worth: float) -> Dict[str, Any]:
        """Compare net worth to age-group peers."""
        for (low, high), stats in AGE_BENCHMARKS.items():
            if low <= age <= high:
                pct_vs_median = ((net_worth - stats["median"]) / stats["median"] * 100) if stats["median"] else 0
                return {
                    "age_group": f"{low}–{high}",
                    "median_net_worth": stats["median"],
                    "mean_net_worth": stats["mean"],
                    "your_net_worth": net_worth,
                    "vs_median_pct": round(pct_vs_median, 1),
                    "percentile_estimate": self._estimate_percentile(net_worth, stats["median"]),
                    "summary": (
                        f"Your net worth of ${net_worth:,.0f} is "
                        f"{'above' if net_worth >= stats['median'] else 'below'} the median "
                        f"(${stats['median']:,.0f}) for your age group ({low}–{high})."
                    ),
                }
        return {}

    def _estimate_percentile(self, net_worth: float, median: float) -> str:
        """Rough percentile estimate relative to median."""
        ratio = net_worth / median if median > 0 else 0
        if ratio >= 4: return "top 10%"
        if ratio >= 2: return "top 25%"
        if ratio >= 1: return "top 50%"
        if ratio >= 0.5: return "bottom 50%"
        return "bottom 25%"

    def _fire_analysis(
        self,
        net_worth: float,
        investable_assets: float,
        annual_expenses: float,
        current_age: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate FIRE number and readiness."""
        fire_number = annual_expenses * 25  # 4% safe withdrawal rate
        lean_fire = annual_expenses * 0.75 * 25  # 75% of expenses
        fat_fire = annual_expenses * 1.5 * 25    # 150% of expenses

        shortfall = max(0, fire_number - investable_assets)
        on_track = investable_assets >= fire_number
        pct_of_goal = (investable_assets / fire_number * 100) if fire_number > 0 else 0

        # Years to FIRE at 7% growth (no additional contributions)
        import math
        if investable_assets > 0 and investable_assets < fire_number:
            years_to_fire = math.log(fire_number / investable_assets) / math.log(1.07)
        elif investable_assets >= fire_number:
            years_to_fire = 0
        else:
            years_to_fire = 999

        fire_age = (current_age or 30) + years_to_fire

        return {
            "fire_number": round(fire_number, 2),
            "lean_fire": round(lean_fire, 2),
            "fat_fire": round(fat_fire, 2),
            "current_investable_assets": round(investable_assets, 2),
            "pct_of_fire_goal": round(pct_of_goal, 1),
            "shortfall": round(shortfall, 2),
            "on_track": on_track,
            "years_to_fire": round(years_to_fire, 1) if years_to_fire < 999 else "N/A",
            "projected_fire_age": round(fire_age, 1) if years_to_fire < 999 else "N/A",
            "annual_withdrawal_at_fire": round(fire_number * 0.04, 2),
            "note": "4% safe withdrawal rate. Assumes 7% annual portfolio growth without additional contributions.",
        }

    def take_snapshot(self, report: NetWorthReport) -> NetWorthSnapshot:
        """Create a point-in-time snapshot for historical tracking."""
        return NetWorthSnapshot(
            snapshot_date=date.today(),
            total_assets=report.total_assets,
            total_liabilities=report.total_liabilities,
            net_worth=report.net_worth,
            liquid_assets=report.liquid_assets,
            illiquid_assets=report.total_assets - report.liquid_assets,
        )
