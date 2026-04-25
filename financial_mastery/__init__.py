"""
SintraPrime Financial Mastery System
====================================
A complete AI financial system replacing CPA, CFP, credit consultant,
investment advisor, and business funding specialist.

Philosophy: Master credit and money. Know how to get funding for business
and daily life. A master accountant and expert of the financial industry.

Modules:
    credit_mastery          — Ultimate credit intelligence (dispute letters, repair, building)
    business_funding_engine — Every funding source: SBA, grants, VC, alternative
    accounting_intelligence — CPA-level accounting, tax optimization, payroll
    investment_advisor      — Fiduciary investment planning, retirement, real estate
    banking_intelligence    — Banking system mastery, rights, payment systems, wealth banking
    debt_elimination_engine — Debt strategy, negotiation, bankruptcy, student loans
    financial_report_generator — Beautiful professional financial artifacts
"""

from .credit_mastery import (
    CreditMastery,
    CreditProfile,
    CreditAction,
    DisputeLetter,
    CreditRepairPlan,
    CreditBuildingRoadmap,
    BusinessCreditRoadmap,
    CREDIT_LAWS,
    STATE_SOL,
)

from .business_funding_engine import (
    BusinessFundingEngine,
    FundingOpportunity,
    FundingMatchReport,
    SBALoanStrategy,
    GrantOpportunity,
    VCStrategy,
    AlternativeFundingOptions,
    PersonalFundingStrategy,
    FUNDING_DATABASE,
)

from .accounting_intelligence import (
    AccountingIntelligence,
    FinancialStatement,
    TaxStrategy,
    RatioAnalysis,
    PayrollReport,
    AuditDefenseStrategy,
    TAX_CALENDAR,
    DEDUCTION_DATABASE,
)

from .investment_advisor import (
    InvestmentAdvisor,
    RiskProfile,
    InvestmentPlan,
    RetirementPlan,
    RealEstateAnalysis,
    TaxLossStrategy,
    CryptoStrategy,
)

from .banking_intelligence import (
    BankingIntelligence,
    BankingSystemGuide,
    BankingStrategy,
    BankingRights,
    PaymentSystemsGuide,
    WealthBankingStrategy,
)

from .debt_elimination_engine import (
    DebtEliminationEngine,
    DebtAnalysis,
    DebtEliminationPlan,
    NegotiationStrategy,
    BankruptcyAnalysis,
    StudentLoanStrategy,
)

from .financial_report_generator import (
    FinancialReportGenerator,
    NetWorthReport,
    CashFlowReport,
    ValuationReport,
    ComprehensiveFinancialPlan,
)

__all__ = [
    # Credit
    "CreditMastery", "CreditProfile", "CreditAction", "DisputeLetter",
    "CreditRepairPlan", "CreditBuildingRoadmap", "BusinessCreditRoadmap",
    "CREDIT_LAWS", "STATE_SOL",
    # Business Funding
    "BusinessFundingEngine", "FundingOpportunity", "FundingMatchReport",
    "SBALoanStrategy", "GrantOpportunity", "VCStrategy",
    "AlternativeFundingOptions", "PersonalFundingStrategy", "FUNDING_DATABASE",
    # Accounting
    "AccountingIntelligence", "FinancialStatement", "TaxStrategy",
    "RatioAnalysis", "PayrollReport", "AuditDefenseStrategy",
    "TAX_CALENDAR", "DEDUCTION_DATABASE",
    # Investment
    "InvestmentAdvisor", "RiskProfile", "InvestmentPlan", "RetirementPlan",
    "RealEstateAnalysis", "TaxLossStrategy", "CryptoStrategy",
    # Banking
    "BankingIntelligence", "BankingSystemGuide", "BankingStrategy",
    "BankingRights", "PaymentSystemsGuide", "WealthBankingStrategy",
    # Debt
    "DebtEliminationEngine", "DebtAnalysis", "DebtEliminationPlan",
    "NegotiationStrategy", "BankruptcyAnalysis", "StudentLoanStrategy",
    # Reports
    "FinancialReportGenerator", "NetWorthReport", "CashFlowReport",
    "ValuationReport", "ComprehensiveFinancialPlan",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Financial Intelligence"
