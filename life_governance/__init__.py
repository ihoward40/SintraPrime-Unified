"""
SintraPrime Life & Entity Governance Engine
============================================
Manages and governs the complete life and property of any living entity.

Modules:
    entity_formation        — Business entity creation and structuring
    estate_planning_engine  — Estate and succession planning
    asset_protection_system — Protection from creditors and liability
    real_estate_intelligence — Real estate from purchase to portfolio
    personal_legal_advisor  — Personal legal situations navigation
    life_command_center     — Master orchestrator for all life domains
"""

from .entity_formation import (
    EntityFormationEngine,
    EntityStructure,
    EntityRecommendation,
    LLCFormationPackage,
    CorporationFormationPackage,
    HoldingStructureStrategy,
    NonprofitFormationPackage,
    AnnualComplianceCalendar,
)

from .estate_planning_engine import (
    EstatePlanningEngine,
    EstatePlan,
    LastWillAndTestament,
    LivingTrustPackage,
    PowerOfAttorney,
    AdvanceDirective,
    EstateTaxStrategy,
    SuccessionPlan,
    DigitalEstatePlan,
)

from .asset_protection_system import (
    AssetProtectionSystem,
    VulnerabilityReport,
    AssetProtectionPlan,
    HomesteadAnalysis,
    RetirementProtectionGuide,
    OffshoreStrategy,
    InsuranceStrategy,
)

from .real_estate_intelligence import (
    RealEstateIntelligence,
    HomePurchaseStrategy,
    MortgageStrategy,
    LandlordGuide,
    InvestmentRealEstateGuide,
    DeedGuide,
)

from .personal_legal_advisor import (
    PersonalLegalAdvisor,
    FamilyLawStrategy,
    NameChangeInstructions,
    IdentityTheftResponsePlan,
    ConsumerRightsGuide,
    EmploymentRightsAnalysis,
)

from .life_command_center import (
    LifeCommandCenter,
    LifeProfile,
    LifeActionPlan,
    ComprehensiveAuditReport,
    UpdatedPlan,
)

__all__ = [
    # Entity Formation
    "EntityFormationEngine",
    "EntityStructure",
    "EntityRecommendation",
    "LLCFormationPackage",
    "CorporationFormationPackage",
    "HoldingStructureStrategy",
    "NonprofitFormationPackage",
    "AnnualComplianceCalendar",
    # Estate Planning
    "EstatePlanningEngine",
    "EstatePlan",
    "LastWillAndTestament",
    "LivingTrustPackage",
    "PowerOfAttorney",
    "AdvanceDirective",
    "EstateTaxStrategy",
    "SuccessionPlan",
    "DigitalEstatePlan",
    # Asset Protection
    "AssetProtectionSystem",
    "VulnerabilityReport",
    "AssetProtectionPlan",
    "HomesteadAnalysis",
    "RetirementProtectionGuide",
    "OffshoreStrategy",
    "InsuranceStrategy",
    # Real Estate
    "RealEstateIntelligence",
    "HomePurchaseStrategy",
    "MortgageStrategy",
    "LandlordGuide",
    "InvestmentRealEstateGuide",
    "DeedGuide",
    # Personal Legal
    "PersonalLegalAdvisor",
    "FamilyLawStrategy",
    "NameChangeInstructions",
    "IdentityTheftResponsePlan",
    "ConsumerRightsGuide",
    "EmploymentRightsAnalysis",
    # Life Command Center
    "LifeCommandCenter",
    "LifeProfile",
    "LifeActionPlan",
    "ComprehensiveAuditReport",
    "UpdatedPlan",
]
