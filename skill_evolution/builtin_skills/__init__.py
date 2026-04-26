"""Built-in skill implementations for SintraPrime-Unified."""

from .legal_research import LegalResearchSkill
from .document_drafter import DocumentDrafterSkill
from .financial_analyzer import FinancialAnalyzerSkill
from .court_monitor import CourtMonitorSkill
from .contract_reviewer import ContractReviewerSkill
from .deadline_calculator import DeadlineCalculatorSkill

__all__ = [
    "LegalResearchSkill",
    "DocumentDrafterSkill",
    "FinancialAnalyzerSkill",
    "CourtMonitorSkill",
    "ContractReviewerSkill",
    "DeadlineCalculatorSkill",
]
