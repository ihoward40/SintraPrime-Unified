"""
ai_compliance — AI Governance & Compliance Layer for SintraPrime-Unified
Covers EU AI Act, US State AI Laws, NIST RMF, FTC Guidelines, and ABA AI Rules.
"""

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"

from ai_compliance.ai_law_db import (
    AILaw,
    ALL_LAWS,
    ComplianceArea,
    Jurisdiction,
    RiskTier,
    get_applicable_laws,
    get_laws_by_area,
    get_laws_by_jurisdiction,
    get_laws_summary,
)

from ai_compliance.compliance_checker import (
    CheckStatus,
    ComplianceCheck,
    ComplianceChecker,
    ComplianceSummary,
    OperationContext,
    Severity,
    quick_check,
)

from ai_compliance.ethics_framework import (
    AIAction,
    EthicsDecision,
    EthicsReview,
    EthicsReviewer,
    EthicalPrinciple,
    RED_LINES,
    ethics_review,
)

from ai_compliance.bias_detector import (
    BiasDetector,
    BiasReport,
    BiasSeverity,
    BiasType,
    ProtectedCategory,
    check_bias,
    compute_adverse_impact_ratio,
    compute_group_adverse_impact,
)

from ai_compliance.compliance_reporter import (
    ComplianceReportData,
    ComplianceReporter,
    ComplianceSnapshot,
    TrendDirection,
    RiskRating,
    compute_risk_rating,
    compute_trend,
)

__all__ = [
    # Law DB
    "AILaw", "ALL_LAWS", "ComplianceArea", "Jurisdiction", "RiskTier",
    "get_applicable_laws", "get_laws_by_area", "get_laws_by_jurisdiction", "get_laws_summary",
    # Compliance Checker
    "CheckStatus", "ComplianceCheck", "ComplianceChecker", "ComplianceSummary",
    "OperationContext", "Severity", "quick_check",
    # Ethics
    "AIAction", "EthicsDecision", "EthicsReview", "EthicsReviewer",
    "EthicalPrinciple", "RED_LINES", "ethics_review",
    # Bias
    "BiasDetector", "BiasReport", "BiasSeverity", "BiasType", "ProtectedCategory",
    "check_bias", "compute_adverse_impact_ratio", "compute_group_adverse_impact",
    # Reporter
    "ComplianceReportData", "ComplianceReporter", "ComplianceSnapshot",
    "TrendDirection", "RiskRating", "compute_risk_rating", "compute_trend",
]
