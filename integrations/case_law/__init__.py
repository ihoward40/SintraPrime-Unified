"""
SintraPrime Case Law & Legal Data Integration
=============================================
"""

from .courtlistener_client import CourtListenerClient
from .congress_api import CongressAPIClient
from .citation_network import CitationNetworkBuilder, CitationNetwork, CitationEdge, CaseNode, CitationReport
from .precedent_finder import (
    PrecedentFinder,
    PrecedentResult,
    PrecedentBrief,
    PrecedentCandidate,
    BindingStatus,
    JurisdictionFilter,
)
from .case_alert_system import CaseAlertSystem
from .opinion_analyzer import OpinionAnalyzer
from .case_law_search_engine import CaseLawSearchEngine
from .jurisdiction_mapper import JurisdictionMapper
from .statute_tracker import StatuteTracker
from .regulatory_monitor import RegulatoryMonitor
from .legal_news_aggregator import LegalNewsAggregator
from .state_courts import StateCourtNavigator
from .pacer_navigator import PACERNavigator

__all__ = [
    "CourtListenerClient",
    "CongressAPIClient",
    "CitationNetworkBuilder",
    "CitationNetwork",
    "CitationEdge",
    "CaseNode",
    "CitationReport",
    "PrecedentFinder",
    "PrecedentResult",
    "PrecedentBrief",
    "PrecedentCandidate",
    "BindingStatus",
    "JurisdictionFilter",
    "CaseAlertSystem",
    "OpinionAnalyzer",
    "CaseLawSearchEngine",
    "JurisdictionMapper",
    "StatuteTracker",
    "RegulatoryMonitor",
    "LegalNewsAggregator",
    "StateCourtNavigator",
    "PACERNavigator",
]

__version__ = "1.0.0"
__author__ = "SintraPrime Legal Intelligence"
