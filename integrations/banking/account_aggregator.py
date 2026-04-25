"""
Account Aggregator — Unified view of all connected bank accounts across institutions.
Normalizes Plaid data into a single coherent financial picture.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .plaid_client import PlaidClient, AccountBalance, Transaction

logger = logging.getLogger(__name__)


class AccountCategory(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    RETIREMENT = "retirement"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    BROKERAGE = "brokerage"
    OTHER = "other"


class InstitutionSummary(BaseModel):
    institution_id: str
    institution_name: str
    access_token: str
    item_id: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced: Optional[datetime] = None
    products: List[str] = Field(default_factory=list)
    status: str = "active"


class EnrichedAccount(BaseModel):
    account_id: str
    institution_id: str
    institution_name: str
    name: str
    official_name: Optional[str] = None
    category: AccountCategory
    account_type: str
    account_subtype: Optional[str] = None
    current_balance: float = 0.0
    available_balance: Optional[float] = None
    credit_limit: Optional[float] = None
    currency: str = "USD"
    mask: Optional[str] = None
    is_asset: bool = True
    is_liability: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AggregatedPortfolio(BaseModel):
    client_id: str
    institutions: List[InstitutionSummary] = Field(default_factory=list)
    accounts: List[EnrichedAccount] = Field(default_factory=list)
    total_cash: float = 0.0
    total_investments: float = 0.0
    total_retirement: float = 0.0
    total_credit_card_debt: float = 0.0
    total_loan_debt: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    net_worth: float = 0.0
    account_count: int = 0
    institution_count: int = 0
    last_refreshed: datetime = Field(default_factory=datetime.utcnow)


TYPE_TO_CATEGORY: Dict[str, AccountCategory] = {
    "depository:checking": AccountCategory.CHECKING,
    "depository:savings": AccountCategory.SAVINGS,
    "depository:money market": AccountCategory.SAVINGS,
    "depository:cd": AccountCategory.SAVINGS,
    "credit:credit card": AccountCategory.CREDIT_CARD,
    "credit:paypal": AccountCategory.CREDIT_CARD,
    "investment:brokerage": AccountCategory.BROKERAGE,
    "investment:retirement": AccountCategory.RETIREMENT,
    "investment:401k": AccountCategory.RETIREMENT,
    "investment:ira": AccountCategory.RETIREMENT,
    "investment:roth": AccountCategory.RETIREMENT,
    "investment:529": AccountCategory.INVESTMENT,
    "loan:student": AccountCategory.LOAN,
    "loan:auto": AccountCategory.LOAN,
    "loan:personal": AccountCategory.LOAN,
    "loan:mortgage": AccountCategory.MORTGAGE,
    "loan:home equity": AccountCategory.MORTGAGE,
}

ASSET_CATEGORIES = {AccountCategory.CHECKING, AccountCategory.SAVINGS, AccountCategory.INVESTMENT,
                    AccountCategory.RETIREMENT, AccountCategory.BROKERAGE}
LIABILITY_CATEGORIES = {AccountCategory.CREDIT_CARD, AccountCategory.LOAN, AccountCategory.MORTGAGE}


class AccountAggregator:
    """
    Aggregates all Plaid-connected accounts into a unified financial portfolio.
    Tracks institutions, normalizes account types, and computes totals.
    """

    def __init__(self, plaid_client: PlaidClient):
        self.client = plaid_client
        self._institution_cache: Dict[str, InstitutionSummary] = {}

    def _categorize_account(self, account_type: str, account_subtype: Optional[str]) -> AccountCategory:
        key = f"{account_type}:{account_subtype}".lower() if account_subtype else account_type.lower()
        return TYPE_TO_CATEGORY.get(key, AccountCategory.OTHER)

    def _enrich_account(
        self,
        acct: AccountBalance,
        institution: InstitutionSummary,
    ) -> EnrichedAccount:
        category = self._categorize_account(acct.account_type, acct.account_subtype)
        is_liability = category in LIABILITY_CATEGORIES
        is_asset = category in ASSET_CATEGORIES

        # For liabilities, balance is debt (positive = owed)
        current_balance = acct.current_balance or 0.0

        return EnrichedAccount(
            account_id=acct.account_id,
            institution_id=institution.institution_id,
            institution_name=institution.institution_name,
            name=acct.name,
            official_name=acct.official_name,
            category=category,
            account_type=acct.account_type,
            account_subtype=acct.account_subtype,
            current_balance=current_balance,
            available_balance=acct.available_balance,
            credit_limit=acct.credit_limit,
            currency=acct.currency,
            mask=acct.mask,
            is_asset=is_asset,
            is_liability=is_liability,
        )

    async def aggregate(
        self,
        client_id: str,
        institutions: List[InstitutionSummary],
    ) -> AggregatedPortfolio:
        """
        Fetch all accounts from all connected institutions and build a unified portfolio.
        """
        portfolio = AggregatedPortfolio(
            client_id=client_id,
            institutions=institutions,
        )

        all_accounts: List[EnrichedAccount] = []
        for inst in institutions:
            try:
                raw_accounts = await self.client.get_accounts(inst.access_token)
                for acct in raw_accounts:
                    enriched = self._enrich_account(acct, inst)
                    all_accounts.append(enriched)
                inst.last_synced = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to fetch accounts for {inst.institution_name}: {e}")
                inst.status = "error"

        portfolio.accounts = all_accounts
        portfolio.account_count = len(all_accounts)
        portfolio.institution_count = len(institutions)
        portfolio = self._compute_totals(portfolio)
        return portfolio

    def _compute_totals(self, portfolio: AggregatedPortfolio) -> AggregatedPortfolio:
        """Compute aggregate balances and net worth."""
        cash = investments = retirement = cc_debt = loan_debt = 0.0

        for acct in portfolio.accounts:
            bal = acct.current_balance
            cat = acct.category
            if cat in (AccountCategory.CHECKING, AccountCategory.SAVINGS):
                cash += bal
            elif cat == AccountCategory.BROKERAGE:
                investments += bal
            elif cat == AccountCategory.RETIREMENT:
                retirement += bal
            elif cat == AccountCategory.CREDIT_CARD:
                cc_debt += max(bal, 0)
            elif cat in (AccountCategory.LOAN, AccountCategory.MORTGAGE):
                loan_debt += max(bal, 0)

        portfolio.total_cash = round(cash, 2)
        portfolio.total_investments = round(investments, 2)
        portfolio.total_retirement = round(retirement, 2)
        portfolio.total_credit_card_debt = round(cc_debt, 2)
        portfolio.total_loan_debt = round(loan_debt, 2)
        portfolio.total_assets = round(cash + investments + retirement, 2)
        portfolio.total_liabilities = round(cc_debt + loan_debt, 2)
        portfolio.net_worth = round(portfolio.total_assets - portfolio.total_liabilities, 2)
        return portfolio

    async def refresh_balances(
        self,
        portfolio: AggregatedPortfolio,
    ) -> AggregatedPortfolio:
        """Refresh real-time balances for all accounts."""
        inst_map = {inst.institution_id: inst for inst in portfolio.institutions}
        for acct in portfolio.accounts:
            inst = inst_map.get(acct.institution_id)
            if not inst:
                continue
            try:
                balances = await self.client.get_balance(inst.access_token, [acct.account_id])
                if balances:
                    acct.current_balance = balances[0].current_balance or 0.0
                    acct.available_balance = balances[0].available_balance
                    acct.last_updated = datetime.utcnow()
            except Exception as e:
                logger.warning(f"Balance refresh failed for {acct.name}: {e}")

        return self._compute_totals(portfolio)

    def get_accounts_by_category(
        self,
        portfolio: AggregatedPortfolio,
        category: AccountCategory,
    ) -> List[EnrichedAccount]:
        return [a for a in portfolio.accounts if a.category == category]

    def get_institution_summary(
        self, portfolio: AggregatedPortfolio
    ) -> List[Dict[str, Any]]:
        """Per-institution balance summary."""
        summary: Dict[str, Dict[str, Any]] = {}
        for acct in portfolio.accounts:
            inst_id = acct.institution_id
            if inst_id not in summary:
                summary[inst_id] = {
                    "institution_name": acct.institution_name,
                    "accounts": 0,
                    "total_balance": 0.0,
                    "assets": 0.0,
                    "liabilities": 0.0,
                }
            summary[inst_id]["accounts"] += 1
            if acct.is_asset:
                summary[inst_id]["assets"] += acct.current_balance
                summary[inst_id]["total_balance"] += acct.current_balance
            elif acct.is_liability:
                summary[inst_id]["liabilities"] += acct.current_balance
        return list(summary.values())
