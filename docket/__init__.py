"""
SintraPrime-Unified Docket Monitoring System

Real-time federal and state court docket monitoring with:
- PACER integration for all federal courts
- CourtListener free API access
- Intelligent docket monitoring and change detection
- Multi-channel alert system (email, SMS, Slack, webhooks)
- Comprehensive deadline tracking (FRCP, FRAP, state rules, SOL)
- Supreme Court cert petition and opinion monitoring
- All 50 state court system support
- FastAPI REST and WebSocket interface
"""

__version__ = "1.0.0"
__author__ = "SintraPrime Development"
__all__ = [
    # PACER Client
    "PACERClient",
    "PACERCase",
    "DocketEntry",
    "CaseSummary",
    "CourtType",
    "DocumentType",
    "PACERAuthError",
    "PACERConnectionError",
    
    # CourtListener Client
    "CourtListenerClient",
    "Opinion",
    "OpinionType",
    "Alert",
    "Subscription",
    "CitationNetwork",
    "JudgeProfile",
    "CircuitSplit",
    "Jurisdiction",
    
    # Docket Monitor
    "DocketMonitor",
    "MonitoredCase",
    "DocketUpdate",
    "Deadline",
    "DeadlineType",
    "DeadlineRule",
    "AlertConfig",
    "AlertPriority",
    
    # Alert System
    "AlertSystem",
    "AlertRule",
    "AlertChannel",
    "AlertType",
    
    # Deadline Tracker
    "DeadlineTracker",
    "DeadlineCalculator",
    "StatuteOfLimitations",
    "RiskLevel",
    "RiskReport",
    "DeadlineChain",
    
    # SCOTUS Tracker
    "SCOTUSTracker",
    "CertPetition",
    "OralArgument",
    "SCOTUSOpinion",
    "CertStatus",
    "JusticeVotingPattern",
    
    # State Courts
    "StateCourtMonitor",
    "StateCourt",
    "StateCase",
    "HearingDate",
    "StateCourtLevel",
    "EFilingPlatform",
    
    # API Router
    "router",
]

# Import all classes and functions
from .pacer_client import (
    PACERClient,
    PACERCase,
    DocketEntry,
    CaseSummary,
    CourtType,
    DocumentType,
    PACERAuthError,
    PACERConnectionError,
)

from .courtlistener_client import (
    CourtListenerClient,
    Opinion,
    OpinionType,
    Alert,
    Subscription,
    CitationNetwork,
    JudgeProfile,
    CircuitSplit,
    Jurisdiction,
)

from .docket_monitor import (
    DocketMonitor,
    MonitoredCase,
    DocketUpdate,
    Deadline,
    DeadlineType,
    DeadlineRule,
    AlertConfig,
    AlertPriority,
)

from .alert_system import (
    AlertSystem,
    AlertRule,
    AlertChannel,
    AlertType,
)

from .deadline_tracker import (
    DeadlineTracker,
    DeadlineCalculator,
    StatuteOfLimitations,
    RiskLevel,
    RiskReport,
    DeadlineChain,
)

from .scotus_tracker import (
    SCOTUSTracker,
    CertPetition,
    OralArgument,
    SCOTUSOpinion,
    CertStatus,
    JusticeVotingPattern,
)

from .state_courts import (
    StateCourtMonitor,
    StateCourt,
    StateCase,
    HearingDate,
    StateCourtLevel,
    EFilingPlatform,
)

from .docket_api import router


def get_pacer_client(username: str, password: str) -> PACERClient:
    """
    Create and return authenticated PACER client.
    
    Args:
        username: PACER account username
        password: PACER account password
        
    Returns:
        Authenticated PACER client
        
    Example:
        >>> client = get_pacer_client("my_username", "my_password")
        >>> cases = client.search_cases("Smith v. Jones")
    """
    return PACERClient(username, password)


def get_courtlistener_client(api_token: str = None) -> CourtListenerClient:
    """
    Create and return CourtListener client.
    
    Args:
        api_token: Optional API token for higher rate limits
        
    Returns:
        CourtListener client instance
        
    Example:
        >>> client = get_courtlistener_client()
        >>> opinions = client.search_opinions("First Amendment")
    """
    return CourtListenerClient(api_token)


def create_docket_system(
    pacer_username: str = None,
    pacer_password: str = None,
    courtlistener_token: str = None,
    enable_monitoring: bool = True
) -> dict:
    """
    Create complete docket monitoring system with all components.
    
    Args:
        pacer_username: PACER account username
        pacer_password: PACER account password
        courtlistener_token: CourtListener API token
        enable_monitoring: Whether to enable background monitoring
        
    Returns:
        Dictionary with all system components
        
    Example:
        >>> system = create_docket_system(
        ...     pacer_username="user",
        ...     pacer_password="pass"
        ... )
        >>> monitor = system["monitor"]
        >>> monitor.add_case("1:21-cv-001", "Client", "M-001", "NDCA")
    """
    pacer = None
    cl = None
    
    if pacer_username and pacer_password:
        pacer = PACERClient(pacer_username, pacer_password)
    
    if courtlistener_token:
        cl = CourtListenerClient(courtlistener_token)
    else:
        cl = CourtListenerClient()
    
    monitor = DocketMonitor(pacer, cl)
    alert_system = AlertSystem()
    deadline_tracker = DeadlineTracker()
    scotus = SCOTUSTracker()
    state_courts = StateCourtMonitor()
    
    if enable_monitoring:
        monitor.start_monitoring()
    
    return {
        "pacer": pacer,
        "courtlistener": cl,
        "monitor": monitor,
        "alerts": alert_system,
        "deadlines": deadline_tracker,
        "scotus": scotus,
        "state_courts": state_courts,
    }


# Package metadata
__title__ = "SintraPrime-Unified Docket Monitoring"
__description__ = "Real-time federal and state court docket monitoring system"
__url__ = "https://www.sintraprime.com"
__license__ = "Proprietary"
__copyright__ = "2024 SintraPrime Inc."
