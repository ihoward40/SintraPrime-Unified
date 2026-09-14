"""
SintraPrime Legal Intelligence System

One for All and All for One — the complete AI law firm replacement.
Covers every major practice area, court system, and government agency.
"""

from legal_intelligence.practice_areas import (
    PracticeArea,
    LegalMatter,
    PracticeAreaRouter,
    LEGAL_STANDARDS,
)
from legal_intelligence.court_navigator import (
    CourtNavigator,
    CourtRecommendation,
    FilingRequirements,
    CourtFiling,
    TimelineEstimate,
    JurisdictionAnalysis,
)
from legal_intelligence.motion_drafting_engine import (
    MotionDraftingEngine,
    LegalDocument,
    ComplianceReport,
    MOTION_TEMPLATES,
)
from legal_intelligence.contract_intelligence import (
    ContractIntelligence,
    ContractAnalysis,
    RedFlag,
    NegotiationStrategy,
    EnforceabilityReport,
    ContractSummary,
    RED_FLAG_PATTERNS,
)
from legal_intelligence.criminal_defense_engine import (
    CriminalDefenseEngine,
    ChargeAnalysis,
    DefenseStrategy,
    FourthAmendmentAnalysis,
    PleaAnalysis,
    SentencingRange,
)
from legal_intelligence.civil_rights_engine import (
    CivilRightsEngine,
    Section1983Analysis,
    EmploymentDiscriminationAnalysis,
    ADAAnalysis,
    FirstAmendmentAnalysis,
    DamagesEstimate,
    QualifiedImmunityAnalysis,
)
from legal_intelligence.immigration_engine import (
    ImmigrationEngine,
    VisaOption,
    GreenCardOption,
    NaturalizationAnalysis,
    RemovalDefenseStrategy,
    AsylumAnalysis,
    DACAAnalysis,
    I9ComplianceReport,
    WaiverStrategy,
)
from legal_intelligence.legal_research_engine import (
    LegalResearchEngine,
    CaseCitation,
    CitationHistory,
    AnalogousCase,
    RuleSynthesis,
    LegalMemo,
    StatuteReference,
    LegislativeHistory,
    LANDMARK_CASES,
)
from legal_intelligence.government_navigation import (
    GovernmentNavigator,
    FOIARequest,
    BenefitsAnalysis,
    AppealStrategy,
    ComplianceChecklist,
    ContractingStrategy,
)
from legal_intelligence.transaction_capacity_gate import (
    TransactionCapacityGate,
    TransactionCapacityGateError,
    TheoryClassification,
    GateDecision,
)
from legal_intelligence.rare_legal_levers import RareLegalLeverageEngine, LegalLever
from legal_intelligence.procedural_traps import ProceduralTrapScanner, ProceduralTrap
from legal_intelligence.ike_advantage import IKEAdvantageEngine, AdvantageControl, TreasuryStep
from legal_intelligence.private_capital import PrivateCapitalEngine, CapitalDecision, CapitalFinding, CapitalReport
from legal_intelligence.capital_ledger import CapitalLedgerEngine, CapitalLedgerEntry, LedgerLine, FacilitySnapshot
from legal_intelligence.credit_committee import CreditCommitteeEngine, CreditDecision
from legal_intelligence.receivables import ReceivablesEngine, Receivable, BorrowingBaseReport
from legal_intelligence.related_party import RelatedPartyEngine, RelatedPartyReport
from legal_intelligence.private_capital_docs import PrivateCapitalDocsEngine, DocumentTemplateSpec
from legal_intelligence.capital_risk import CapitalRiskEngine, CapitalRiskReport

__all__ = [
    "PracticeArea", "LegalMatter", "PracticeAreaRouter", "LEGAL_STANDARDS",
    "CourtNavigator", "CourtRecommendation", "FilingRequirements", "CourtFiling", "TimelineEstimate", "JurisdictionAnalysis",
    "MotionDraftingEngine", "LegalDocument", "ComplianceReport", "MOTION_TEMPLATES",
    "ContractIntelligence", "ContractAnalysis", "RedFlag", "NegotiationStrategy", "EnforceabilityReport", "ContractSummary", "RED_FLAG_PATTERNS",
    "CriminalDefenseEngine", "ChargeAnalysis", "DefenseStrategy", "FourthAmendmentAnalysis", "PleaAnalysis", "SentencingRange",
    "CivilRightsEngine", "Section1983Analysis", "EmploymentDiscriminationAnalysis", "ADAAnalysis", "FirstAmendmentAnalysis", "DamagesEstimate", "QualifiedImmunityAnalysis",
    "ImmigrationEngine", "VisaOption", "GreenCardOption", "NaturalizationAnalysis", "RemovalDefenseStrategy", "AsylumAnalysis", "DACAAnalysis", "I9ComplianceReport", "WaiverStrategy",
    "LegalResearchEngine", "CaseCitation", "CitationHistory", "AnalogousCase", "RuleSynthesis", "LegalMemo", "StatuteReference", "LegislativeHistory", "LANDMARK_CASES",
    "GovernmentNavigator", "FOIARequest", "BenefitsAnalysis", "AppealStrategy", "ComplianceChecklist", "ContractingStrategy",
    "TransactionCapacityGate", "TransactionCapacityGateError", "TheoryClassification", "GateDecision",
    "RareLegalLeverageEngine", "LegalLever", "ProceduralTrapScanner", "ProceduralTrap",
    "IKEAdvantageEngine", "AdvantageControl", "TreasuryStep",
    "PrivateCapitalEngine", "CapitalDecision", "CapitalFinding", "CapitalReport",
    "CapitalLedgerEngine", "CapitalLedgerEntry", "LedgerLine", "FacilitySnapshot",
    "CreditCommitteeEngine", "CreditDecision",
    "ReceivablesEngine", "Receivable", "BorrowingBaseReport",
    "RelatedPartyEngine", "RelatedPartyReport",
    "PrivateCapitalDocsEngine", "DocumentTemplateSpec",
    "CapitalRiskEngine", "CapitalRiskReport",
]

__version__ = "1.3.0"
__author__ = "SintraPrime Legal Intelligence"
__description__ = "Legal intelligence with transaction-capacity, leverage, procedure, evidence, and private-capital controls"
