"""
Tests for PlaidClient — mocked API responses, no real Plaid calls.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_config():
    from integrations.banking.plaid_client import PlaidConfig, PlaidEnvironment
    return PlaidConfig(
        client_id="test_client_id",
        secret="test_secret_key",
        environment=PlaidEnvironment.SANDBOX,
    )


@pytest.fixture
def mock_plaid_client(mock_config):
    """PlaidClient with mocked internal API client."""
    with patch("integrations.banking.plaid_client.plaid_api.PlaidApi"):
        with patch("integrations.banking.plaid_client.plaid.ApiClient"):
            with patch("integrations.banking.plaid_client.plaid.Configuration"):
                from integrations.banking.plaid_client import PlaidClient
                client = PlaidClient(config=mock_config)
                client._client = MagicMock()
                return client


MOCK_ACCOUNTS_RESPONSE = {
    "accounts": [
        {
            "account_id": "acct_001",
            "name": "Chase Checking",
            "official_name": "Chase Total Checking",
            "type": "depository",
            "subtype": "checking",
            "mask": "1234",
            "balances": {
                "current": 5_000.00,
                "available": 4_800.00,
                "limit": None,
                "iso_currency_code": "USD",
            },
        },
        {
            "account_id": "acct_002",
            "name": "Chase Sapphire",
            "official_name": "Chase Sapphire Preferred",
            "type": "credit",
            "subtype": "credit card",
            "mask": "5678",
            "balances": {
                "current": 1_200.00,
                "available": 8_800.00,
                "limit": 10_000.00,
                "iso_currency_code": "USD",
            },
        },
    ],
    "item": {"item_id": "item_001"},
    "request_id": "req_001",
}

MOCK_TRANSACTIONS_RESPONSE = {
    "transactions": [
        {
            "transaction_id": "txn_001",
            "account_id": "acct_001",
            "amount": 85.32,
            "date": date(2025, 3, 15),
            "name": "Whole Foods Market",
            "merchant_name": "Whole Foods",
            "category": ["Food and Drink", "Groceries"],
            "category_id": "21007",
            "pending": False,
            "iso_currency_code": "USD",
            "payment_channel": "in store",
            "location": {"city": "San Francisco", "state": "CA"},
            "logo_url": None,
            "website": "wholefoods.com",
            "authorized_date": date(2025, 3, 15),
            "personal_finance_category": {"primary": "FOOD_AND_DRINK", "detailed": "GROCERIES"},
        },
        {
            "transaction_id": "txn_002",
            "account_id": "acct_001",
            "amount": -3_500.00,
            "date": date(2025, 3, 1),
            "name": "Payroll Direct Deposit",
            "merchant_name": None,
            "category": ["Transfer", "Credit"],
            "category_id": "21009",
            "pending": False,
            "iso_currency_code": "USD",
            "payment_channel": "online",
            "location": {},
            "logo_url": None,
            "website": None,
            "authorized_date": date(2025, 3, 1),
            "personal_finance_category": None,
        },
    ],
    "total_transactions": 2,
    "item": {"item_id": "item_001"},
    "request_id": "req_002",
}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestPlaidConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("PLAID_CLIENT_ID", "env_client")
        monkeypatch.setenv("PLAID_SECRET", "env_secret")
        monkeypatch.setenv("PLAID_ENV", "sandbox")
        from integrations.banking.plaid_client import PlaidConfig
        config = PlaidConfig.from_env()
        assert config.client_id == "env_client"
        assert config.environment == "sandbox"

    def test_default_environment(self, mock_config):
        assert mock_config.environment == "sandbox"

    def test_secret_is_masked(self, mock_config):
        repr_str = repr(mock_config)
        assert "test_secret_key" not in repr_str


class TestPlaidClientAccounts:
    @pytest.mark.asyncio
    async def test_get_accounts_returns_list(self, mock_plaid_client):
        mock_plaid_client._client.accounts_get.return_value = MOCK_ACCOUNTS_RESPONSE
        accounts = await mock_plaid_client.get_accounts("access-sandbox-token")
        assert len(accounts) == 2

    @pytest.mark.asyncio
    async def test_get_accounts_checking(self, mock_plaid_client):
        mock_plaid_client._client.accounts_get.return_value = MOCK_ACCOUNTS_RESPONSE
        accounts = await mock_plaid_client.get_accounts("access-sandbox-token")
        checking = next(a for a in accounts if "checking" in a.account_type.lower() or "checking" in (a.account_subtype or "").lower())
        assert checking.current_balance == 5_000.00
        assert checking.mask == "1234"

    @pytest.mark.asyncio
    async def test_get_accounts_credit_card(self, mock_plaid_client):
        mock_plaid_client._client.accounts_get.return_value = MOCK_ACCOUNTS_RESPONSE
        accounts = await mock_plaid_client.get_accounts("access-sandbox-token")
        credit = next(a for a in accounts if a.credit_limit is not None)
        assert credit.credit_limit == 10_000.00
        assert credit.available_balance == 8_800.00

    @pytest.mark.asyncio
    async def test_get_accounts_empty(self, mock_plaid_client):
        mock_plaid_client._client.accounts_get.return_value = {"accounts": [], "item": {}, "request_id": "r"}
        accounts = await mock_plaid_client.get_accounts("access-sandbox-token")
        assert accounts == []


class TestPlaidClientTransactions:
    @pytest.mark.asyncio
    async def test_get_transactions_returns_tuple(self, mock_plaid_client):
        mock_plaid_client._client.transactions_get.return_value = MOCK_TRANSACTIONS_RESPONSE
        txns, total = await mock_plaid_client.get_transactions("access-token")
        assert total == 2
        assert len(txns) == 2

    @pytest.mark.asyncio
    async def test_transaction_fields(self, mock_plaid_client):
        mock_plaid_client._client.transactions_get.return_value = MOCK_TRANSACTIONS_RESPONSE
        txns, _ = await mock_plaid_client.get_transactions("access-token")
        expense = next(t for t in txns if t.amount > 0)
        assert expense.merchant_name == "Whole Foods"
        assert expense.amount == 85.32
        assert expense.currency == "USD"

    @pytest.mark.asyncio
    async def test_income_transaction(self, mock_plaid_client):
        mock_plaid_client._client.transactions_get.return_value = MOCK_TRANSACTIONS_RESPONSE
        txns, _ = await mock_plaid_client.get_transactions("access-token")
        income = next(t for t in txns if t.amount < 0)
        assert income.amount == -3_500.00

    @pytest.mark.asyncio
    async def test_get_all_transactions_paginates(self, mock_plaid_client):
        """Verify pagination stops when offset >= total."""
        page1 = {**MOCK_TRANSACTIONS_RESPONSE, "total_transactions": 2}
        mock_plaid_client._client.transactions_get.return_value = page1
        all_txns = await mock_plaid_client.get_all_transactions("access-token")
        assert len(all_txns) == 2


class TestPlaidClientLinkFlow:
    @pytest.mark.asyncio
    async def test_create_link_token(self, mock_plaid_client):
        mock_plaid_client._client.link_token_create.return_value = {
            "link_token": "link-sandbox-abc123",
            "expiration": datetime.utcnow(),
            "request_id": "req_link_001",
        }
        result = await mock_plaid_client.create_link_token(user_id="user_001")
        assert result.link_token.startswith("link-")
        assert result.request_id == "req_link_001"

    @pytest.mark.asyncio
    async def test_exchange_public_token(self, mock_plaid_client):
        mock_plaid_client._client.item_public_token_exchange.return_value = {
            "access_token": "access-sandbox-xyz789",
            "item_id": "item_001",
            "request_id": "req_exchange_001",
        }
        result = await mock_plaid_client.exchange_public_token("public-sandbox-token")
        assert result.access_token == "access-sandbox-xyz789"
        assert result.item_id == "item_001"


class TestWebhookHandler:
    @pytest.mark.asyncio
    async def test_handle_webhook_transactions_default(self, mock_plaid_client):
        event = await mock_plaid_client.handle_webhook(
            webhook_type="TRANSACTIONS",
            webhook_code="DEFAULT_UPDATE",
            data={
                "item_id": "item_001",
                "new_transactions": 5,
            },
        )
        assert event.webhook_type == "TRANSACTIONS"
        assert event.new_transactions == 5

    @pytest.mark.asyncio
    async def test_handle_webhook_error(self, mock_plaid_client):
        event = await mock_plaid_client.handle_webhook(
            webhook_type="ITEM",
            webhook_code="ERROR",
            data={
                "item_id": "item_001",
                "error": {"error_code": "ITEM_LOGIN_REQUIRED"},
            },
        )
        assert event.error is not None
        assert event.error["error_code"] == "ITEM_LOGIN_REQUIRED"
