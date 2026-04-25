"""
SintraPrime Legal Intelligence System

One for All and All for One — the complete AI law firm replacement.
Covers every major practice area, court system, and government agency.

Modules:
    practice_areas: PracticeAreaRouter, LegalMatter, PracticeArea
    court_navigator: CourtNavigator, CourtRecommendation, FilingRequirements
    motion_drafting_engine: MotionDraftingEngine, LegalDocument, ComplianceReport
    contract_intelligence: ContractIntelligence, ContractAnalysis, RedFlag
    criminal_defense_engine: CriminalDefenseEngine, ChargeAnalysis, DefenseStrategy
    civil_rights_engine: CivilRightsEngine, Section1983Analysis, DamagesEstimate
    immigration_engine: ImmigrationEngine, VisaOption, GreenCardOption
    legal_research_engine: LegalResearchEngine, CaseCitation, LegalMemo, LANDMARK_CASES
    government_navigation: GovernmentNavigator, FOIARequest, BenefitsAnalysis

Example:
    >>> from legal_intelligence import PracticeAreaRouter, CourtNavigator
    >>> router = PracticeAreaRouter()
    >>> matter = router.classify_matter("I was fired because of my race")
    >>> matter.practice_area.value
    'employment_law'
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

__all__ = [
    # Practice Areas
    "PracticeArea",
    "LegalMatter",
    "PracticeAreaRouter",
    "LEGAL_STANDARDS",
    # Court Navigator
    "CourtNavigator",
    "CourtRecommendation",
    "FilingRequirements",
    "CourtFiling",
    "TimelineEstimate",
    "JurisdictionAnalysis",
    # Motion Drafting
    "MotionDraftingEngine",
    "LegalDocument",
    "ComplianceReport",
    "MOTION_TEMPLATES",
    # Contract Intelligence
    "ContractIntelligence",
    "ContractAnalysis",
    "RedFlag",
    "NegotiationStrategy",
    "EnforceabilityReport",
    "ContractSummary",
    "RED_FLAG_PATTERNS",
    # Criminal Defense
    "CriminalDefenseEngine",
    "ChargeAnalysis",
    "DefenseStrategy",
    "FourthAmendmentAnalysis",
    "PleaAnalysis",
    "SentencingRange",
    # Civil Rights
    "CivilRightsEngine",
    "Section1983Analysis",
    "EmploymentDiscriminationAnalysis",
    "ADAAnalysis",
    "FirstAmendmentAnalysis",
    "DamagesEstimate",
    "QualifiedImmunityAnalysis",
    # Immigration
    "ImmigrationEngine",
    "VisaOption",
    "GreenCardOption",
    "NaturalizationAnalysis",
    "RemovalDefenseStrategy",
    "AsylumAnalysis",
    "DACAAnalysis",
    "I9ComplianceReport",
    "WaiverStrategy",
    # Legal Research
    "LegalResearchEngine",
    "CaseCitation",
    "CitationHistory",
    "AnalogousCase",
    "RuleSynthesis",
    "LegalMemo",
    "StatuteReference",
    "LegislativeHistory",
    "LANDMARK_CASES",
    # Government Navigation
    "GovernmentNavigator",
    "FOIARequest",
    "BenefitsAnalysis",
    "AppealStrategy",
    "ComplianceChecklist",
    "ContractingStrategy",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Legal Intelligence"
__description__ = "Complete AI law firm replacement — One for All and All for One"
