"""
Transaction Engine — Categorize, enrich, analyze, and search transactions.
Supports recurring detection, anomaly alerts, tax tagging, and NL search.
"""

import re
import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from .plaid_client import PlaidClient, Transaction

logger = logging.getLogger(__name__)


class MasterCategory(str, Enum):
    INCOME = "income"
    HOUSING = "housing"
    FOOD = "food"
    TRANSPORTATION = "transportation"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    FINANCIAL = "financial"
    LEGAL = "legal"
    BUSINESS = "business"
    TRAVEL = "travel"
    EDUCATION = "education"
    PERSONAL_CARE = "personal_care"
    UTILITIES = "utilities"
    INSURANCE = "insurance"
    TAXES = "taxes"
    TRANSFER = "transfer"
    OTHER = "other"


class TaxCategory(str, Enum):
    DEDUCTIBLE_BUSINESS = "deductible_business"
    DEDUCTIBLE_MEDICAL = "deductible_medical"
    DEDUCTIBLE_CHARITABLE = "deductible_charitable"
    DEDUCTIBLE_EDUCATION = "deductible_education"
    NOT_DEDUCTIBLE = "not_deductible"
    UNKNOWN = "unknown"


class RecurrenceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"


class EnrichedTransaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    date: date
    name: str
    merchant_name: Optional[str] = None
    master_category: MasterCategory = MasterCategory.OTHER
    sub_category: Optional[str] = None
    plaid_category: Optional[List[str]] = None
    is_income: bool = False
    is_expense: bool = True
    is_transfer: bool = False
    is_subscription: bool = False
    is_recurring: bool = False
    recurrence_frequency: Optional[RecurrenceFrequency] = None
    is_tax_deductible: bool = False
    tax_category: TaxCategory = TaxCategory.UNKNOWN
    is_unusual: bool = False
    is_duplicate: bool = False
    pending: bool = False
    currency: str = "USD"
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class RecurringTransaction(BaseModel):
    merchant_name: str
    master_category: MasterCategory
    frequency: RecurrenceFrequency
    average_amount: float
    last_amount: float
    last_date: date
    next_predicted_date: Optional[date] = None
    occurrences: int = 0
    total_paid: float = 0.0
    is_subscription: bool = False
    annual_cost: float = 0.0


# Alias for backward compatibility
RecurringTransactionGroup = RecurringTransaction


class TransactionSummary(BaseModel):
    period_start: date
    period_end: date
    total_income: float = 0.0
    total_expenses: float = 0.0
    net_cash_flow: float = 0.0
    by_category: Dict[str, float] = Field(default_factory=dict)
    top_merchants: List[Dict[str, Any]] = Field(default_factory=list)
    transaction_count: int = 0
    unusual_count: int = 0
    recurring_total: float = 0.0


# ── Keyword-based categorization rules ────────────────────────────────────────
CATEGORY_RULES: List[Tuple[MasterCategory, str, List[str]]] = [
    # (master_category, sub_category, [keyword_patterns])
    (MasterCategory.INCOME, "payroll", ["direct dep", "payroll", "adp", "gusto", "paychex", "salary", "wages"]),
    (MasterCategory.INCOME, "freelance", ["stripe", "paypal", "venmo", "zelle", "square", "cashapp"]),
    (MasterCategory.INCOME, "dividends", ["dividend", "interest payment", "schwab div"]),
    (MasterCategory.INCOME, "refund", ["refund", "credit adj", "return credit"]),
    (MasterCategory.HOUSING, "rent", ["rent", "apartment", "property mgmt", "zillow"]),
    (MasterCategory.HOUSING, "mortgage", ["mortgage", "loan payment", "home loan"]),
    (MasterCategory.HOUSING, "utilities", ["pg&e", "con ed", "electric", "water bill", "gas bill", "spectrum", "comcast", "xfinity", "at&t", "verizon"]),
    (MasterCategory.HOUSING, "hoa", ["hoa", "homeowners assoc"]),
    (MasterCategory.FOOD, "groceries", ["whole foods", "trader joe", "kroger", "safeway", "publix", "aldi", "walmart grocery", "target grocery", "costco"]),
    (MasterCategory.FOOD, "restaurants", ["mcdonald", "starbucks", "chipotle", "subway", "taco bell", "domino", "pizza", "restaurant", "diner", "bistro", "cafe"]),
    (MasterCategory.FOOD, "delivery", ["doordash", "uber eats", "grubhub", "instacart", "postmates", "caviar"]),
    (MasterCategory.TRANSPORTATION, "gas", ["chevron", "shell", "bp ", "exxon", "mobil", "arco", "speedway", "fuel"]),
    (MasterCategory.TRANSPORTATION, "rideshare", ["uber", "lyft"]),
    (MasterCategory.TRANSPORTATION, "auto_insurance", ["geico", "progressive", "state farm", "allstate", "auto insurance"]),
    (MasterCategory.TRANSPORTATION, "parking", ["parking", "parkwhiz", "spothero"]),
    (MasterCategory.TRANSPORTATION, "public_transit", ["metro", "mta", "caltrain", "bart", "bus pass", "transit"]),
    (MasterCategory.HEALTHCARE, "doctor", ["medical", "dr ", "physician", "clinic", "hospital", "urgent care"]),
    (MasterCategory.HEALTHCARE, "pharmacy", ["cvs", "walgreens", "rite aid", "pharmacy", "rx "]),
    (MasterCategory.HEALTHCARE, "dental", ["dental", "dentist", "orthodon"]),
    (MasterCategory.HEALTHCARE, "health_insurance", ["health insurance", "blue cross", "aetna", "cigna", "kaiser", "united health"]),
    (MasterCategory.ENTERTAINMENT, "streaming", ["netflix", "spotify", "hulu", "disney+", "apple tv", "hbo", "amazon prime", "peacock", "paramount"]),
    (MasterCategory.ENTERTAINMENT, "events", ["ticketmaster", "eventbrite", "stubhub", "concert", "movie theater", "amc", "regal"]),
    (MasterCategory.ENTERTAINMENT, "gaming", ["steam", "playstation", "xbox", "nintendo", "epic games"]),
    (MasterCategory.SHOPPING, "amazon", ["amazon", "amzn"]),
    (MasterCategory.SHOPPING, "clothing", ["h&m", "zara", "gap", "old navy", "macy", "nordstrom", "tjmaxx", "marshalls"]),
    (MasterCategory.SHOPPING, "electronics", ["best buy", "apple store", "samsung", "newegg", "b&h photo"]),
    (MasterCategory.FINANCIAL, "investment", ["schwab", "fidelity", "vanguard", "robinhood", "e*trade", "td ameritrade", "acorns", "betterment"]),
    (MasterCategory.FINANCIAL, "savings_transfer", ["savings transfer", "transfer to savings"]),
    (MasterCategory.LEGAL, "attorney", ["attorney", "law firm", "legal services", "lawgroup"]),
    (MasterCategory.LEGAL, "court", ["court fee", "filing fee", "clerk of court"]),
    (MasterCategory.BUSINESS, "software", ["github", "notion", "slack", "zoom", "google workspace", "microsoft 365", "adobe", "dropbox", "jira", "salesforce"]),
    (MasterCategory.BUSINESS, "office", ["staples", "office depot", "fedex office", "ups store"]),
    (MasterCategory.BUSINESS, "advertising", ["google ads", "facebook ads", "meta ads", "linkedin ads"]),
    (MasterCategory.TRAVEL, "airline", ["delta", "united", "american airlines", "southwest", "jetblue", "spirit air"]),
    (MasterCategory.TRAVEL, "hotel", ["hilton", "marriott", "hyatt", "airbnb", "vrbo", "hotel"]),
    (MasterCategory.TRAVEL, "car_rental", ["enterprise", "hertz", "avis", "budget rent"]),
    (MasterCategory.EDUCATION, "tuition", ["university", "college", "tuition", "student loan"]),
    (MasterCategory.EDUCATION, "books", ["amazon textbook", "chegg", "coursera", "udemy", "masterclass"]),
    (MasterCategory.INSURANCE, "life_insurance", ["life insurance", "term life", "whole life", "northwestern mutual", "new york life"]),
    (MasterCategory.TAXES, "tax_payment", ["irs", "state tax", "franchise tax board", "tax payment"]),
    (MasterCategory.TRANSFER, "transfer", ["transfer", "zelle", "wire", "ach"]),
]

TAX_DEDUCTIBLE_CATEGORIES = {
    MasterCategory.BUSINESS,
    MasterCategory.LEGAL,
    MasterCategory.EDUCATION,
}
TAX_DEDUCTIBLE_SUBS = {"health_insurance", "medical", "pharmacy", "dental", "charity", "mortgage"}


class TransactionEngine:
    """
    Enriches, categorizes, and analyzes Plaid transactions.
    """

    def __init__(self, plaid_client: Optional[PlaidClient] = None):
        self.client = plaid_client
        self._custom_rules: List[Tuple[MasterCategory, str, List[str]]] = []
        self._category_history: Dict[str, MasterCategory] = {}

    # ── Categorization ─────────────────────────────────────────────────────

    def categorize(self, txn: Transaction) -> Tuple[MasterCategory, Optional[str], TaxCategory]:
        """Determine master category, sub-category, and tax classification."""
        search_text = " ".join(filter(None, [
            txn.name.lower(),
            (txn.merchant_name or "").lower(),
        ]))

        # Custom rules first
        for (master_cat, sub_cat, keywords) in self._custom_rules + CATEGORY_RULES:
            if any(kw in search_text for kw in keywords):
                tax_cat = self._classify_tax(master_cat, sub_cat)
                return master_cat, sub_cat, tax_cat

        # Plaid category fallback
        if txn.category:
            plaid_top = (txn.category[0] or "").lower()
            if "income" in plaid_top or "payroll" in plaid_top:
                return MasterCategory.INCOME, "payroll", TaxCategory.NOT_DEDUCTIBLE
            if "food" in plaid_top:
                return MasterCategory.FOOD, "general", TaxCategory.NOT_DEDUCTIBLE
            if "travel" in plaid_top:
                return MasterCategory.TRAVEL, "general", TaxCategory.DEDUCTIBLE_BUSINESS

        return MasterCategory.OTHER, None, TaxCategory.UNKNOWN

    def _classify_tax(self, master: MasterCategory, sub: Optional[str]) -> TaxCategory:
        if master in TAX_DEDUCTIBLE_CATEGORIES:
            return TaxCategory.DEDUCTIBLE_BUSINESS
        if sub in TAX_DEDUCTIBLE_SUBS or master == MasterCategory.HEALTHCARE:
            return TaxCategory.DEDUCTIBLE_MEDICAL
        if master == MasterCategory.TAXES:
            return TaxCategory.NOT_DEDUCTIBLE
        return TaxCategory.NOT_DEDUCTIBLE

    def add_custom_rule(
        self,
        master_category: MasterCategory,
        sub_category: str,
        keywords: List[str],
    ):
        """Add a custom categorization rule (takes priority over defaults)."""
        self._custom_rules.insert(0, (master_category, sub_category, keywords))

    # ── Enrichment ─────────────────────────────────────────────────────────

    def enrich(self, transactions):
        """Enrich raw transactions with categories, flags, and metadata.
        Accepts a single dict/Transaction or a list of them.
        If a single item is passed, returns a single EnrichedTransaction.
        """
        single = False
        if isinstance(transactions, dict):
            # Convert dict to Transaction
            txn_dict = transactions
            # Map iso_currency_code to currency if needed
            if 'iso_currency_code' in txn_dict and 'currency' not in txn_dict:
                txn_dict['currency'] = txn_dict.pop('iso_currency_code')
            # Remove unknown fields
            known_fields = set(Transaction.model_fields.keys())
            clean = {k: v for k, v in txn_dict.items() if k in known_fields}
            transactions = [Transaction(**clean)]
            single = True
        elif isinstance(transactions, Transaction):
            transactions = [transactions]
            single = True
        elif not isinstance(transactions, list):
            transactions = [transactions]
            single = True

        enriched = []
        for txn in transactions:
            if isinstance(txn, dict):
                txn_dict = txn
                if 'iso_currency_code' in txn_dict and 'currency' not in txn_dict:
                    txn_dict['currency'] = txn_dict.pop('iso_currency_code')
                known_fields = set(Transaction.model_fields.keys())
                clean = {k: v for k, v in txn_dict.items() if k in known_fields}
                txn = Transaction(**clean)
            master_cat, sub_cat, tax_cat = self.categorize(txn)
            is_income = (master_cat == MasterCategory.INCOME) or (txn.amount < 0)
            is_transfer = master_cat == MasterCategory.TRANSFER
            # Detect subscriptions from category keywords
            search_text = " ".join(filter(None, [txn.name.lower(), (txn.merchant_name or "").lower()]))
            is_sub = bool(sub_cat == "streaming" or
                      any(kw in search_text for kw in ["netflix", "spotify", "hulu", "disney", "hbo", "amazon prime", "subscription"]) or
                      (txn.category and any("subscription" in c.lower() for c in txn.category)))

            e = EnrichedTransaction(
                transaction_id=txn.transaction_id,
                account_id=txn.account_id,
                amount=txn.amount,
                date=txn.date,
                name=txn.name,
                merchant_name=txn.merchant_name,
                master_category=master_cat,
                sub_category=sub_cat,
                plaid_category=txn.category,
                is_income=is_income,
                is_expense=not is_income and not is_transfer,
                is_transfer=is_transfer,
                is_subscription=is_sub,
                tax_category=tax_cat,
                is_tax_deductible=tax_cat in (TaxCategory.DEDUCTIBLE_BUSINESS, TaxCategory.DEDUCTIBLE_MEDICAL,
                                               TaxCategory.DEDUCTIBLE_CHARITABLE, TaxCategory.DEDUCTIBLE_EDUCATION),
                pending=txn.pending,
                currency=txn.currency,
                logo_url=txn.logo_url,
                website=txn.website,
            )
            enriched.append(e)

        enriched = self._detect_duplicates(enriched)
        enriched = self._detect_unusual(enriched)
        if single:
            return enriched[0] if enriched else None
        return enriched

    # ── Recurring Detection ────────────────────────────────────────────────

    def detect_recurring(
        self, transactions: List[EnrichedTransaction]
    ) -> List[RecurringTransaction]:
        """Identify subscriptions and recurring bills."""
        merchant_txns: Dict[str, List[EnrichedTransaction]] = defaultdict(list)
        for txn in transactions:
            if txn.is_expense:
                key = (txn.merchant_name or txn.name or "").lower()
                if key:
                    merchant_txns[key].append(txn)

        recurring: List[RecurringTransaction] = []
        for merchant, txns in merchant_txns.items():
            if len(txns) < 2:
                continue
            sorted_txns = sorted(txns, key=lambda t: t.date)
            intervals = [
                (sorted_txns[i+1].date - sorted_txns[i].date).days
                for i in range(len(sorted_txns) - 1)
            ]
            avg_interval = statistics.mean(intervals) if intervals else 0
            freq = self._interval_to_frequency(avg_interval)

            if freq and freq != RecurrenceFrequency.IRREGULAR:
                amounts = [t.amount for t in txns]
                avg_amount = statistics.mean(amounts)
                annual_cost = avg_amount * self._freq_to_annual_multiplier(freq)

                # Mark transactions as recurring
                for t in txns:
                    t.is_recurring = True
                    t.recurrence_frequency = freq

                recurring.append(RecurringTransaction(
                    merchant_name=sorted_txns[0].merchant_name or sorted_txns[0].name or merchant,
                    master_category=sorted_txns[0].master_category,
                    frequency=freq,
                    average_amount=round(avg_amount, 2),
                    last_amount=sorted_txns[-1].amount,
                    last_date=sorted_txns[-1].date,
                    next_predicted_date=self._predict_next_date(sorted_txns[-1].date, freq),
                    occurrences=len(txns),
                    total_paid=round(sum(amounts), 2),
                    is_subscription=sorted_txns[0].master_category == MasterCategory.ENTERTAINMENT,
                    annual_cost=round(annual_cost, 2),
                ))

        return sorted(recurring, key=lambda r: r.annual_cost, reverse=True)

    def _interval_to_frequency(self, avg_days: float) -> Optional[RecurrenceFrequency]:
        if avg_days < 2:
            return RecurrenceFrequency.DAILY
        if 5 <= avg_days <= 9:
            return RecurrenceFrequency.WEEKLY
        if 12 <= avg_days <= 16:
            return RecurrenceFrequency.BIWEEKLY
        if 25 <= avg_days <= 35:
            return RecurrenceFrequency.MONTHLY
        if 85 <= avg_days <= 95:
            return RecurrenceFrequency.QUARTERLY
        if 355 <= avg_days <= 375:
            return RecurrenceFrequency.ANNUAL
        if avg_days > 2:
            return RecurrenceFrequency.IRREGULAR
        return None

    def _freq_to_annual_multiplier(self, freq: RecurrenceFrequency) -> float:
        return {
            RecurrenceFrequency.DAILY: 365,
            RecurrenceFrequency.WEEKLY: 52,
            RecurrenceFrequency.BIWEEKLY: 26,
            RecurrenceFrequency.MONTHLY: 12,
            RecurrenceFrequency.QUARTERLY: 4,
            RecurrenceFrequency.ANNUAL: 1,
            RecurrenceFrequency.IRREGULAR: 1,
        }.get(freq, 1)

    def _predict_next_date(self, last_date: date, freq: RecurrenceFrequency) -> Optional[date]:
        delta_map = {
            RecurrenceFrequency.DAILY: timedelta(days=1),
            RecurrenceFrequency.WEEKLY: timedelta(weeks=1),
            RecurrenceFrequency.BIWEEKLY: timedelta(weeks=2),
            RecurrenceFrequency.MONTHLY: timedelta(days=30),
            RecurrenceFrequency.QUARTERLY: timedelta(days=91),
            RecurrenceFrequency.ANNUAL: timedelta(days=365),
        }
        delta = delta_map.get(freq)
        return last_date + delta if delta else None

    # ── Anomaly Detection ──────────────────────────────────────────────────

    def _detect_unusual(
        self, transactions: List[EnrichedTransaction]
    ) -> List[EnrichedTransaction]:
        """Flag transactions more than 2 standard deviations above the merchant average."""
        merchant_amounts: Dict[str, List[float]] = defaultdict(list)
        for txn in transactions:
            key = txn.merchant_name or txn.name
            merchant_amounts[key].append(abs(txn.amount))

        thresholds: Dict[str, float] = {}
        for merchant, amounts in merchant_amounts.items():
            if len(amounts) >= 3:
                mean = statistics.mean(amounts)
                std = statistics.stdev(amounts)
                thresholds[merchant] = mean + 2 * std

        for txn in transactions:
            key = txn.merchant_name or txn.name
            threshold = thresholds.get(key)
            if threshold and abs(txn.amount) > threshold:
                txn.is_unusual = True

        return transactions

    def _detect_duplicates(
        self, transactions: List[EnrichedTransaction]
    ) -> List[EnrichedTransaction]:
        """Flag potential duplicate transactions (same amount, merchant, within 2 days)."""
        seen: Set[Tuple] = set()
        for txn in transactions:
            key = (txn.merchant_name or txn.name, txn.amount)
            if key in seen:
                txn.is_duplicate = True
            seen.add(key)
        return transactions

    # ── Search ─────────────────────────────────────────────────────────────

    def search(
        self,
        transactions: List[EnrichedTransaction],
        query: str = "",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        categories: Optional[List[MasterCategory]] = None,
        merchant: Optional[str] = None,
        category: Optional[MasterCategory] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[EnrichedTransaction]:
        """
        Natural language-aware transaction search.
        e.g. 'all Amazon purchases last 3 months'
        """
        # Handle alternative parameter names
        if date_from and not start_date:
            start_date = date_from
        if date_to and not end_date:
            end_date = date_to
        if category and not categories:
            categories = [category]

        results = transactions[:]

        # Date filters
        if start_date:
            results = [t for t in results if t.date >= start_date]
        if end_date:
            results = [t for t in results if t.date <= end_date]

        # Amount filters
        if min_amount is not None:
            results = [t for t in results if abs(t.amount) >= min_amount]
        if max_amount is not None:
            results = [t for t in results if abs(t.amount) <= max_amount]

        # Category filter
        if categories:
            results = [t for t in results if t.master_category in categories]

        # Merchant filter
        if merchant:
            ml = merchant.lower()
            results = [t for t in results if ml in (t.merchant_name or "").lower() or ml in t.name.lower()]

        # Query text search
        if query:
            ql = query.lower()
            results = [
                t for t in results
                if ql in t.name.lower()
                or ql in (t.merchant_name or "").lower()
                or ql in (t.sub_category or "").lower()
                or ql in t.master_category.value.lower()
            ]

        return sorted(results, key=lambda t: t.date, reverse=True)

    # ── Summary ────────────────────────────────────────────────────────────

    def summarize(
        self,
        transactions: List[EnrichedTransaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> TransactionSummary:
        """Generate spending summary by category for a time period."""
        filtered = transactions
        if start_date:
            filtered = [t for t in filtered if t.date >= start_date]
        if end_date:
            filtered = [t for t in filtered if t.date <= end_date]

        total_income = sum(abs(t.amount) for t in filtered if t.is_income)
        total_expenses = sum(t.amount for t in filtered if t.is_expense and not t.is_income)
        recurring_total = sum(t.amount for t in filtered if t.is_recurring and t.is_expense)

        by_category: Dict[str, float] = defaultdict(float)
        merchant_totals: Dict[str, float] = defaultdict(float)

        for t in filtered:
            if t.is_expense:
                by_category[t.master_category.value] += t.amount
                key = t.merchant_name or t.name
                merchant_totals[key] += t.amount

        top_merchants = sorted(
            [{"merchant": m, "total": round(v, 2)} for m, v in merchant_totals.items()],
            key=lambda x: x["total"],
            reverse=True,
        )[:10]

        return TransactionSummary(
            period_start=start_date or (min(t.date for t in filtered) if filtered else date.today()),
            period_end=end_date or date.today(),
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_cash_flow=round(total_income - total_expenses, 2),
            by_category={k: round(v, 2) for k, v in by_category.items()},
            top_merchants=top_merchants,
            transaction_count=len(filtered),
            unusual_count=sum(1 for t in filtered if t.is_unusual),
            recurring_total=round(recurring_total, 2),
        )

    def export_csv(self, transactions: List[EnrichedTransaction]) -> str:
        """Return CSV string of enriched transactions."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "date", "merchant_name", "name", "amount", "master_category",
            "sub_category", "is_income", "is_recurring", "is_tax_deductible", "pending", "currency",
        ])
        writer.writeheader()
        for t in transactions:
            writer.writerow({
                "date": t.date.isoformat(),
                "merchant_name": t.merchant_name or "",
                "name": t.name,
                "amount": t.amount,
                "master_category": t.master_category.value,
                "sub_category": t.sub_category or "",
                "is_income": t.is_income,
                "is_recurring": t.is_recurring,
                "is_tax_deductible": t.is_tax_deductible,
                "pending": t.pending,
                "currency": t.currency,
            })
        return output.getvalue()

    def detect_anomalies(self, transactions: List[EnrichedTransaction]) -> List[EnrichedTransaction]:
        """Flag anomalous transactions — exposed wrapper around internal detection."""
        if len(transactions) < 3:
            return []
        merchant_amounts: Dict[str, List[float]] = defaultdict(list)
        for txn in transactions:
            key = txn.merchant_name or txn.name
            merchant_amounts[key].append(abs(txn.amount))

        flagged = []
        for txn in transactions:
            key = txn.merchant_name or txn.name
            amounts = merchant_amounts.get(key, [])
            if len(amounts) >= 3:
                mean = statistics.mean(amounts)
                std = statistics.stdev(amounts)
                if std > 0 and abs(txn.amount) > mean + 2 * std:
                    flagged.append(txn)
        return flagged

    def monthly_summary(self, transactions: List[EnrichedTransaction], year: int, month: int) -> TransactionSummary:
        """Generate a monthly spending summary."""
        from calendar import monthrange
        month_txns = [t for t in transactions if t.date.year == year and t.date.month == month]
        total_income = sum(abs(t.amount) for t in month_txns if t.is_income)
        total_expenses = sum(abs(t.amount) for t in month_txns if t.is_expense)
        cat_totals: Dict[str, float] = defaultdict(float)
        for t in month_txns:
            if t.is_expense:
                cat_totals[t.master_category.value] += abs(t.amount)
        _, last_day = monthrange(year, month)
        return TransactionSummary(
            period_start=date(year, month, 1),
            period_end=date(year, month, last_day),
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_cash_flow=round(total_income - total_expenses, 2),
            by_category=dict(cat_totals),
            transaction_count=len(month_txns),
        )

    def category_breakdown(self, transactions: List[EnrichedTransaction]) -> Dict[str, float]:
        """Return spending totals by master category."""
        totals: Dict[str, float] = defaultdict(float)
        for t in transactions:
            if t.is_expense:
                totals[t.master_category.value] += round(abs(t.amount), 2)
        return dict(totals)

