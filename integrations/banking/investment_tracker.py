"""
Investment Tracker — Brokerage, retirement, and portfolio analytics.
Tracks holdings, performance, allocation, and tax-lot information.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .plaid_client import PlaidClient, InvestmentHolding

logger = logging.getLogger(__name__)


class AssetClass(str, Enum):
    EQUITIES = "equities"
    FIXED_INCOME = "fixed_income"
    CASH = "cash"
    REAL_ESTATE = "real_estate"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    ALTERNATIVES = "alternatives"
    UNKNOWN = "unknown"


class SecurityType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    OPTION = "option"
    DERIVATIVE = "derivative"
    CASH = "cash"
    OTHER = "other"


class HoldingDetail(BaseModel):
    account_id: str
    account_name: Optional[str] = None
    security_id: str
    ticker: Optional[str] = None
    security_name: Optional[str] = None
    security_type: SecurityType = SecurityType.OTHER
    asset_class: AssetClass = AssetClass.UNKNOWN
    quantity: float = 0.0
    current_price: Optional[float] = None
    market_value: float = 0.0
    cost_basis: Optional[float] = None
    unrealized_gain: Optional[float] = None
    unrealized_gain_pct: Optional[float] = None
    currency: str = "USD"
    is_core_position: bool = False


class AccountPerformance(BaseModel):
    account_id: str
    account_name: str
    account_subtype: str  # "401k", "ira", "brokerage", etc.
    total_value: float = 0.0
    total_cost_basis: Optional[float] = None
    total_gain: Optional[float] = None
    total_gain_pct: Optional[float] = None
    holdings: List[HoldingDetail] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AllocationBreakdown(BaseModel):
    by_asset_class: Dict[str, float] = Field(default_factory=dict)   # percentage
    by_account_type: Dict[str, float] = Field(default_factory=dict)
    by_security_type: Dict[str, float] = Field(default_factory=dict)
    top_holdings: List[Dict[str, Any]] = Field(default_factory=list)
    concentration_risk: Optional[str] = None


class PortfolioSummary(BaseModel):
    client_id: str
    total_portfolio_value: float = 0.0
    total_cost_basis: Optional[float] = None
    total_unrealized_gain: Optional[float] = None
    total_unrealized_gain_pct: Optional[float] = None
    accounts: List[AccountPerformance] = Field(default_factory=list)
    allocation: AllocationBreakdown = Field(default_factory=AllocationBreakdown)
    retirement_value: float = 0.0
    brokerage_value: float = 0.0
    other_investment_value: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


SECURITY_TYPE_MAP = {
    "equity": SecurityType.STOCK,
    "etf": SecurityType.ETF,
    "mutual fund": SecurityType.MUTUAL_FUND,
    "fixed income": SecurityType.BOND,
    "bond": SecurityType.BOND,
    "option": SecurityType.OPTION,
    "cash": SecurityType.CASH,
    "derivative": SecurityType.DERIVATIVE,
}

RETIREMENT_SUBTYPES = {"401k", "roth", "ira", "pension", "simple ira", "sep ira", "403b", "457b"}


class InvestmentTracker:
    """
    Tracks all investment accounts, computes portfolio performance,
    asset allocation, and retirement readiness.
    """

    def __init__(self, plaid_client: Optional[PlaidClient] = None):
        self.client = plaid_client

    def _classify_security(self, plaid_type: Optional[str]) -> SecurityType:
        if not plaid_type:
            return SecurityType.OTHER
        return SECURITY_TYPE_MAP.get(plaid_type.lower(), SecurityType.OTHER)

    def _classify_asset_class(self, security_type: SecurityType, ticker: Optional[str]) -> AssetClass:
        if security_type == SecurityType.BOND:
            return AssetClass.FIXED_INCOME
        if security_type == SecurityType.CASH:
            return AssetClass.CASH
        if security_type in (SecurityType.STOCK, SecurityType.ETF, SecurityType.MUTUAL_FUND):
            return AssetClass.EQUITIES
        return AssetClass.UNKNOWN

    async def build_portfolio(
        self,
        client_id: str,
        access_tokens: List[str],
    ) -> PortfolioSummary:
        """Fetch and aggregate investment data across all accounts."""
        portfolio = PortfolioSummary(client_id=client_id)
        all_holdings: List[HoldingDetail] = []

        for token in access_tokens:
            try:
                data = await self.client.get_investments(token)
                acct_map = {a["account_id"]: a for a in data.get("accounts", [])}
                holdings = data.get("holdings", [])

                # Group by account
                acct_holdings: Dict[str, List[HoldingDetail]] = {}
                for h in holdings:
                    acct_id = h.account_id
                    acct = acct_map.get(acct_id, {})
                    acct_name = acct.get("name", "Investment Account")
                    subtype = str(acct.get("subtype", "brokerage")).lower()
                    sec_type = self._classify_security(h.security_type)
                    asset_cls = self._classify_asset_class(sec_type, h.ticker_symbol)

                    mv = h.institution_value or 0.0
                    cb = h.cost_basis
                    gain = (mv - cb) if cb else None
                    gain_pct = (gain / cb) if (cb and cb > 0) else None

                    detail = HoldingDetail(
                        account_id=acct_id,
                        account_name=acct_name,
                        security_id=h.security_id,
                        ticker=h.ticker_symbol,
                        security_name=h.security_name,
                        security_type=sec_type,
                        asset_class=asset_cls,
                        quantity=h.quantity or 0.0,
                        current_price=h.institution_price,
                        market_value=round(mv, 2),
                        cost_basis=cb,
                        unrealized_gain=round(gain, 2) if gain is not None else None,
                        unrealized_gain_pct=round(gain_pct * 100, 2) if gain_pct is not None else None,
                        currency=h.currency,
                    )
                    all_holdings.append(detail)

                    if acct_id not in acct_holdings:
                        acct_holdings[acct_id] = []
                    acct_holdings[acct_id].append(detail)

                # Build AccountPerformance objects
                for acct_id, h_list in acct_holdings.items():
                    acct = acct_map.get(acct_id, {})
                    subtype = str(acct.get("subtype", "brokerage")).lower()
                    total_val = sum(h.market_value for h in h_list)
                    total_cb = sum(h.cost_basis for h in h_list if h.cost_basis is not None)
                    total_gain = sum(h.unrealized_gain for h in h_list if h.unrealized_gain is not None)
                    perf = AccountPerformance(
                        account_id=acct_id,
                        account_name=acct.get("name", "Investment Account"),
                        account_subtype=subtype,
                        total_value=round(total_val, 2),
                        total_cost_basis=round(total_cb, 2) if total_cb else None,
                        total_gain=round(total_gain, 2) if total_gain else None,
                        total_gain_pct=round((total_gain / total_cb * 100), 2) if (total_gain and total_cb) else None,
                        holdings=h_list,
                    )
                    portfolio.accounts.append(perf)

                    if subtype in RETIREMENT_SUBTYPES:
                        portfolio.retirement_value += total_val
                    else:
                        portfolio.brokerage_value += total_val

            except Exception as e:
                logger.error(f"Failed to fetch investments for token: {e}")

        portfolio.total_portfolio_value = round(portfolio.retirement_value + portfolio.brokerage_value, 2)

        # Aggregate gains
        total_cb = sum(h.cost_basis for h in all_holdings if h.cost_basis)
        total_gain = sum(h.unrealized_gain for h in all_holdings if h.unrealized_gain is not None)
        portfolio.total_cost_basis = round(total_cb, 2) if total_cb else None
        portfolio.total_unrealized_gain = round(total_gain, 2) if total_gain else None
        portfolio.total_unrealized_gain_pct = round(total_gain / total_cb * 100, 2) if (total_gain and total_cb) else None

        portfolio.allocation = self._compute_allocation(all_holdings, portfolio.total_portfolio_value)
        return portfolio

    def _compute_allocation(
        self, holdings: List[HoldingDetail], total_value: float
    ) -> AllocationBreakdown:
        """Compute asset class and security type allocation percentages."""
        by_asset: Dict[str, float] = {}
        by_sec_type: Dict[str, float] = {}

        for h in holdings:
            ac = h.asset_class.value
            st = h.security_type.value
            pct = (h.market_value / total_value * 100) if total_value > 0 else 0
            by_asset[ac] = round(by_asset.get(ac, 0) + pct, 2)
            by_sec_type[st] = round(by_sec_type.get(st, 0) + pct, 2)

        # Top holdings by value
        top_holdings = sorted(
            [{"ticker": h.ticker or h.security_name, "value": h.market_value,
              "pct": round(h.market_value / total_value * 100, 2) if total_value > 0 else 0}
             for h in holdings],
            key=lambda x: x["value"],
            reverse=True,
        )[:10]

        # Concentration risk
        top_pct = top_holdings[0]["pct"] if top_holdings else 0
        concentration = (
            "High — top holding exceeds 20% of portfolio. Consider diversifying."
            if top_pct > 20 else
            "Moderate" if top_pct > 10 else "Low"
        )

        return AllocationBreakdown(
            by_asset_class=by_asset,
            by_security_type=by_sec_type,
            top_holdings=top_holdings,
            concentration_risk=concentration,
        )

    def retirement_readiness(
        self,
        portfolio: PortfolioSummary,
        current_age: int,
        target_retirement_age: int = 65,
        annual_income: float = 100_000,
        expected_return: float = 0.07,
        withdrawal_rate: float = 0.04,
    ) -> Dict[str, Any]:
        """
        Project retirement account growth and assess readiness.
        Uses compound interest with expected market return.
        """
        years_to_retire = max(0, target_retirement_age - current_age)
        current_balance = portfolio.retirement_value

        # FV = PV * (1 + r)^n  (no additional contributions modeled)
        projected_value = current_balance * ((1 + expected_return) ** years_to_retire)

        # Sustainable withdrawal
        annual_withdrawal = projected_value * withdrawal_rate
        replacement_rate = annual_withdrawal / annual_income if annual_income > 0 else 0

        # Target: ~25x annual expenses (4% rule)
        annual_expenses = annual_income * 0.80  # assume 80% income replacement
        fire_target = annual_expenses * 25

        return {
            "current_retirement_balance": round(current_balance, 2),
            "years_to_retirement": years_to_retire,
            "projected_balance_at_retirement": round(projected_value, 2),
            "projected_annual_withdrawal": round(annual_withdrawal, 2),
            "income_replacement_rate": f"{replacement_rate*100:.0f}%",
            "fire_target": round(fire_target, 2),
            "on_track": projected_value >= fire_target,
            "shortfall": round(max(0, fire_target - projected_value), 2),
            "recommendation": (
                "On track! Continue current contributions." if projected_value >= fire_target
                else f"Increase annual retirement contributions by ${(fire_target - projected_value) / max(years_to_retire * 12, 1):,.0f}/month to close the gap."
            ),
        }
