"""
Tests for TransactionEngine — categorization, recurring detection, anomaly alerts, search.
"""

import pytest
from datetime import date
from typing import List

from integrations.banking.transaction_engine import (
    TransactionEngine,
    EnrichedTransaction,
    MasterCategory,
    RecurringTransactionGroup,
)


def make_txn(
    txn_id: str,
    name: str,
    amount: float,
    category: list = None,
    txn_date: date = None,
    merchant: str = None,
) -> dict:
    return {
        "transaction_id": txn_id,
        "account_id": "acct_001",
        "amount": amount,
        "date": txn_date or date(2025, 3, 15),
        "name": name,
        "merchant_name": merchant,
        "category": category or [],
        "category_id": "21007",
        "pending": False,
        "iso_currency_code": "USD",
        "payment_channel": "online",
        "location": {},
        "logo_url": None,
        "website": None,
        "authorized_date": txn_date or date(2025, 3, 15),
        "personal_finance_category": None,
    }


@pytest.fixture
def engine():
    return TransactionEngine()


@pytest.fixture
def sample_transactions(engine):
    raw = [
        make_txn("t1", "Whole Foods Market", 87.32, ["Food and Drink", "Groceries"], merchant="Whole Foods"),
        make_txn("t2", "Netflix", 15.99, ["Service", "Subscription"], merchant="Netflix"),
        make_txn("t3", "Payroll", -4_500.00, ["Transfer", "Credit"]),
        make_txn("t4", "Shell Gas Station", 58.00, ["Travel", "Gas Stations"], merchant="Shell"),
        make_txn("t5", "Amazon", 123.45, ["Shops", "General"]),
        make_txn("t6", "Dr. Smith Office", 250.00, ["Healthcare", "Doctors"]),
        make_txn("t7", "Spotify", 9.99, ["Service", "Subscription"], merchant="Spotify"),
        make_txn("t8", "Rent Payment", 2_200.00, ["Payment", "Rent"]),
    ]
    return [engine.enrich(t) for t in raw]


class TestEnrichment:
    def test_enrich_sets_master_category_food(self, engine):
        raw = make_txn("x1", "Trader Joe's", 55.00, ["Food and Drink", "Groceries"])
        txn = engine.enrich(raw)
        assert txn.master_category == MasterCategory.FOOD

    def test_enrich_sets_master_category_income(self, engine):
        raw = make_txn("x2", "Payroll Direct Deposit", -5_000.00, ["Transfer"])
        txn = engine.enrich(raw)
        assert txn.is_income is True

    def test_enrich_transportation(self, engine):
        raw = make_txn("x3", "Shell Gas Station", 65.00, ["Travel", "Gas Stations"])
        txn = engine.enrich(raw)
        assert txn.master_category == MasterCategory.TRANSPORTATION

    def test_enrich_subscription(self, engine):
        raw = make_txn("x4", "Netflix", 15.99, ["Service", "Subscription"])
        txn = engine.enrich(raw)
        assert txn.is_subscription is True

    def test_enrich_is_expense(self, engine):
        raw = make_txn("x5", "Starbucks", 6.50, ["Food and Drink", "Coffee Shop"])
        txn = engine.enrich(raw)
        assert txn.is_expense is True
        assert txn.is_income is False


class TestCategories:
    def test_all_master_categories_assigned(self, sample_transactions):
        for txn in sample_transactions:
            assert txn.master_category is not None

    def test_healthcare_category(self, engine):
        raw = make_txn("h1", "CVS Pharmacy", 34.99, ["Healthcare", "Pharmacies"])
        txn = engine.enrich(raw)
        assert txn.master_category == MasterCategory.HEALTHCARE

    def test_housing_category(self, engine):
        raw = make_txn("r1", "Rent Payment", 2_100.00, ["Payment", "Rent"])
        txn = engine.enrich(raw)
        assert txn.master_category == MasterCategory.HOUSING

    def test_entertainment_category(self, engine):
        raw = make_txn("e1", "AMC Theaters", 28.00, ["Entertainment", "Cinema"])
        txn = engine.enrich(raw)
        assert txn.master_category == MasterCategory.ENTERTAINMENT


class TestRecurringDetection:
    def test_detects_monthly_subscription(self, engine):
        txns = []
        for i in range(3):
            raw = make_txn(
                f"sub_{i}",
                "Netflix",
                15.99,
                ["Service", "Subscription"],
                txn_date=date(2025, 1 + i, 1),
                merchant="Netflix",
            )
            txns.append(engine.enrich(raw))

        groups = engine.detect_recurring(txns)
        netflix_groups = [g for g in groups if "netflix" in g.merchant_name.lower()]
        assert len(netflix_groups) >= 1
        assert netflix_groups[0].frequency == "monthly"

    def test_detects_annual_subscription(self, engine):
        txns = [
            engine.enrich(make_txn("ann1", "Amazon Prime", 139.00, txn_date=date(2023, 1, 15))),
            engine.enrich(make_txn("ann2", "Amazon Prime", 139.00, txn_date=date(2024, 1, 15))),
            engine.enrich(make_txn("ann3", "Amazon Prime", 139.00, txn_date=date(2025, 1, 15))),
        ]
        groups = engine.detect_recurring(txns)
        amazon_groups = [g for g in groups if "amazon" in g.merchant_name.lower()]
        assert any(g.frequency in ("annual", "monthly") for g in amazon_groups)


class TestAnomalyDetection:
    def test_flags_large_transaction(self, engine):
        baseline = [
            engine.enrich(make_txn(f"g{i}", "Grocery Store", 75.00 + i * 2)) for i in range(10)
        ]
        anomaly_raw = make_txn("a1", "Grocery Store", 1_500.00)
        result = engine.detect_anomalies(baseline + [engine.enrich(anomaly_raw)])
        flagged_ids = [t.transaction_id for t in result]
        assert "a1" in flagged_ids

    def test_no_false_positives_on_normal_spending(self, engine):
        txns = [
            engine.enrich(make_txn(f"n{i}", "Starbucks", 5.50 + (i % 3))) for i in range(20)
        ]
        anomalies = engine.detect_anomalies(txns)
        assert len(anomalies) == 0


class TestSearch:
    def test_search_by_merchant(self, sample_transactions, engine):
        results = engine.search(sample_transactions, query="amazon")
        assert any("amazon" in t.name.lower() for t in results)

    def test_search_by_category(self, sample_transactions, engine):
        results = engine.search(sample_transactions, category=MasterCategory.FOOD)
        assert all(t.master_category == MasterCategory.FOOD for t in results)

    def test_search_by_min_amount(self, sample_transactions, engine):
        results = engine.search(sample_transactions, min_amount=200)
        assert all(abs(t.amount) >= 200 for t in results if t.is_expense)

    def test_search_by_date_range(self, sample_transactions, engine):
        results = engine.search(
            sample_transactions,
            date_from=date(2025, 3, 1),
            date_to=date(2025, 3, 31),
        )
        assert all(date(2025, 3, 1) <= t.date <= date(2025, 3, 31) for t in results)


class TestSummary:
    def test_monthly_summary_totals(self, sample_transactions, engine):
        summary = engine.monthly_summary(sample_transactions, year=2025, month=3)
        assert summary.total_expenses >= 0
        assert summary.total_income >= 0

    def test_category_breakdown(self, sample_transactions, engine):
        breakdown = engine.category_breakdown(sample_transactions)
        assert isinstance(breakdown, dict)
        assert all(isinstance(v, float) for v in breakdown.values())
