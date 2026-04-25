"""
SintraPrime Trust Law Intelligence System
==========================================
The first AI agent system to achieve mastery-level understanding of Trust Law
across all major jurisdictions, instruments, and doctrines.

Philosophy: "One for All and All for One" — knowledge shared across all agents.

Modules:
    trust_knowledge_base      — Core trust law doctrines, jurisdictions, UCC concepts
    trust_reasoning_engine    — Multi-step chain-of-thought trust analysis
    trust_document_generator  — Full legal document template generation
    jurisdiction_analyzer     — Optimal jurisdiction finder and comparator
    asset_protection_planner  — Layered asset protection strategy builder
    ucc_filing_assistant      — UCC-1/3 form preparation and analysis
    trust_parliament          — Multi-agent deliberation system
    trust_case_law            — Landmark case database and precedent analysis
"""

from .trust_knowledge_base import TrustKnowledgeBase
from .trust_reasoning_engine import TrustReasoningEngine
from .trust_document_generator import TrustDocumentGenerator
from .jurisdiction_analyzer import JurisdictionAnalyzer
from .asset_protection_planner import AssetProtectionPlanner
from .ucc_filing_assistant import UCCFilingAssistant
from .trust_parliament import TrustParliament
from .trust_case_law import TrustCaseLawDB

__all__ = [
    "TrustKnowledgeBase",
    "TrustReasoningEngine",
    "TrustDocumentGenerator",
    "JurisdictionAnalyzer",
    "AssetProtectionPlanner",
    "UCCFilingAssistant",
    "TrustParliament",
    "TrustCaseLawDB",
]

__version__ = "2.0.0"
__author__ = "SintraPrime Intelligence Core"
__description__ = "Mastery-level Trust Law AI Intelligence System"
__jurisdiction_coverage__ = "All 50 US States + 7 International Jurisdictions"
__doctrine_count__ = 30
__case_law_entries__ = 25
