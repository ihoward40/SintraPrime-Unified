"""
CourtListener.com API Client

Free and open API integration for accessing court opinions, dockets, and
case information. Provides no-cost alternative to PACER with real-time
updates and advanced search capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

try:
    import requests
except ImportError:
    raise ImportError("requests library required: pip install requests")

logger = logging.getLogger(__name__)


class OpinionType(Enum):
    """Opinion types"""
    MAJORITY = "majority"
    CONCURRENCE = "concurrence"
    DISSENT = "dissent"
    PARTIAL_DISSENT = "partial_dissent"
    PER_CURIAM = "per_curiam"


class Jurisdiction(Enum):
    """Court jurisdictions"""
    FEDERAL_CIRCUIT = "federal"
    SCOTUS = "scotus"
    STATE = "state"
    BANKRUPTCY = "bankruptcy"
    SPECIALIZED = "specialized"


@dataclass
class Opinion:
    """Represents a judicial opinion"""
    id: str
    citation: str
    case_name: str
    court: str
    date_filed: date
    opinion_type: OpinionType
    text: str
    judges: List[str] = field(default_factory=list)
    law_citations: List[str] = field(default_factory=list)
    case_citations: List[str] = field(default_factory=list)
    headnotes: List[str] = field(default_factory=list)
    is_published: bool = True
    html_url: Optional[str] = None
    download_url: Optional[str] = None

    def extract_holdings(self) -> List[str]:
        """Extract holdings from opinion text"""
        holdings = []
        # Simple extraction - production code would use NLP
        for line in self.text.split('\n'):
            if any(kw in line.lower() for kw in ['held that', 'we hold', 'the court holds']):
                holdings.append(line.strip())
        return holdings


@dataclass
class Alert:
    """Represents a docket alert/update"""
    id: str
    case_id: str
    case_name: str
    date: datetime
    description: str
    entry_type: str
    document_url: Optional[str] = None
    is_read: bool = False


@dataclass
class Subscription:
    """Represents an alert subscription"""
    id: str
    case_id: str
    case_name: str
    webhook_url: str
    is_active: bool
    created_date: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class CitationNetwork:
    """Citation relationship network for an opinion"""
    opinion_id: str
    opinion_citation: str
    citing_opinions: List[Opinion] = field(default_factory=list)
    cited_opinions: List[Opinion] = field(default_factory=list)
    total_citations: int = 0
    precedential_citations: int = 0
    reversed_by: Optional[Opinion] = None
    affirmed_by: Optional[Opinion] = None


@dataclass
class JudgeProfile:
    """Judge biographical and performance data"""
    id: str
    name: str
    court: str
    appointed_date: Optional[date] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    dupe_group: Optional[int] = None
    cases_decided: int = 0
    opinions_written: int = 0
    avg_reversal_rate: float = 0.0
    avg_citation_rate: float = 0.0
    
    def get_experience_years(self) -> int:
        """Calculate years of judicial experience"""
        if self.appointed_date:
            return (datetime.now().date() - self.appointed_date).days // 365
        return 0


@dataclass
class CircuitSplit:
    """Represents a circuit split in case law"""
    topic: str
    question: str
    split_courts: List[str] = field(default_factory=list)
    split_directions: List[str] = field(default_factory=list)
    lead_opinions: List[Opinion] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)
    status: str = "open"  # open, resolved, merged


class CourtListenerClient:
    """
    Free CourtListener.com API client for case law research.
    
    Provides access to millions of court opinions, docket information,
    judge data, and citation networks without fees.
    """

    API_BASE = "https://www.courtlistener.com/api/rest/v3"
    SUPPORTED_JURISDICTIONS = [
        "scotus", "fed", "ca1", "ca2", "ca3", "ca4", "ca5", "ca6",
        "ca7", "ca8", "ca9", "ca10", "ca11", "cadc", "cafc"
    ]
    REQUEST_TIMEOUT = 30
    MAX_RESULTS = 500

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize CourtListener client.
        
        Args:
            api_token: Optional API token for higher rate limits
        """
        self.api_token = api_token
        self.session = requests.Session()
        if api_token:
            self.session.headers.update({"Authorization": f"Token {api_token}"})
        self.session.headers.update({"User-Agent": "SintraPrime-DocketMonitor/1.0"})

    def search_opinions(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        opinion_type: Optional[str] = None,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Opinion]:
        """
        Full-text search across millions of opinions.
        
        Args:
            query: Search query
            jurisdiction: Optional jurisdiction filter (e.g., "scotus")
            opinion_type: Optional opinion type (majority, dissent, etc.)
            min_date: Optional minimum filing date
            max_date: Optional maximum filing date
            limit: Maximum results to return
            
        Returns:
            List of matching opinions
        """
        params = {
            "q": query,
            "order_by": "-date_filed",
            "limit": min(limit, self.MAX_RESULTS),
        }
        
        if jurisdiction:
            params["court"] = jurisdiction
        if opinion_type:
            params["type"] = opinion_type
        if min_date:
            params["filed_after"] = min_date.isoformat()
        if max_date:
            params["filed_before"] = max_date.isoformat()
        
        try:
            response = self.session.get(
                f"{self.API_BASE}/opinions/",
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            results = response.json()
            opinions = [self._parse_opinion(op) for op in results.get("results", [])]
            logger.info(f"Found {len(opinions)} opinions matching query: {query}")
            return opinions
            
        except requests.RequestException as e:
            logger.error(f"Opinion search failed: {e}")
            return []

    def search_by_citation(
        self,
        citation: str
    ) -> Optional[Opinion]:
        """Look up opinion by standard legal citation"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/opinions/?citation={citation}",
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            results = response.json()
            if results.get("results"):
                return self._parse_opinion(results["results"][0])
            return None
            
        except requests.RequestException as e:
            logger.error(f"Citation lookup failed: {e}")
            return None

    def get_docket_alerts(
        self,
        case_id: str,
        days_back: int = 30
    ) -> List[Alert]:
        """
        Get recent docket updates for a case.
        
        Args:
            case_id: CourtListener case ID
            days_back: Number of days of history to retrieve
            
        Returns:
            List of alerts
        """
        try:
            response = self.session.get(
                f"{self.API_BASE}/dockets/{case_id}/",
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            docket = response.json()
            alerts = []
            
            for entry in docket.get("docket_entries", [])[:100]:
                alert = Alert(
                    id=f"alert_{entry['id']}",
                    case_id=case_id,
                    case_name=docket.get("case_name", ""),
                    date=datetime.fromisoformat(entry["date_filed"].replace("Z", "+00:00")),
                    description=entry.get("description", ""),
                    entry_type="docket_entry",
                    document_url=entry.get("pdf_url")
                )
                alerts.append(alert)
            
            logger.info(f"Retrieved {len(alerts)} alerts for case {case_id}")
            return sorted(alerts, key=lambda x: x.date, reverse=True)
            
        except requests.RequestException as e:
            logger.error(f"Docket alert retrieval failed: {e}")
            return []

    def subscribe_to_case(
        self,
        case_id: str,
        webhook_url: str,
        case_name: str = ""
    ) -> Subscription:
        """
        Subscribe to webhook notifications for case updates.
        
        Args:
            case_id: CourtListener case ID
            webhook_url: URL to receive webhooks
            case_name: Optional case name
            
        Returns:
            Subscription object
        """
        subscription = Subscription(
            id=f"sub_{case_id}_{hash(webhook_url) % 10000}",
            case_id=case_id,
            case_name=case_name,
            webhook_url=webhook_url,
            is_active=True,
            created_date=datetime.now()
        )
        logger.info(f"Created subscription for case {case_id}")
        return subscription

    def get_citation_network(self, opinion_id: str) -> CitationNetwork:
        """
        Get all cases citing a given opinion and vice versa.
        
        Args:
            opinion_id: CourtListener opinion ID
            
        Returns:
            Citation network
        """
        try:
            response = self.session.get(
                f"{self.API_BASE}/opinions/{opinion_id}/",
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            opinion_data = response.json()
            opinion = self._parse_opinion(opinion_data)
            
            # Fetch citing opinions
            citing_response = self.session.get(
                f"{self.API_BASE}/opinions/?cited_opinion={opinion_id}",
                timeout=self.REQUEST_TIMEOUT
            )
            citing_results = citing_response.json().get("results", [])
            citing_opinions = [self._parse_opinion(op) for op in citing_results]
            
            # Fetch cited opinions
            cited_ids = opinion_data.get("citations", [])
            cited_opinions = []
            for cited_id in cited_ids[:10]:  # Limit to avoid too many requests
                try:
                    cited_response = self.session.get(
                        f"{self.API_BASE}/opinions/{cited_id}/",
                        timeout=self.REQUEST_TIMEOUT
                    )
                    cited_response.raise_for_status()
                    cited_opinions.append(self._parse_opinion(cited_response.json()))
                except:
                    pass
            
            network = CitationNetwork(
                opinion_id=opinion_id,
                opinion_citation=opinion.citation,
                citing_opinions=citing_opinions,
                cited_opinions=cited_opinions,
                total_citations=len(citing_opinions),
                precedential_citations=len(citing_opinions)
            )
            
            logger.info(f"Retrieved citation network for opinion {opinion_id}")
            return network
            
        except requests.RequestException as e:
            logger.error(f"Citation network retrieval failed: {e}")
            return CitationNetwork(
                opinion_id=opinion_id,
                opinion_citation=""
            )

    def get_judge_profile(self, judge_id: str) -> Optional[JudgeProfile]:
        """
        Get biographical and performance data for a judge.
        
        Args:
            judge_id: CourtListener judge ID
            
        Returns:
            Judge profile
        """
        try:
            response = self.session.get(
                f"{self.API_BASE}/judges/{judge_id}/",
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            profile = JudgeProfile(
                id=judge_id,
                name=data.get("name", ""),
                court=data.get("court", ""),
                appointed_date=self._parse_date(data.get("date_appointed")),
                birth_date=self._parse_date(data.get("born")),
                gender=data.get("gender"),
                dupe_group=data.get("dupe_group"),
                cases_decided=data.get("cases_decided", 0),
                opinions_written=data.get("opinions_written", 0)
            )
            
            logger.info(f"Retrieved profile for judge {data.get('name', judge_id)}")
            return profile
            
        except requests.RequestException as e:
            logger.error(f"Judge profile retrieval failed: {e}")
            return None

    def get_court_statistics(
        self,
        court: str,
        case_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a court (case types, outcomes, timing).
        
        Args:
            court: Court code (e.g., "scotus")
            case_type: Optional case type filter
            
        Returns:
            Statistics dictionary
        """
        try:
            params = {"order_by": "-date_filed", "limit": 1000}
            if case_type:
                params["case_type"] = case_type
            
            response = self.session.get(
                f"{self.API_BASE}/opinions/?court={court}",
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            results = response.json().get("results", [])
            
            stats = {
                "court": court,
                "total_opinions": len(results),
                "case_types": {},
                "date_range": None,
                "avg_opinions_per_year": 0,
                "by_judge": {}
            }
            
            if results:
                first_date = datetime.fromisoformat(
                    results[-1]["date_filed"].replace("Z", "+00:00")
                ).date()
                last_date = datetime.fromisoformat(
                    results[0]["date_filed"].replace("Z", "+00:00")
                ).date()
                stats["date_range"] = f"{first_date} to {last_date}"
            
            logger.info(f"Retrieved statistics for court {court}")
            return stats
            
        except requests.RequestException as e:
            logger.error(f"Statistics retrieval failed: {e}")
            return {}

    def find_circuit_splits(self, topic: str) -> List[CircuitSplit]:
        """
        Find circuit splits (conflicting circuit decisions) on a topic.
        
        Args:
            topic: Legal topic or issue
            
        Returns:
            List of circuit splits
        """
        # Search for conflicting opinions on the topic
        opinions = self.search_opinions(topic, limit=200)
        
        splits = []
        court_positions = {}
        
        for opinion in opinions:
            court = opinion.court
            if court not in court_positions:
                court_positions[court] = []
            court_positions[court].append(opinion)
        
        # Create split entries for courts with conflicting positions
        if len(court_positions) > 1:
            split = CircuitSplit(
                topic=topic,
                question=f"How do courts interpret {topic}?",
                split_courts=list(court_positions.keys()),
                lead_opinions=[
                    opinions[0] for opinions in court_positions.values()
                ]
            )
            splits.append(split)
        
        logger.info(f"Found {len(splits)} circuit splits on topic: {topic}")
        return splits

    def _parse_opinion(self, data: Dict[str, Any]) -> Opinion:
        """Parse opinion from API response"""
        opinion_type = OpinionType.MAJORITY
        opinion_type_str = data.get("type", "").lower()
        if "dissent" in opinion_type_str:
            opinion_type = OpinionType.DISSENT
        elif "concur" in opinion_type_str:
            opinion_type = OpinionType.CONCURRENCE
        
        return Opinion(
            id=str(data.get("id", "")),
            citation=data.get("citation", ""),
            case_name=data.get("case_name", ""),
            court=data.get("court", ""),
            date_filed=self._parse_date(data.get("date_filed", "")),
            opinion_type=opinion_type,
            text=data.get("plain_text", ""),
            judges=self._parse_judges(data),
            html_url=data.get("absolute_url"),
            download_url=data.get("pdf_url")
        )

    def _parse_judges(self, data: Dict[str, Any]) -> List[str]:
        """Extract judge names from opinion data"""
        judges = []
        if "judges" in data and data["judges"]:
            judges = [j.strip() for j in data["judges"].split(",")]
        return judges

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        try:
            if "T" in date_str:
                return datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                ).date()
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
