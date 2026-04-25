"""
Plaid API Client — Core integration layer for SintraPrime banking intelligence.
Supports all Plaid products: Transactions, Auth, Identity, Assets, Investments,
Liabilities, Credit Details, and Webhooks.
"""

import os
import logging
import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from functools import wraps
import json

from pydantic import BaseModel, Field, SecretStr
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.asset_report_create_request import AssetReportCreateRequest
from plaid.model.asset_report_get_request import AssetReportGetRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

logger = logging.getLogger(__name__)


class PlaidEnvironment(str, Enum):
    SANDBOX = "sandbox"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class PlaidConfig(BaseModel):
    client_id: str = Field(..., description="Plaid Client ID")
    secret: SecretStr = Field(..., description="Plaid Secret Key")
    environment: PlaidEnvironment = Field(default=PlaidEnvironment.SANDBOX)
    redirect_uri: Optional[str] = None
    webhook_url: Optional[str] = None

    class Config:
        use_enum_values = True

    @classmethod
    def from_env(cls) -> "PlaidConfig":
        return cls(
            client_id=os.environ["PLAID_CLIENT_ID"],
            secret=os.environ["PLAID_SECRET"],
            environment=PlaidEnvironment(os.getenv("PLAID_ENV", "sandbox")),
            redirect_uri=os.getenv("PLAID_REDIRECT_URI"),
            webhook_url=os.getenv("PLAID_WEBHOOK_URL"),
        )


class AccountBalance(BaseModel):
    account_id: str
    name: str
    official_name: Optional[str] = None
    account_type: str
    account_subtype: Optional[str] = None
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None
    credit_limit: Optional[float] = None
    currency: str = "USD"
    institution_name: Optional[str] = None
    mask: Optional[str] = None


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    date: date
    name: str
    merchant_name: Optional[str] = None
    category: Optional[List[str]] = None
    category_id: Optional[str] = None
    pending: bool = False
    currency: str = "USD"
    payment_channel: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    authorized_date: Optional[date] = None
    personal_finance_category: Optional[Dict[str, str]] = None


class InvestmentHolding(BaseModel):
    account_id: str
    security_id: str
    institution_value: Optional[float] = None
    institution_price: Optional[float] = None
    quantity: Optional[float] = None
    cost_basis: Optional[float] = None
    security_name: Optional[str] = None
    ticker_symbol: Optional[str] = None
    security_type: Optional[str] = None
    currency: str = "USD"


class LiabilityAccount(BaseModel):
    account_id: str
    name: str
    account_type: str
    current_balance: float
    apr: Optional[float] = None
    last_payment_amount: Optional[float] = None
    last_payment_date: Optional[date] = None
    minimum_payment: Optional[float] = None
    next_payment_due_date: Optional[date] = None
    payoff_balance: Optional[float] = None
    origination_date: Optional[date] = None
    origination_principal: Optional[float] = None


class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: datetime
    request_id: str


class ExchangeTokenResponse(BaseModel):
    access_token: str
    item_id: str
    request_id: str


class WebhookEvent(BaseModel):
    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[Dict[str, Any]] = None
    new_transactions: Optional[int] = None
    removed_transactions: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def retry_on_rate_limit(max_retries: int = 3, backoff_factor: float = 2.0):
    """Decorator to retry Plaid calls on rate limit errors."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except plaid.ApiException as e:
                    if e.status == 429:
                        wait = backoff_factor ** attempt
                        logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait)
                        last_error = e
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


class PlaidClient:
    """
    Full-featured async Plaid API client.
    Wraps all Plaid product endpoints used by SintraPrime.
    """

    ENV_HOSTS = {
        PlaidEnvironment.SANDBOX: plaid.Environment.Sandbox,
        PlaidEnvironment.DEVELOPMENT: plaid.Environment.Sandbox,
        PlaidEnvironment.PRODUCTION: plaid.Environment.Production,
    }

    SUPPORTED_PRODUCTS = [
        Products("transactions"),
        Products("auth"),
        Products("identity"),
        Products("investments"),
        Products("liabilities"),
    ]

    def __init__(self, config: Optional[PlaidConfig] = None):
        self.config = config or PlaidConfig.from_env()
        env_key = PlaidEnvironment(self.config.environment)
        configuration = plaid.Configuration(
            host=self.ENV_HOSTS[env_key],
            api_key={
                "clientId": self.config.client_id,
                "secret": self.config.secret.get_secret_value(),
            },
        )
        api_client = plaid.ApiClient(configuration)
        self._client = plaid_api.PlaidApi(api_client)
        logger.info(f"PlaidClient initialized in {self.config.environment} environment")

    # ─── Link Token Flow ──────────────────────────────────────────────────────

    async def create_link_token(
        self,
        user_id: str,
        products: Optional[List[str]] = None,
        country_codes: Optional[List[str]] = None,
        language: str = "en",
        redirect_uri: Optional[str] = None,
    ) -> LinkTokenResponse:
        """Create a Plaid Link token to initialize the Link flow on the frontend."""
        products_list = [Products(p) for p in (products or ["transactions", "auth", "identity", "investments", "liabilities"])]
        countries = [CountryCode(c) for c in (country_codes or ["US"])]

        request = LinkTokenCreateRequest(
            products=products_list,
            client_name="SintraPrime Financial",
            country_codes=countries,
            language=language,
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
            **({"redirect_uri": redirect_uri or self.config.redirect_uri} if (redirect_uri or self.config.redirect_uri) else {}),
            **({"webhook": self.config.webhook_url} if self.config.webhook_url else {}),
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.link_token_create, request
        )
        logger.info(f"Link token created for user {user_id}")
        return LinkTokenResponse(
            link_token=response["link_token"],
            expiration=response["expiration"],
            request_id=response["request_id"],
        )

    async def exchange_public_token(self, public_token: str) -> ExchangeTokenResponse:
        """Exchange public token from Link for a permanent access token."""
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.item_public_token_exchange, request
        )
        logger.info(f"Exchanged public token → item_id={response['item_id']}")
        return ExchangeTokenResponse(
            access_token=response["access_token"],
            item_id=response["item_id"],
            request_id=response["request_id"],
        )

    # ─── Accounts ─────────────────────────────────────────────────────────────

    @retry_on_rate_limit()
    async def get_accounts(self, access_token: str) -> List[AccountBalance]:
        """Retrieve all linked accounts with current balances."""
        request = AccountsGetRequest(access_token=access_token)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.accounts_get, request
        )
        accounts = []
        for acct in response["accounts"]:
            balances = acct.get("balances", {})
            accounts.append(AccountBalance(
                account_id=acct["account_id"],
                name=acct["name"],
                official_name=acct.get("official_name"),
                account_type=str(acct["type"]),
                account_subtype=str(acct.get("subtype", "")),
                current_balance=balances.get("current"),
                available_balance=balances.get("available"),
                credit_limit=balances.get("limit"),
                currency=balances.get("iso_currency_code", "USD"),
                mask=acct.get("mask"),
            ))
        return accounts

    @retry_on_rate_limit()
    async def get_balance(
        self, access_token: str, account_ids: Optional[List[str]] = None
    ) -> List[AccountBalance]:
        """Get real-time balances (bypasses cache)."""
        options = {}
        if account_ids:
            from plaid.model.accounts_balance_get_request_options import AccountsBalanceGetRequestOptions
            options = {"options": AccountsBalanceGetRequestOptions(account_ids=account_ids)}
        request = AccountsBalanceGetRequest(access_token=access_token, **options)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.accounts_balance_get, request
        )
        return [
            AccountBalance(
                account_id=a["account_id"],
                name=a["name"],
                official_name=a.get("official_name"),
                account_type=str(a["type"]),
                account_subtype=str(a.get("subtype", "")),
                current_balance=a["balances"].get("current"),
                available_balance=a["balances"].get("available"),
                credit_limit=a["balances"].get("limit"),
                currency=a["balances"].get("iso_currency_code", "USD"),
            )
            for a in response["accounts"]
        ]

    # ─── Transactions ─────────────────────────────────────────────────────────

    @retry_on_rate_limit()
    async def get_transactions(
        self,
        access_token: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[str]] = None,
        count: int = 500,
        offset: int = 0,
    ) -> Tuple[List[Transaction], int]:
        """
        Retrieve transactions with pagination.
        Returns (transactions, total_count).
        Defaults to last 24 months.
        """
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=730))

        from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
        options = TransactionsGetRequestOptions(
            count=min(count, 500),
            offset=offset,
            **({"account_ids": account_ids} if account_ids else {}),
        )
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
            options=options,
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.transactions_get, request
        )
        txns = [self._parse_transaction(t) for t in response["transactions"]]
        return txns, response["total_transactions"]

    async def get_all_transactions(
        self,
        access_token: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[str]] = None,
    ) -> List[Transaction]:
        """Paginate through ALL transactions automatically."""
        all_txns: List[Transaction] = []
        offset = 0
        while True:
            txns, total = await self.get_transactions(
                access_token, start_date, end_date, account_ids, count=500, offset=offset
            )
            all_txns.extend(txns)
            offset += len(txns)
            if offset >= total:
                break
            await asyncio.sleep(0.2)  # gentle rate limiting
        logger.info(f"Fetched {len(all_txns)} total transactions")
        return all_txns

    def _parse_transaction(self, t: Dict[str, Any]) -> Transaction:
        return Transaction(
            transaction_id=t["transaction_id"],
            account_id=t["account_id"],
            amount=t["amount"],
            date=t["date"],
            name=t["name"],
            merchant_name=t.get("merchant_name"),
            category=t.get("category"),
            category_id=t.get("category_id"),
            pending=t.get("pending", False),
            currency=t.get("iso_currency_code", "USD"),
            payment_channel=t.get("payment_channel"),
            location=t.get("location"),
            logo_url=t.get("logo_url"),
            website=t.get("website"),
            authorized_date=t.get("authorized_date"),
            personal_finance_category=t.get("personal_finance_category"),
        )

    async def refresh_transactions(self, access_token: str) -> bool:
        """Trigger a transaction refresh (Plaid fires webhook when ready)."""
        request = TransactionsRefreshRequest(access_token=access_token)
        await asyncio.get_event_loop().run_in_executor(
            None, self._client.transactions_refresh, request
        )
        logger.info("Transaction refresh triggered")
        return True

    # ─── Investments ──────────────────────────────────────────────────────────

    @retry_on_rate_limit()
    async def get_investments(
        self, access_token: str, account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get investment holdings and recent transactions."""
        from plaid.model.investments_holdings_get_request_options import InvestmentsHoldingsGetRequestOptions
        options = {}
        if account_ids:
            options["options"] = InvestmentsHoldingsGetRequestOptions(account_ids=account_ids)

        holdings_req = InvestmentsHoldingsGetRequest(access_token=access_token, **options)
        holdings_resp = await asyncio.get_event_loop().run_in_executor(
            None, self._client.investments_holdings_get, holdings_req
        )

        securities = {s["security_id"]: s for s in holdings_resp.get("securities", [])}
        holdings = []
        for h in holdings_resp.get("holdings", []):
            sec = securities.get(h.get("security_id"), {})
            holdings.append(InvestmentHolding(
                account_id=h["account_id"],
                security_id=h["security_id"],
                institution_value=h.get("institution_value"),
                institution_price=h.get("institution_price"),
                quantity=h.get("quantity"),
                cost_basis=h.get("cost_basis"),
                security_name=sec.get("name"),
                ticker_symbol=sec.get("ticker_symbol"),
                security_type=str(sec.get("type", "")),
                currency=h.get("iso_currency_code", "USD"),
            ))

        # Investment transactions (last 2 years)
        end = date.today()
        start = end - timedelta(days=730)
        inv_txn_req = InvestmentsTransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
        )
        inv_txn_resp = await asyncio.get_event_loop().run_in_executor(
            None, self._client.investments_transactions_get, inv_txn_req
        )

        return {
            "holdings": holdings,
            "accounts": holdings_resp.get("accounts", []),
            "investment_transactions": inv_txn_resp.get("investment_transactions", []),
            "securities": list(securities.values()),
        }

    # ─── Liabilities ──────────────────────────────────────────────────────────

    @retry_on_rate_limit()
    async def get_liabilities(self, access_token: str) -> Dict[str, Any]:
        """Retrieve all liability accounts: credit cards, mortgages, student loans."""
        request = LiabilitiesGetRequest(access_token=access_token)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.liabilities_get, request
        )
        liabilities = response.get("liabilities", {})
        return {
            "accounts": response.get("accounts", []),
            "credit": liabilities.get("credit", []),
            "mortgage": liabilities.get("mortgage", []),
            "student": liabilities.get("student", []),
        }

    # ─── Identity ─────────────────────────────────────────────────────────────

    @retry_on_rate_limit()
    async def get_identity(self, access_token: str) -> Dict[str, Any]:
        """Get account owner identity information."""
        request = IdentityGetRequest(access_token=access_token)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.identity_get, request
        )
        return {
            "accounts": response.get("accounts", []),
            "item": response.get("item", {}),
        }

    # ─── Asset Reports ────────────────────────────────────────────────────────

    async def create_asset_report(
        self, access_tokens: List[str], days_requested: int = 730
    ) -> str:
        """Create an asset report for lending purposes. Returns asset_report_token."""
        request = AssetReportCreateRequest(
            access_tokens=access_tokens,
            days_requested=days_requested,
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.asset_report_create, request
        )
        return response["asset_report_token"]

    async def get_asset_report(self, asset_report_token: str) -> Dict[str, Any]:
        """Poll for completed asset report."""
        request = AssetReportGetRequest(asset_report_token=asset_report_token)
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._client.asset_report_get, request
        )
        return response.get("report", {})

    # ─── Webhooks ─────────────────────────────────────────────────────────────

    async def handle_webhook(
        self, webhook_type: str, webhook_code: str, data: Dict[str, Any]
    ) -> WebhookEvent:
        """
        Process incoming Plaid webhooks.
        Dispatches to appropriate handler by type and code.
        """
        event = WebhookEvent(
            webhook_type=webhook_type,
            webhook_code=webhook_code,
            item_id=data.get("item_id", ""),
            error=data.get("error"),
            new_transactions=data.get("new_transactions"),
            removed_transactions=data.get("removed_transactions"),
        )

        handler = self._webhook_handlers.get((webhook_type, webhook_code))
        if handler:
            await handler(event, data)
        else:
            logger.info(f"Unhandled webhook: {webhook_type}/{webhook_code}")

        return event

    _webhook_handlers: Dict[Tuple[str, str], Any] = {}

    def register_webhook_handler(self, webhook_type: str, webhook_code: str):
        """Decorator to register a webhook handler."""
        def decorator(func):
            self._webhook_handlers[(webhook_type, webhook_code)] = func
            return func
        return decorator
