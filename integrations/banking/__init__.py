"""
SintraPrime Banking Integration Package
Powered by Plaid — Real-time financial intelligence for every client.
"""

from .plaid_client import PlaidClient
from .account_aggregator import AccountAggregator
from .transaction_engine import TransactionEngine
from .credit_intelligence import CreditIntelligence
from .investment_tracker import InvestmentTracker
from .liability_manager import LiabilityManager
from .cash_flow_analyzer import CashFlowAnalyzer
from .budget_engine import BudgetEngine
from .net_worth_calculator import NetWorthCalculator
from .fraud_detector import FraudDetector
from .financial_health_scorer import FinancialHealthScorer
from .funding_matcher import FundingMatcher
from .tax_optimizer import TaxOptimizer
from .wealth_builder import WealthBuilder
from .debt_eliminator import DebtEliminator
from .credit_optimizer import CreditOptimizer
from .business_banking import BusinessBanking

__version__ = "1.0.0"
__all__ = [
    "PlaidClient",
    "AccountAggregator",
    "TransactionEngine",
    "CreditIntelligence",
    "InvestmentTracker",
    "LiabilityManager",
    "CashFlowAnalyzer",
    "BudgetEngine",
    "NetWorthCalculator",
    "FraudDetector",
    "FinancialHealthScorer",
    "FundingMatcher",
    "TaxOptimizer",
    "WealthBuilder",
    "DebtEliminator",
    "CreditOptimizer",
    "BusinessBanking",
]
