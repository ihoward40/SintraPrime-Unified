"""
Liability Manager — Comprehensive debt tracking for mortgages, auto, student, and personal loans.
Provides payoff timelines, total interest calculations, and refinancing analysis.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from .plaid_client import PlaidClient

logger = logging.getLogger(__name__)


class LiabilityType(str, Enum):
    MORTGAGE = "mortgage"
    AUTO = "auto"
    STUDENT = "student"
    PERSONAL = "personal"
    CREDIT_CARD = "credit_card"
    BUSINESS = "business"
    HELOC = "heloc"
    OTHER = "other"


class PaymentStatus(str, Enum):
    CURRENT = "current"
    LATE_30 = "late_30"
    LATE_60 = "late_60"
    LATE_90 = "late_90"
    DEFAULT = "default"
    PAID_OFF = "paid_off"


class Liability(BaseModel):
    liability_id: str
    account_id: str
    name: str
    liability_type: LiabilityType
    current_balance: float
    original_principal: Optional[float] = None
    apr: float = 0.0
    monthly_payment: Optional[float] = None
    minimum_payment: Optional[float] = None
    payoff_balance: Optional[float] = None
    origination_date: Optional[date] = None
    payoff_date: Optional[date] = None
    payment_status: PaymentStatus = PaymentStatus.CURRENT
    last_payment_amount: Optional[float] = None
    last_payment_date: Optional[date] = None
    lender: Optional[str] = None
    is_deductible: bool = False  # mortgage interest, student loan interest


class LiabilityPortfolio(BaseModel):
    client_id: str
    liabilities: List[Liability] = Field(default_factory=list)
    total_debt: float = 0.0
    total_monthly_payments: float = 0.0
    mortgage_balance: float = 0.0
    auto_loan_balance: float = 0.0
    student_loan_balance: float = 0.0
    credit_card_balance: float = 0.0
    personal_loan_balance: float = 0.0
    weighted_average_apr: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PayoffProjection(BaseModel):
    liability_id: str
    name: str
    current_balance: float
    monthly_payment: float
    payoff_months: int
    payoff_date: date
    total_interest_paid: float
    total_paid: float


class RefinanceAnalysis(BaseModel):
    liability_id: str
    name: str
    current_balance: float
    current_apr: float
    current_remaining_months: int
    current_total_interest: float
    new_apr: float
    new_monthly_payment: float
    new_total_interest: float
    interest_savings: float
    break_even_months: int
    recommendation: str


class LiabilityManager:
    """
    Comprehensive liability tracking and payoff analysis.
    """

    def __init__(self, plaid_client: Optional[PlaidClient] = None):
        self.client = plaid_client

    async def build_portfolio(
        self, client_id: str, access_token: str
    ) -> LiabilityPortfolio:
        """Fetch and structure all liabilities from Plaid."""
        portfolio = LiabilityPortfolio(client_id=client_id)

        if not self.client:
            return portfolio

        data = await self.client.get_liabilities(access_token)
        acct_map = {a["account_id"]: a for a in data.get("accounts", [])}

        liabilities: List[Liability] = []

        # Credit cards
        for cc in data.get("credit", []):
            acct = acct_map.get(cc.get("account_id", ""), {})
            bal = cc.get("last_statement_balance") or 0.0
            apr_list = cc.get("aprs", [])
            apr = apr_list[0].get("apr_percentage", 0.0) if apr_list else 0.0
            liabilities.append(Liability(
                liability_id=cc.get("account_id", ""),
                account_id=cc.get("account_id", ""),
                name=acct.get("name", "Credit Card"),
                liability_type=LiabilityType.CREDIT_CARD,
                current_balance=bal,
                apr=apr / 100,
                minimum_payment=cc.get("minimum_payment_amount"),
                last_payment_amount=cc.get("last_payment_amount"),
                last_payment_date=cc.get("last_payment_date"),
                credit_limit=cc.get("credit_limit"),
                is_deductible=False,
            ))
            portfolio.credit_card_balance += bal

        # Mortgages
        for mort in data.get("mortgage", []):
            acct = acct_map.get(mort.get("account_id", ""), {})
            bal = mort.get("current_outstanding_principal_balance") or 0.0
            liabilities.append(Liability(
                liability_id=mort.get("account_id", ""),
                account_id=mort.get("account_id", ""),
                name=acct.get("name", "Mortgage"),
                liability_type=LiabilityType.MORTGAGE,
                current_balance=bal,
                original_principal=mort.get("origination_principal_amount"),
                apr=(mort.get("interest_rate", {}) or {}).get("percentage", 0.0) / 100,
                monthly_payment=mort.get("next_monthly_payment"),
                payoff_balance=mort.get("past_due_amount"),
                origination_date=mort.get("origination_date"),
                payoff_date=mort.get("expected_payoff_date"),
                last_payment_date=mort.get("last_payment_date"),
                last_payment_amount=mort.get("last_payment_amount"),
                is_deductible=True,
            ))
            portfolio.mortgage_balance += bal

        # Student loans
        for sl in data.get("student", []):
            acct = acct_map.get(sl.get("account_id", ""), {})
            bal = sl.get("outstanding_interest_amount", 0) + (sl.get("principal_balance", {}) or {}).get("amount", 0)
            liabilities.append(Liability(
                liability_id=sl.get("account_id", ""),
                account_id=sl.get("account_id", ""),
                name=acct.get("name", "Student Loan"),
                liability_type=LiabilityType.STUDENT,
                current_balance=bal,
                minimum_payment=sl.get("minimum_payment_amount"),
                is_deductible=True,
            ))
            portfolio.student_loan_balance += bal

        portfolio.liabilities = liabilities
        portfolio.total_debt = sum(l.current_balance for l in liabilities)
        portfolio.total_monthly_payments = sum(
            (l.monthly_payment or l.minimum_payment or 0) for l in liabilities
        )

        # Weighted average APR
        if portfolio.total_debt > 0:
            weighted = sum(l.current_balance * l.apr for l in liabilities)
            portfolio.weighted_average_apr = round(weighted / portfolio.total_debt, 4)

        return portfolio

    def project_payoffs(
        self,
        portfolio: LiabilityPortfolio,
        extra_monthly_payment: float = 0.0,
    ) -> List[PayoffProjection]:
        """Project payoff timeline for each liability."""
        projections = []
        for liability in portfolio.liabilities:
            payment = (liability.monthly_payment or liability.minimum_payment or 0) + extra_monthly_payment
            if payment <= 0:
                continue
            proj = self._calculate_payoff(liability, payment)
            projections.append(proj)
        return sorted(projections, key=lambda p: p.payoff_months)

    def _calculate_payoff(
        self, liability: Liability, monthly_payment: float
    ) -> PayoffProjection:
        """Calculate amortization for a single liability."""
        balance = liability.current_balance
        monthly_rate = liability.apr / 12
        total_interest = 0.0
        months = 0
        max_months = 600  # 50 years cap

        while balance > 0 and months < max_months:
            interest = balance * monthly_rate
            total_interest += interest
            principal = min(monthly_payment - interest, balance)
            balance -= max(principal, 0)
            months += 1
            if monthly_payment <= interest and monthly_rate > 0:
                # Payment doesn't cover interest — infinite loop guard
                months = max_months
                break

        payoff_date = date.today().replace(day=1)
        from datetime import timedelta
        payoff_date = date(
            payoff_date.year + (payoff_date.month + months - 1) // 12,
            (payoff_date.month + months - 1) % 12 + 1,
            1,
        )

        return PayoffProjection(
            liability_id=liability.liability_id,
            name=liability.name,
            current_balance=liability.current_balance,
            monthly_payment=monthly_payment,
            payoff_months=months,
            payoff_date=payoff_date,
            total_interest_paid=round(total_interest, 2),
            total_paid=round(liability.current_balance + total_interest, 2),
        )

    def analyze_refinance(
        self,
        liability: Liability,
        new_apr: float,
        closing_costs: float = 0.0,
    ) -> RefinanceAnalysis:
        """Analyze whether refinancing a loan is beneficial."""
        current_proj = self._calculate_payoff(
            liability, liability.monthly_payment or liability.minimum_payment or 0
        )

        # New loan parameters
        new_monthly_rate = new_apr / 12
        new_balance = liability.current_balance + closing_costs
        n = current_proj.payoff_months

        if new_monthly_rate > 0:
            new_payment = new_balance * (new_monthly_rate * (1 + new_monthly_rate) ** n) / ((1 + new_monthly_rate) ** n - 1)
        else:
            new_payment = new_balance / n

        new_total_interest = (new_payment * n) - new_balance
        interest_savings = current_proj.total_interest_paid - new_total_interest

        # Break-even: months until savings exceed closing costs
        monthly_savings = (current_proj.monthly_payment - new_payment)
        break_even = int(closing_costs / monthly_savings) if monthly_savings > 0 else 999

        return RefinanceAnalysis(
            liability_id=liability.liability_id,
            name=liability.name,
            current_balance=liability.current_balance,
            current_apr=liability.apr,
            current_remaining_months=current_proj.payoff_months,
            current_total_interest=current_proj.total_interest_paid,
            new_apr=new_apr,
            new_monthly_payment=round(new_payment, 2),
            new_total_interest=round(new_total_interest, 2),
            interest_savings=round(interest_savings, 2),
            break_even_months=break_even,
            recommendation=(
                f"Refinancing saves ${interest_savings:,.0f} total interest. "
                f"Break-even at month {break_even}. {'Recommended.' if break_even < 36 else 'Only beneficial if you plan to hold long-term.'}"
            ) if interest_savings > 0 else "Current rate is already competitive. Refinancing not recommended.",
        )
