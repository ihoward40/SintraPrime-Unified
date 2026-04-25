"""
SintraPrime-Unified Artifacts Engine
=====================================
Professional document generation, legal templates, financial reporting,
and credit analysis — rendered to world-class standards.
"""

from .document_renderer import (
    DocumentRenderer,
    DocumentStyle,
    RenderedDocument,
    DocumentPackage,
    LEGAL_TRADITIONAL,
    FINANCIAL_PROFESSIONAL,
    CORPORATE_MODERN,
    GOVERNMENT_OFFICIAL,
    SINTRAPRIME_SIGNATURE,
)
from .legal_document_library import LegalDocumentLibrary
from .financial_report_templates import FinancialReportTemplates
from .credit_report_analyzer import CreditReportAnalyzer, DisputePackage

__all__ = [
    "DocumentRenderer",
    "DocumentStyle",
    "RenderedDocument",
    "DocumentPackage",
    "LEGAL_TRADITIONAL",
    "FINANCIAL_PROFESSIONAL",
    "CORPORATE_MODERN",
    "GOVERNMENT_OFFICIAL",
    "SINTRAPRIME_SIGNATURE",
    "LegalDocumentLibrary",
    "FinancialReportTemplates",
    "CreditReportAnalyzer",
    "DisputePackage",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"
