"""
Tax Optimizer — Tax-loss harvesting, deduction strategies, and tax-advantaged account recommendations.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .transaction_engine import EnrichedTransaction, TaxCategory
from .investment_tracker import HoldingDetail, PortfolioSummary

logger = logging.getLogger(__name__)


class FilingStatus(str, Enum):
    SINGLE = "single"
    MARRIED_JOINTLY = "married_filing_jointly"
    MARRIED_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class TaxBracket(BaseModel):
    min_income: float
    max_income: float
    rate: float
    filing_status: FilingStatus


class TaxLossHarvestingOpportunity(BaseModel):
    security_name: Optional[str]
    ticker: Optional[str]
    current_value: float
    cost_basis: float
    unrealized_loss: float
    tax_savings_estimate: float
    wash_sale_risk: bool
    recommendation: str


class DeductionOpportunity(BaseModel):
    deduction_name: str
    category: str
    estimated_amount: float
    tax_savings_estimate: float
    action_required: str
    deadline: Optional[str] = None
    is_current_year: bool = True


class TaxOptimizationReport(BaseModel):
    client_id: str
    tax_year: int
    filing_status: FilingStatus
    estimated_agi: float
    marginal_rate: float
    effective_rate: Optional[float] = None
    total_deductible_expenses: float = 0.0
    total_tax_savings_identified: float = 0.0
    deduction_opportunities: List[DeductionOpportunity] = Field(default_factory=list)
    tax_loss_opportunities: List[TaxLossHarvestingOpportunity] = Field(default_factory=list)
    account_recommendations: List[str] = Field(default_factory=list)
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# 2024 Federal Tax Brackets (Married Filing Jointly)
TAX_BRACKETS = {
    FilingStatus.MARRIED_JOINTLY: [
        (0, 23_200, 0.10),
        (23_200, 94_300, 0.12),
        (94_300, 201_050, 0.22),
        (201_050, 383_900, 0.24),
        (383_900, 487_450, 0.32),
        (487_450, 731_200, 0.35),
        (731_200, float("inf"), 0.37),
    ],
    FilingStatus.SINGLE: [
        (0, 11_600, 0.10),
        (11_600, 47_150, 0.12),
        (47_150, 100_525, 0.22),
        (100_525, 191_950, 0.24),
        (191_950, 243_725, 0.32),
        (243_725, 609_350, 0.35),
        (609_350, float("inf"), 0.37),
    ],
}

STANDARD_DEDUCTIONS = {
    FilingStatus.SINGLE: 14_600,
    FilingStatus.MARRIED_JOINTLY: 29_200,
    FilingStatus.MARRIED_SEPARATELY: 14_600,
    FilingStatus.HEAD_OF_HOUSEHOLD: 21_900,
}


class TaxOptimizer:
    """
    Identifies tax optimization opportunities from transaction and investment data.
    """

    def __init__(self):
        pass

    def analyze(
        self,
        client_id: str,
        transactions: List[EnrichedTransaction],
        portfolio: Optional[PortfolioSummary] = None,
        annual_income: float = 0.0,
        filing_status: FilingStatus = FilingStatus.SINGLE,
        tax_year: Optional[int] = None,
        has_business: bool = False,
    ) -> TaxOptimizationReport:
        year = tax_year or date.today().year
        marginal_rate = self._get_marginal_rate(annual_income, filing_status)
        standard_deduction = STANDARD_DEDUCTIONS.get(filing_status, 14_600)

        # Find deductible transactions
        deductible = [t for t in transactions if t.is_tax_deductible]
        total_deductible = sum(abs(t.amount) for t in deductible)

        deduction_opps = self._identify_deductions(
            transactions=deductible,
            annual_income=annual_income,
            filing_status=filing_status,
            has_business=has_business,
            standard_deduction=standard_deduction,
            marginal_rate=marginal_rate,
        )

        # Tax-loss harvesting
        tlh_opps = []
        if portfolio:
            tlh_opps = self._identify_tax_loss_harvesting(portfolio, marginal_rate)

        total_savings = sum(d.tax_savings_estimate for d in deduction_opps) + \
                        sum(t.tax_savings_estimate for t in tlh_opps)

        # Account optimization recommendations
        acct_recs = self._account_recommendations(annual_income, marginal_rate)

        report = TaxOptimizationReport(
            client_id=client_id,
            tax_year=year,
            filing_status=filing_status,
            estimated_agi=annual_income,
            marginal_rate=marginal_rate,
            total_deductible_expenses=round(total_deductible, 2),
            total_tax_savings_identified=round(total_savings, 2),
            deduction_opportunities=deduction_opps,
            tax_loss_opportunities=tlh_opps,
            account_recommendations=acct_recs,
        )
        report.summary = self._build_summary(report)
        return report

    def _get_marginal_rate(self, income: float, status: FilingStatus) -> float:
        brackets = TAX_BRACKETS.get(status, TAX_BRACKETS[FilingStatus.SINGLE])
        for low, high, rate in brackets:
            if low <= income < high:
                return rate
        return 0.37

    def _identify_deductions(
        self,
        transactions: List[EnrichedTransaction],
        annual_income: float,
        filing_status: FilingStatus,
        has_business: bool,
        standard_deduction: float,
        marginal_rate: float,
    ) -> List[DeductionOpportunity]:
        opps = []

        # Business expense deductions
        if has_business:
            biz_txns = [t for t in transactions if t.tax_category == TaxCategory.DEDUCTIBLE_BUSINESS]
            biz_total = sum(abs(t.amount) for t in biz_txns)
            if biz_total > 0:
                opps.append(DeductionOpportunity(
                    deduction_name="Business Expenses (Schedule C)",
                    category="business",
                    estimated_amount=round(biz_total, 2),
                    tax_savings_estimate=round(biz_total * marginal_rate, 2),
                    action_required="Compile receipts and categorize on Schedule C. Use accounting software.",
                ))

        # Medical deductions (>7.5% of AGI)
        med_txns = [t for t in transactions if t.tax_category == TaxCategory.DEDUCTIBLE_MEDICAL]
        med_total = sum(abs(t.amount) for t in med_txns)
        threshold = annual_income * 0.075
        if med_total > threshold:
            deductible_med = med_total - threshold
            opps.append(DeductionOpportunity(
                deduction_name="Medical Expenses (excess over 7.5% AGI)",
                category="healthcare",
                estimated_amount=round(deductible_med, 2),
                tax_savings_estimate=round(deductible_med * marginal_rate, 2),
                action_required="Itemize deductions on Schedule A. Collect all medical receipts.",
            ))

        # Home mortgage interest
        opps.append(DeductionOpportunity(
            deduction_name="Mortgage Interest Deduction",
            category="housing",
            estimated_amount=0.0,  # pulled from liability data in full implementation
            tax_savings_estimate=0.0,
            action_required="Pull Form 1098 from your mortgage servicer. Deductible if itemizing.",
        ))

        # Retirement contributions
        retirement_limit = 23_000  # 2024 401k limit
        opps.append(DeductionOpportunity(
            deduction_name="Maximize 401(k) Contribution",
            category="retirement",
            estimated_amount=retirement_limit,
            tax_savings_estimate=round(retirement_limit * marginal_rate, 2),
            action_required=f"Max out your 401(k) at ${retirement_limit:,}/year to reduce AGI by ${retirement_limit:,}.",
            deadline="December 31",
        ))

        # HSA
        hsa_limit = 4_150  # 2024 individual HSA limit
        opps.append(DeductionOpportunity(
            deduction_name="Health Savings Account (HSA) Contribution",
            category="healthcare",
            estimated_amount=hsa_limit,
            tax_savings_estimate=round(hsa_limit * marginal_rate, 2),
            action_required=f"Contribute up to ${hsa_limit:,} to your HSA (triple tax advantage: pre-tax, grows tax-free, withdrawals tax-free for medical).",
            deadline="April 15",
        ))

        return opps

    def _identify_tax_loss_harvesting(
        self,
        portfolio: PortfolioSummary,
        marginal_rate: float,
    ) -> List[TaxLossHarvestingOpportunity]:
        opps = []
        for acct in portfolio.accounts:
            for holding in acct.holdings:
                if holding.unrealized_gain is not None and holding.unrealized_gain < -500:
                    loss = abs(holding.unrealized_gain)
                    # Long-term capital gains rate (simplified)
                    cap_gains_rate = min(marginal_rate, 0.20)
                    tax_savings = loss * cap_gains_rate
                    opps.append(TaxLossHarvestingOpportunity(
                        security_name=holding.security_name,
                        ticker=holding.ticker,
                        current_value=holding.market_value,
                        cost_basis=holding.cost_basis or 0.0,
                        unrealized_loss=holding.unrealized_gain,
                        tax_savings_estimate=round(tax_savings, 2),
                        wash_sale_risk=False,  # simplified
                        recommendation=(
                            f"Sell {holding.ticker or holding.security_name} to realize ${loss:,.0f} loss. "
                            f"Estimated tax savings: ${tax_savings:,.0f}. "
                            f"Reinvest in a similar (not substantially identical) security to maintain market exposure. "
                            f"Wait 31 days before repurchasing to avoid wash-sale rule."
                        ),
                    ))
        return sorted(opps, key=lambda o: abs(o.unrealized_loss), reverse=True)

    def _account_recommendations(
        self, income: float, marginal_rate: float
    ) -> List[str]:
        recs = []
        if marginal_rate >= 0.22:
            recs.append("Max out pre-tax 401(k) to reduce taxable income — saves thousands at your bracket.")
            recs.append("Consider a Traditional IRA if you're eligible for the deduction.")
        if income < 146_000:  # 2024 Roth IRA income limit single
            recs.append("Contribute to a Roth IRA — tax-free growth is extremely valuable over time.")
        if marginal_rate >= 0.32:
            recs.append("At your tax bracket, municipal bonds can provide tax-free income.")
            recs.append("Review asset location: put bonds and REITs in tax-deferred accounts.")
        recs.append("Use tax-loss harvesting in taxable brokerage accounts at year-end.")
        recs.append("Track all business and deductible expenses year-round with receipt capture.")
        return recs

    def _build_summary(self, report: TaxOptimizationReport) -> str:
        return (
            f"Identified ${report.total_tax_savings_identified:,.0f} in potential tax savings for {report.tax_year}. "
            f"Marginal rate: {report.marginal_rate*100:.0f}%. "
            f"Top action: {report.deduction_opportunities[0].action_required[:80] if report.deduction_opportunities else 'Maximize retirement contributions.'}"
        )
