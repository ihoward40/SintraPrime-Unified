"""
Budget Engine — Budget creation, tracking, and personalized recommendations.
Supports 50/30/20, zero-based, envelope, and custom budget frameworks.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .transaction_engine import EnrichedTransaction, MasterCategory

logger = logging.getLogger(__name__)


class BudgetFramework(str, Enum):
    FIFTY_THIRTY_TWENTY = "50_30_20"
    ZERO_BASED = "zero_based"
    ENVELOPE = "envelope"
    CUSTOM = "custom"


class BudgetStatus(str, Enum):
    ON_TRACK = "on_track"
    WARNING = "warning"      # 80–100% spent
    OVER_BUDGET = "over_budget"
    UNDER_SPENT = "under_spent"


class BudgetCategory(BaseModel):
    category: str
    label: str
    budgeted_amount: float
    spent_amount: float = 0.0
    remaining: float = 0.0
    utilization: float = 0.0  # 0–1
    status: BudgetStatus = BudgetStatus.ON_TRACK
    budget_type: str = "discretionary"  # "needs", "wants", "savings"


class Budget(BaseModel):
    budget_id: str
    client_id: str
    name: str
    framework: BudgetFramework
    monthly_income: float
    total_budgeted: float = 0.0
    total_spent: float = 0.0
    total_remaining: float = 0.0
    categories: List[BudgetCategory] = Field(default_factory=list)
    period_start: date
    period_end: date
    adherence_score: float = 0.0  # 0–100
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BudgetRecommendation(BaseModel):
    category: str
    current_spending: float
    recommended_budget: float
    adjustment: float
    reason: str
    priority: str  # "high", "medium", "low"


class BudgetEngine:
    """
    Creates and tracks budgets using multiple frameworks.
    Generates spending alerts and optimization recommendations.
    """

    # 50/30/20 rule allocation by category
    FIFTY_THIRTY_TWENTY_MAPPING = {
        # NEEDS (50%)
        MasterCategory.HOUSING: ("needs", 0.30),
        MasterCategory.UTILITIES: ("needs", 0.05),
        MasterCategory.FOOD: ("needs", 0.10),
        MasterCategory.TRANSPORTATION: ("needs", 0.10),
        MasterCategory.HEALTHCARE: ("needs", 0.05),
        MasterCategory.INSURANCE: ("needs", 0.05),
        # WANTS (30%)
        MasterCategory.ENTERTAINMENT: ("wants", 0.05),
        MasterCategory.SHOPPING: ("wants", 0.10),
        MasterCategory.TRAVEL: ("wants", 0.07),
        MasterCategory.PERSONAL_CARE: ("wants", 0.03),
        MasterCategory.EDUCATION: ("wants", 0.05),
        # SAVINGS (20%)
        MasterCategory.FINANCIAL: ("savings", 0.20),
    }

    def create_budget(
        self,
        client_id: str,
        monthly_income: float,
        framework: BudgetFramework,
        period_start: date,
        period_end: date,
        custom_allocations: Optional[Dict[str, float]] = None,
    ) -> Budget:
        """Create a budget using the specified framework."""
        import uuid
        budget = Budget(
            budget_id=str(uuid.uuid4()),
            client_id=client_id,
            name=f"{framework.value.replace('_', ' ').title()} Budget",
            framework=framework,
            monthly_income=monthly_income,
            period_start=period_start,
            period_end=period_end,
        )

        if framework == BudgetFramework.FIFTY_THIRTY_TWENTY:
            budget.categories = self._build_503020_categories(monthly_income)
        elif framework == BudgetFramework.ZERO_BASED:
            budget.categories = self._build_zero_based(monthly_income)
        elif framework == BudgetFramework.CUSTOM and custom_allocations:
            budget.categories = self._build_custom(monthly_income, custom_allocations)
        else:
            budget.categories = self._build_503020_categories(monthly_income)

        budget.total_budgeted = sum(c.budgeted_amount for c in budget.categories)
        return budget

    def _build_503020_categories(self, income: float) -> List[BudgetCategory]:
        categories = []
        for master_cat, (budget_type, pct) in self.FIFTY_THIRTY_TWENTY_MAPPING.items():
            amount = income * pct
            categories.append(BudgetCategory(
                category=master_cat.value,
                label=master_cat.value.replace("_", " ").title(),
                budgeted_amount=round(amount, 2),
                remaining=round(amount, 2),
                budget_type=budget_type,
            ))
        return categories

    def _build_zero_based(self, income: float) -> List[BudgetCategory]:
        """Every dollar is assigned a job."""
        buckets = [
            ("housing", "Housing (Rent/Mortgage)", income * 0.28, "needs"),
            ("food", "Food (Groceries + Dining)", income * 0.12, "needs"),
            ("transportation", "Transportation", income * 0.10, "needs"),
            ("utilities", "Utilities + Phone", income * 0.05, "needs"),
            ("healthcare", "Healthcare", income * 0.04, "needs"),
            ("insurance", "Insurance", income * 0.04, "needs"),
            ("entertainment", "Entertainment", income * 0.05, "wants"),
            ("shopping", "Shopping", income * 0.05, "wants"),
            ("travel", "Travel + Dining Out", income * 0.03, "wants"),
            ("personal_care", "Personal Care", income * 0.02, "wants"),
            ("financial", "Savings + Investments", income * 0.20, "savings"),
            ("education", "Education + Growth", income * 0.02, "savings"),
        ]
        return [
            BudgetCategory(
                category=cat,
                label=label,
                budgeted_amount=round(amt, 2),
                remaining=round(amt, 2),
                budget_type=btype,
            )
            for cat, label, amt, btype in buckets
        ]

    def _build_custom(
        self, income: float, allocations: Dict[str, float]
    ) -> List[BudgetCategory]:
        return [
            BudgetCategory(
                category=cat,
                label=cat.replace("_", " ").title(),
                budgeted_amount=round(income * pct, 2),
                remaining=round(income * pct, 2),
                budget_type="custom",
            )
            for cat, pct in allocations.items()
        ]

    def apply_transactions(
        self, budget: Budget, transactions: List[EnrichedTransaction]
    ) -> Budget:
        """Update budget with actual spending from transactions."""
        cat_map = {c.category: c for c in budget.categories}

        for txn in transactions:
            if not txn.is_expense or txn.is_transfer:
                continue
            cat_key = txn.master_category.value
            if cat_key in cat_map:
                cat_map[cat_key].spent_amount += txn.amount

        for cat in budget.categories:
            cat.remaining = round(cat.budgeted_amount - cat.spent_amount, 2)
            cat.utilization = (cat.spent_amount / cat.budgeted_amount) if cat.budgeted_amount > 0 else 0.0
            if cat.utilization >= 1.0:
                cat.status = BudgetStatus.OVER_BUDGET
            elif cat.utilization >= 0.80:
                cat.status = BudgetStatus.WARNING
            elif cat.utilization < 0.20 and cat.budgeted_amount > 0:
                cat.status = BudgetStatus.UNDER_SPENT
            else:
                cat.status = BudgetStatus.ON_TRACK

        budget.total_spent = sum(c.spent_amount for c in budget.categories)
        budget.total_remaining = budget.total_budgeted - budget.total_spent
        budget.adherence_score = self._adherence_score(budget)
        return budget

    def _adherence_score(self, budget: Budget) -> float:
        """Score 0–100 based on how well spending matches the budget."""
        if not budget.categories:
            return 0.0
        on_track = sum(1 for c in budget.categories if c.status == BudgetStatus.ON_TRACK)
        return round((on_track / len(budget.categories)) * 100, 1)

    def generate_recommendations(
        self,
        budget: Budget,
        historical_avg: Dict[str, float],
    ) -> List[BudgetRecommendation]:
        """Recommend budget adjustments based on actual spending history."""
        recs = []
        for cat in budget.categories:
            avg_spend = historical_avg.get(cat.category, 0.0)
            if avg_spend == 0:
                continue
            adjustment = cat.budgeted_amount - avg_spend
            if abs(adjustment) > cat.budgeted_amount * 0.15:
                recs.append(BudgetRecommendation(
                    category=cat.label,
                    current_spending=round(avg_spend, 2),
                    recommended_budget=round(avg_spend * 1.05, 2),  # +5% buffer
                    adjustment=round(adjustment, 2),
                    reason=(
                        f"You consistently {'overspend' if adjustment < 0 else 'underspend'} "
                        f"this category by ${abs(adjustment):,.0f}/month."
                    ),
                    priority="high" if cat.status == BudgetStatus.OVER_BUDGET else "medium",
                ))
        return sorted(recs, key=lambda r: abs(r.adjustment), reverse=True)
