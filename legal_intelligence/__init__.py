"""
SintraPrime Legal Intelligence System

One for All and All for One — the complete AI law firm replacement.
Covers every major practice area, court system, and government agency.
"""

from legal_intelligence.practice_areas import PracticeArea, LegalMatter, PracticeAreaRouter, LEGAL_STANDARDS
from legal_intelligence.court_navigator import CourtNavigator, CourtRecommendation, FilingRequirements, CourtFiling, TimelineEstimate, JurisdictionAnalysis
from legal_intelligence.motion_drafting_engine import MotionDraftingEngine, LegalDocument, ComplianceReport, MOTION_TEMPLATES
from legal_intelligence.contract_intelligence import ContractIntelligence, ContractAnalysis, RedFlag, NegotiationStrategy, EnforceabilityReport, ContractSummary, RED_FLAG_PATTERNS
from legal_intelligence.criminal_defense_engine import CriminalDefenseEngine, ChargeAnalysis, DefenseStrategy, FourthAmendmentAnalysis, PleaAnalysis, SentencingRange
from legal_intelligence.civil_rights_engine import CivilRightsEngine, Section1983Analysis, EmploymentDiscriminationAnalysis, ADAAnalysis, FirstAmendmentAnalysis, DamagesEstimate, QualifiedImmunityAnalysis
from legal_intelligence.immigration_engine import ImmigrationEngine, VisaOption, GreenCardOption, NaturalizationAnalysis, RemovalDefenseStrategy, AsylumAnalysis, DACAAnalysis, I9ComplianceReport, WaiverStrategy
from legal_intelligence.legal_research_engine import LegalResearchEngine, CaseCitation, CitationHistory, AnalogousCase, RuleSynthesis, LegalMemo, StatuteReference, LegislativeHistory, LANDMARK_CASES
from legal_intelligence.government_navigation import GovernmentNavigator, FOIARequest, BenefitsAnalysis, AppealStrategy, ComplianceChecklist, ContractingStrategy
from legal_intelligence.transaction_capacity_gate import TransactionCapacityGate, TransactionCapacityGateError, TheoryClassification, GateDecision
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
from legal_intelligence.capital_servicing import CapitalServicingEngine, ServicingReport
from legal_intelligence.capital_dashboard import CapitalDashboardEngine, CapitalDashboardReport
from legal_intelligence.decision_journal import DecisionJournalHashChain, DecisionJournalEntry
from legal_intelligence.hash_anchor import HashAnchorEngine, AnchorReceipt, AnchorReport
from legal_intelligence.workout_recovery import WorkoutRecoveryEngine, RecoveryScenario
from legal_intelligence.collateral_monitor import CollateralMonitorEngine, CollateralMonitorReport
from legal_intelligence.capital_audit import CapitalAuditEngine, CapitalAuditReport
from legal_intelligence.capital_custody import CapitalCustodyEngine, CustodyDecision, CustodyRoleAssignment
from legal_intelligence.capital_continuity import CapitalContinuityEngine, ContinuityReport
from legal_intelligence.capital_stress import CapitalStressEngine, StressResult
from legal_intelligence.capital_policy_engine import CapitalPolicyEngine, CapitalPolicy, PolicyEvaluation
from legal_intelligence.capital_early_warning import CapitalEarlyWarningEngine, EarlyWarningSignal, EarlyWarningReport
from legal_intelligence.policy_change_control import PolicyChangeControlEngine, PolicyChangeRequest, PolicyChangeDecision
from legal_intelligence.capital_escalation import CapitalEscalationEngine, EscalationSignal, EscalationDecision
from legal_intelligence.capital_case_management import CapitalCaseManagementEngine, CapitalCase
from legal_intelligence.capital_override import CapitalOverrideEngine, CapitalOverride
from legal_intelligence.capital_risk_trends import CapitalRiskTrendsEngine, RiskTrendPoint, RiskTrendReport
from legal_intelligence.capital_committee_pack import CapitalCommitteePackEngine, CommitteePack
from legal_intelligence.capital_committee_decisions import CapitalCommitteeDecisionsEngine, CommitteeDecision, CommitteeDecisionValidation
from legal_intelligence.capital_action_tracker import CapitalActionTrackerEngine, CapitalAction, ActionStatusReport
from legal_intelligence.capital_outcome_review import CapitalOutcomeReviewEngine, OutcomeReview, MetricOutcome
from legal_intelligence.capital_lessons_learned import CapitalLessonsLearnedEngine, CapitalLesson
from legal_intelligence.capital_control_validation import CapitalControlValidationEngine, ControlObservation, ControlValidationReport
from legal_intelligence.capital_rule_registry import CapitalRuleRegistryEngine, CapitalRuleRecord, RuleRegistryDecision
from legal_intelligence.capital_rule_dependency import CapitalRuleDependencyEngine, RuleDependency, RuleDependencyReport
from legal_intelligence.capital_champion_challenger import CapitalChampionChallengerEngine, RuleTestObservation, RulePerformance, ChampionChallengerReport
from legal_intelligence.capital_data_quality import CapitalDataQualityEngine, DataQualitySnapshot, DataQualityReport
from legal_intelligence.capital_drift_monitor import CapitalDriftMonitorEngine, DriftFeatureObservation, DriftFeatureResult, DriftMonitorReport

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
    "CapitalServicingEngine", "ServicingReport",
    "CapitalDashboardEngine", "CapitalDashboardReport",
    "DecisionJournalHashChain", "DecisionJournalEntry",
    "HashAnchorEngine", "AnchorReceipt", "AnchorReport",
    "WorkoutRecoveryEngine", "RecoveryScenario",
    "CollateralMonitorEngine", "CollateralMonitorReport",
    "CapitalAuditEngine", "CapitalAuditReport",
    "CapitalCustodyEngine", "CustodyDecision", "CustodyRoleAssignment",
    "CapitalContinuityEngine", "ContinuityReport",
    "CapitalStressEngine", "StressResult",
    "CapitalPolicyEngine", "CapitalPolicy", "PolicyEvaluation",
    "CapitalEarlyWarningEngine", "EarlyWarningSignal", "EarlyWarningReport",
    "PolicyChangeControlEngine", "PolicyChangeRequest", "PolicyChangeDecision",
    "CapitalEscalationEngine", "EscalationSignal", "EscalationDecision",
    "CapitalCaseManagementEngine", "CapitalCase",
    "CapitalOverrideEngine", "CapitalOverride",
    "CapitalRiskTrendsEngine", "RiskTrendPoint", "RiskTrendReport",
    "CapitalCommitteePackEngine", "CommitteePack",
    "CapitalCommitteeDecisionsEngine", "CommitteeDecision", "CommitteeDecisionValidation",
    "CapitalActionTrackerEngine", "CapitalAction", "ActionStatusReport",
    "CapitalOutcomeReviewEngine", "OutcomeReview", "MetricOutcome",
    "CapitalLessonsLearnedEngine", "CapitalLesson",
    "CapitalControlValidationEngine", "ControlObservation", "ControlValidationReport",
    "CapitalRuleRegistryEngine", "CapitalRuleRecord", "RuleRegistryDecision",
    "CapitalRuleDependencyEngine", "RuleDependency", "RuleDependencyReport",
    "CapitalChampionChallengerEngine", "RuleTestObservation", "RulePerformance", "ChampionChallengerReport",
    "CapitalDataQualityEngine", "DataQualitySnapshot", "DataQualityReport",
    "CapitalDriftMonitorEngine", "DriftFeatureObservation", "DriftFeatureResult", "DriftMonitorReport",
]

__version__ = "2.5.0"
__author__ = "SintraPrime Legal Intelligence"
__description__ = "Legal intelligence with governed data-quality and drift monitoring, champion/challenger shadow testing, rule dependency mapping, control validation, institutional learning, committee follow-through, centralized policy, escalation, stress, audit, and tamper-evident governance controls"
