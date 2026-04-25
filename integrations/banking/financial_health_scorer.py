"""
Financial Health Scorer — Composite 0–100 score across 8 financial dimensions.
Generates letter grades, dimension breakdowns, and personalized recommendations.
"""

import logging
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HealthGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"


class HealthDimension(BaseModel):
    # Class-level dimension name constants
    EMERGENCY_FUND: ClassVar[str] = "Emergency Fund"
    DEBT_TO_INCOME: ClassVar[str] = "Debt-to-Income Ratio"
    SAVINGS_RATE: ClassVar[str] = "Savings Rate"
    INVESTMENT_RATE: ClassVar[str] = "Investment Rate"
    CREDIT_SCORE: ClassVar[str] = "Credit Score"
    NET_WORTH_GROWTH: ClassVar[str] = "Net Worth Growth"
    BUDGET_ADHERENCE: ClassVar[str] = "Budget Adherence"
    INSURANCE_COVERAGE: ClassVar[str] = "Insurance Coverage"

    name: str
    weight: float  # % weight in composite score
    raw_value: float  # actual metric value (months, ratio, %)
    score: float    # 0–100
    grade: HealthGrade
    status: str     # "excellent", "good", "fair", "needs_attention", "critical"
    insight: str
    recommendations: List[str] = Field(default_factory=list)


class FinancialHealthInput(BaseModel):
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    liquid_savings: float = 0.0
    total_debt: float = 0.0
    monthly_debt_payments: float = 0.0
    monthly_savings: float = 0.0
    monthly_investments: float = 0.0
    credit_score: int = 0
    net_worth: float = 0.0
    net_worth_prior_year: float = 0.0
    budget_adherence_pct: float = 80.0
    has_life_insurance: bool = False
    has_health_insurance: bool = True
    has_disability_insurance: bool = False
    has_property_insurance: bool = True


class FinancialHealthReport(BaseModel):
    client_id: str
    composite_score: float  # 0–100
    grade: HealthGrade
    dimensions: List[HealthDimension] = Field(default_factory=list)
    top_wins: List[str] = Field(default_factory=list)
    top_actions: List[str] = Field(default_factory=list)
    letter_grade: str = ""
    recommendations: List[str] = Field(default_factory=list)
    score_history: List[Dict[str, Any]] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    next_review_date: Optional[str] = None


def score_to_grade(score: float) -> HealthGrade:
    if score >= 97: return HealthGrade.A_PLUS
    if score >= 93: return HealthGrade.A
    if score >= 90: return HealthGrade.A_MINUS
    if score >= 87: return HealthGrade.B_PLUS
    if score >= 83: return HealthGrade.B
    if score >= 80: return HealthGrade.B_MINUS
    if score >= 77: return HealthGrade.C_PLUS
    if score >= 73: return HealthGrade.C
    if score >= 70: return HealthGrade.C_MINUS
    if score >= 60: return HealthGrade.D
    return HealthGrade.F


def score_to_status(score: float) -> str:
    if score >= 80: return "excellent"
    if score >= 65: return "good"
    if score >= 50: return "fair"
    if score >= 35: return "needs_attention"
    return "critical"


class FinancialHealthScorer:
    """
    Scores financial health across 8 dimensions with weighted composite score.
    """

    DIMENSION_WEIGHTS = {
        "emergency_fund": 0.20,
        "debt_to_income": 0.18,
        "savings_rate": 0.15,
        "investment_rate": 0.12,
        "credit_score": 0.12,
        "net_worth_growth": 0.10,
        "budget_adherence": 0.08,
        "insurance_coverage": 0.05,
    }

    def score(
        self,
        client_id_or_input=None,
        # Emergency fund
        emergency_fund_months: float = 0.0,
        # Debt-to-income
        monthly_debt_payments: float = 0.0,
        gross_monthly_income: float = 1.0,
        # Savings
        monthly_savings: float = 0.0,
        # Investments
        monthly_invested: float = 0.0,
        # Credit
        credit_score: Optional[int] = None,
        # Net worth growth
        net_worth_growth_pct: Optional[float] = None,
        # Budget adherence
        budget_adherence_pct: float = 80.0,
        # Insurance
        has_health_insurance: bool = True,
        has_life_insurance: bool = False,
        has_disability_insurance: bool = False,
        has_property_insurance: bool = True,
        # Historical
        score_history: Optional[List[Dict[str, Any]]] = None,
    ) -> FinancialHealthReport:
        """Generate a comprehensive financial health report."""
        if isinstance(client_id_or_input, FinancialHealthInput):
            inp = client_id_or_input
            client_id = "default"
            gross_monthly_income = inp.monthly_income if inp.monthly_income > 0 else 1.0
            emergency_fund_months = inp.liquid_savings / inp.monthly_expenses if inp.monthly_expenses > 0 else 0.0
            monthly_debt_payments = inp.monthly_debt_payments
            # Derive savings from surplus (income - expenses) for more realistic scoring
            surplus = max(0, inp.monthly_income - inp.monthly_expenses)
            monthly_savings = max(inp.monthly_savings, surplus)
            # Derive investment from surplus allocation
            surplus_after_debt = max(0, inp.monthly_income - inp.monthly_expenses - inp.monthly_debt_payments)
            monthly_invested = max(inp.monthly_investments, surplus_after_debt * 0.3)
            credit_score = inp.credit_score
            nw_prior = inp.net_worth_prior_year
            if nw_prior and nw_prior != 0:
                net_worth_growth_pct = ((inp.net_worth - nw_prior) / abs(nw_prior)) * 100
            else:
                net_worth_growth_pct = 0.0
            budget_adherence_pct = inp.budget_adherence_pct
            has_health_insurance = inp.has_health_insurance
            has_life_insurance = inp.has_life_insurance
            has_disability_insurance = inp.has_disability_insurance
            has_property_insurance = inp.has_property_insurance
        else:
            client_id = client_id_or_input or "default"
        dimensions = []

        # 1. Emergency Fund (target: 6 months)
        ef_score = min(100, (emergency_fund_months / 6) * 100)
        dimensions.append(HealthDimension(
            name="Emergency Fund",
            weight=self.DIMENSION_WEIGHTS["emergency_fund"] * 100,
            raw_value=emergency_fund_months,
            score=round(ef_score, 1),
            grade=score_to_grade(ef_score),
            status=score_to_status(ef_score),
            insight=f"{emergency_fund_months:.1f} months of expenses covered (target: 6+)",
            recommendations=self._ef_recommendations(emergency_fund_months),
        ))

        # 2. Debt-to-Income Ratio (target: <36%)
        dti = (monthly_debt_payments / gross_monthly_income) if gross_monthly_income > 0 else 0
        dti_score = max(0, 100 - (dti * 200))  # 50% DTI = 0 score
        dimensions.append(HealthDimension(
            name="Debt-to-Income Ratio",
            weight=self.DIMENSION_WEIGHTS["debt_to_income"] * 100,
            raw_value=round(dti, 3),
            score=round(dti_score, 1),
            grade=score_to_grade(dti_score),
            status=score_to_status(dti_score),
            insight=f"DTI: {dti*100:.0f}% (excellent <20%, good <36%, high >43%)",
            recommendations=self._dti_recommendations(dti),
        ))

        # 3. Savings Rate (target: 20% of income)
        savings_rate = (monthly_savings / gross_monthly_income) if gross_monthly_income > 0 else 0
        sr_score = min(100, (savings_rate / 0.20) * 100)
        dimensions.append(HealthDimension(
            name="Savings Rate",
            weight=self.DIMENSION_WEIGHTS["savings_rate"] * 100,
            raw_value=round(savings_rate, 3),
            score=round(sr_score, 1),
            grade=score_to_grade(sr_score),
            status=score_to_status(sr_score),
            insight=f"Saving {savings_rate*100:.0f}% of income (target: 20%+)",
            recommendations=self._savings_recommendations(savings_rate),
        ))

        # 4. Investment Rate (target: 15% of income)
        inv_rate = (monthly_invested / gross_monthly_income) if gross_monthly_income > 0 else 0
        inv_score = min(100, (inv_rate / 0.15) * 100)
        dimensions.append(HealthDimension(
            name="Investment Rate",
            weight=self.DIMENSION_WEIGHTS["investment_rate"] * 100,
            raw_value=round(inv_rate, 3),
            score=round(inv_score, 1),
            grade=score_to_grade(inv_score),
            status=score_to_status(inv_score),
            insight=f"Investing {inv_rate*100:.0f}% of income (target: 15%+)",
            recommendations=self._investment_recommendations(inv_rate, gross_monthly_income),
        ))

        # 5. Credit Score (target: 740+)
        credit_normalized = 0.0
        if credit_score:
            credit_normalized = max(0, min(100, (credit_score - 300) / 550 * 100))
        dimensions.append(HealthDimension(
            name="Credit Score",
            weight=self.DIMENSION_WEIGHTS["credit_score"] * 100,
            raw_value=float(credit_score or 0),
            score=round(credit_normalized, 1),
            grade=score_to_grade(credit_normalized),
            status=score_to_status(credit_normalized),
            insight=f"Credit score: {credit_score or 'N/A'} (target: 740+)",
            recommendations=(["Pull your credit report and work on improving your score."] if not credit_score
                             else self._credit_recommendations(credit_score)),
        ))

        # 6. Net Worth Growth (target: positive and growing)
        nwg = net_worth_growth_pct or 0.0
        nwg_score = min(100, max(0, 50 + nwg * 2.5))  # 0% = 50, +20% = 100, -20% = 0
        dimensions.append(HealthDimension(
            name="Net Worth Growth",
            weight=self.DIMENSION_WEIGHTS["net_worth_growth"] * 100,
            raw_value=nwg,
            score=round(nwg_score, 1),
            grade=score_to_grade(nwg_score),
            status=score_to_status(nwg_score),
            insight=f"Net worth grew {nwg:+.1f}% over the past 12 months",
            recommendations=(["Focus on reducing liabilities and increasing assets."] if nwg <= 0 else []),
        ))

        # 7. Budget Adherence
        ba_score = min(100, budget_adherence_pct)
        dimensions.append(HealthDimension(
            name="Budget Adherence",
            weight=self.DIMENSION_WEIGHTS["budget_adherence"] * 100,
            raw_value=budget_adherence_pct,
            score=round(ba_score, 1),
            grade=score_to_grade(ba_score),
            status=score_to_status(ba_score),
            insight=f"Staying within budget {budget_adherence_pct:.0f}% of the time",
            recommendations=(["Set up weekly budget reviews and use the envelope method."] if ba_score < 70 else []),
        ))

        # 8. Insurance Coverage
        coverage_count = sum([has_health_insurance, has_life_insurance, has_disability_insurance, has_property_insurance])
        ins_score = (coverage_count / 4) * 100
        dimensions.append(HealthDimension(
            name="Insurance Coverage",
            weight=self.DIMENSION_WEIGHTS["insurance_coverage"] * 100,
            raw_value=float(coverage_count),
            score=round(ins_score, 1),
            grade=score_to_grade(ins_score),
            status=score_to_status(ins_score),
            insight=f"{coverage_count}/4 key insurance types covered",
            recommendations=self._insurance_recommendations(
                has_health_insurance, has_life_insurance, has_disability_insurance, has_property_insurance
            ),
        ))

        # Composite score
        composite = sum(
            d.score * list(self.DIMENSION_WEIGHTS.values())[i]
            for i, d in enumerate(dimensions)
        )

        # Wins and actions
        wins = [d.insight for d in dimensions if d.score >= 80]
        actions = []
        for d in sorted(dimensions, key=lambda x: x.score):
            actions.extend(d.recommendations[:1])
        actions = actions[:5]

        grade = score_to_grade(composite)
        return FinancialHealthReport(
            client_id=client_id,
            composite_score=round(composite, 1),
            grade=grade,
            dimensions=dimensions,
            top_wins=wins[:3],
            top_actions=actions,
            letter_grade=grade.value,
            recommendations=actions,
            score_history=score_history or [],
        )

    # ── Recommendation helpers ─────────────────────────────────────────────

    def _ef_recommendations(self, months: float) -> List[str]:
        if months < 1:
            return ["Open a dedicated high-yield savings account immediately.", "Set up automatic $500/month transfer until you reach 1 month of expenses."]
        if months < 3:
            return ["Increase your emergency fund to 3 months. Automate transfers right after payday."]
        if months < 6:
            return ["You're close! Boost to 6 months for full protection."]
        return []

    def _dti_recommendations(self, dti: float) -> List[str]:
        if dti > 0.43:
            return ["Critical: DTI above 43% makes new credit difficult. Prioritize debt payoff immediately."]
        if dti > 0.36:
            return ["DTI is elevated. Use the avalanche strategy to eliminate high-interest debt."]
        if dti > 0.20:
            return ["Good progress. Continue paying down debt to reach the optimal <20% DTI."]
        return []

    def _savings_recommendations(self, rate: float) -> List[str]:
        if rate < 0.05:
            return ["Start with saving just $50/week. Automate it — you won't miss what you don't see."]
        if rate < 0.10:
            return ["Increase your savings rate by 1% per month until you reach 20%."]
        if rate < 0.20:
            return ["Great job! Push toward 20% by cutting one discretionary category."]
        return []

    def _investment_recommendations(self, rate: float, income: float) -> List[str]:
        if rate < 0.01:
            return [f"Start investing today. Even ${income*0.01:,.0f}/month in index funds makes a difference over 30 years."]
        if rate < 0.10:
            return ["Max out your 401k match first — it's an instant 50–100% return."]
        return []

    def _credit_recommendations(self, score: int) -> List[str]:
        if score < 580:
            return ["Focus on on-time payments above all else. Consider a secured credit card to rebuild."]
        if score < 670:
            return ["Pay down credit card balances below 30% utilization to see quick gains."]
        if score < 740:
            return ["You're almost at 'very good' territory. Avoid new credit applications for 6 months."]
        return []

    def _insurance_recommendations(
        self, health: bool, life: bool, disability: bool, property: bool
    ) -> List[str]:
        recs = []
        if not health:
            recs.append("Get health insurance immediately — one hospitalization can cause financial ruin.")
        if not disability:
            recs.append("Disability insurance protects your income — the most important coverage for working professionals.")
        if not life:
            recs.append("If others depend on your income, get term life insurance (10–20x annual income).")
        if not property:
            recs.append("Ensure your home/renters and auto insurance are adequate.")
        return recs
