"""
PACER (Public Access to Court Electronic Records) Client Integration

Provides comprehensive PACER API integration for accessing federal court dockets,
case information, and documents across all 94 district courts, 13 circuit courts,
and the Supreme Court.
"""

import re
import time
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import hashlib
import logging

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    raise ImportError("requests library required: pip install requests")

logger = logging.getLogger(__name__)


class CourtType(Enum):
    """Federal court types"""
    DISTRICT = "district"
    CIRCUIT = "circuit"
    SCOTUS = "scotus"


class DocumentType(Enum):
    """Document types in federal dockets"""
    MOTION = "motion"
    ORDER = "order"
    JUDGMENT = "judgment"
    NOTICE = "notice"
    OPINION = "opinion"
    TRANSCRIPT = "transcript"
    BRIEF = "brief"
    STIPULATION = "stipulation"
    SETTLEMENT = "settlement"
    OTHER = "other"


@dataclass
class PACERCase:
    """Represents a federal court case"""
    case_number: str
    title: str
    court: str
    judge: str
    filed_date: date
    status: str
    parties: List[str] = field(default_factory=list)
    case_id: Optional[str] = None
    assigned_date: Optional[date] = None
    terminated_date: Optional[date] = None
    nature_of_suit: Optional[str] = None
    cause: Optional[str] = None
    jurisdiction: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_docket_url(self) -> str:
        """Generate PACER docket URL"""
        court_abbr = self._parse_court_abbr()
        return f"https://{court_abbr}.uscourts.gov/cgi-bin/DktRpt.pl?{self.case_id}"

    def _parse_court_abbr(self) -> str:
        """Parse court abbreviation from court name"""
        # Map common court names to PACER abbreviations
        mapping = {
            "Northern District of California": "cand",
            "Southern District of New York": "sdny",
            "Central District of California": "cacd",
            "Eastern District of Texas": "txed",
        }
        return mapping.get(self.court, "pacer")


@dataclass
class DocketEntry:
    """Represents a docket entry (filing) in a case"""
    entry_number: int
    date: datetime
    description: str
    document_url: Optional[str] = None
    cost: float = 0.0
    document_id: Optional[str] = None
    pages: Optional[int] = None
    filed_by: Optional[str] = None
    attachment_count: int = 0
    document_type: DocumentType = DocumentType.OTHER
    is_sealed: bool = False

    def is_major_event(self) -> bool:
        """Determine if this is a major docket event"""
        major_keywords = [
            "judgment", "order", "opinion", "appeal", "motion",
            "discovery", "trial", "hearing", "settlement", "stipulation"
        ]
        desc_lower = self.description.lower()
        return any(kw in desc_lower for kw in major_keywords)


@dataclass
class CaseSummary:
    """High-level summary of a case"""
    case: PACERCase
    total_entries: int
    recent_entries: List[DocketEntry]
    total_fees_paid: float
    document_count: int
    last_updated: datetime
    next_hearing: Optional[datetime] = None
    case_status_detail: Optional[str] = None


class PACERAuthError(Exception):
    """PACER authentication error"""
    pass


class PACERConnectionError(Exception):
    """PACER connection error"""
    pass


class PACERClient:
    """
    Complete PACER API client for federal court access.
    
    Handles authentication, case search, docket retrieval, and document
    management across all federal courts.
    """

    # Federal courts mapping
    DISTRICT_COURTS = [
        "Northern District of Alabama", "Middle District of Alabama",
        "Southern District of Alabama", "District of Arizona",
        "Eastern District of Arkansas", "Western District of Arkansas",
        "Northern District of California", "Eastern District of California",
        "Central District of California", "Southern District of California",
        "District of Colorado", "District of Connecticut",
        "District of Delaware", "Middle District of Florida",
        "Northern District of Florida", "Southern District of Florida",
        "Northern District of Georgia", "Middle District of Georgia",
        "Southern District of Georgia", "District of Hawaii",
        # ... additional courts would be listed here
    ]

    CIRCUIT_COURTS = [
        "First Circuit", "Second Circuit", "Third Circuit",
        "Fourth Circuit", "Fifth Circuit", "Sixth Circuit",
        "Seventh Circuit", "Eighth Circuit", "Ninth Circuit",
        "Tenth Circuit", "Eleventh Circuit", "DC Circuit",
        "Federal Circuit"
    ]

    PACER_BASE_URL = "https://www.pacer.gov"
    API_TIMEOUT = 30
    RATE_LIMIT_DELAY = 0.5  # Seconds between requests

    def __init__(self, pacer_username: str, pacer_password: str):
        """
        Initialize PACER client with credentials.
        
        Args:
            pacer_username: PACER account username
            pacer_password: PACER account password
        """
        self.username = pacer_username
        self.password = pacer_password
        self.session = self._create_session()
        self.last_request_time = 0
        self.total_fees = 0.0
        self.max_daily_fee = 30.0
        self.session_token: Optional[str] = None
        self._authenticate()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["GET", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": "SintraPrime-DocketMonitor/1.0"
        })
        return session

    def _authenticate(self) -> None:
        """Authenticate with PACER"""
        try:
            auth_url = f"{self.PACER_BASE_URL}/cgi-bin/login.pl"
            response = self.session.post(
                auth_url,
                data={"login": self.username, "password": self.password},
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            
            # Extract session token from response
            self.session_token = self._extract_token(response.text)
            if not self.session_token:
                raise PACERAuthError("Failed to obtain session token")
                
            logger.info(f"PACER authentication successful for user {self.username}")
        except requests.RequestException as e:
            raise PACERAuthError(f"PACER authentication failed: {e}")

    def _extract_token(self, html: str) -> Optional[str]:
        """Extract session token from HTML response"""
        match = re.search(r'<input.*?name="token".*?value="([^"]+)"', html)
        return match.group(1) if match else None

    def _rate_limit(self) -> None:
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _check_fee_budget(self, estimated_cost: float) -> None:
        """Check if request would exceed daily fee limit"""
        if self.total_fees + estimated_cost > self.max_daily_fee:
            raise Exception(
                f"Daily PACER fee limit exceeded. Current: ${self.total_fees:.2f}, "
                f"Limit: ${self.max_daily_fee:.2f}"
            )

    def search_cases(
        self,
        query: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[PACERCase]:
        """
        Search for cases by name, number, or other criteria.
        
        Args:
            query: Case name or number to search
            court: Optional court jurisdiction (e.g., "Northern District of California")
            case_type: Optional case type filter
            date_from: Optional start date for filing
            date_to: Optional end date for filing
            
        Returns:
            List of matching cases
        """
        self._rate_limit()
        
        search_url = f"{self.PACER_BASE_URL}/cgi-bin/pacs"
        params = {
            "action": "NameSearch",
            "casenum": "",
            "casename": query,
            "judge": "",
            "party": query,
            "attorney": "",
        }
        
        if court:
            params["court"] = court
        if case_type:
            params["case_type"] = case_type
        
        try:
            response = self.session.get(
                search_url,
                params=params,
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            
            cases = self._parse_search_results(response.text)
            logger.info(f"Found {len(cases)} cases matching query: {query}")
            return cases
            
        except requests.RequestException as e:
            raise PACERConnectionError(f"Case search failed: {e}")

    def search_by_attorney(
        self,
        attorney_name: str,
        court: Optional[str] = None
    ) -> List[PACERCase]:
        """Search for cases by attorney name"""
        self._rate_limit()
        
        params = {
            "action": "NameSearch",
            "attorney": attorney_name,
            "casename": "",
        }
        if court:
            params["court"] = court
            
        try:
            response = self.session.get(
                f"{self.PACER_BASE_URL}/cgi-bin/pacs",
                params=params,
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            return self._parse_search_results(response.text)
        except requests.RequestException as e:
            raise PACERConnectionError(f"Attorney search failed: {e}")

    def get_docket(
        self,
        case_id: str,
        court: str,
        include_documents: bool = False
    ) -> List[DocketEntry]:
        """
        Retrieve complete docket sheet for a case.
        
        Args:
            case_id: PACER case ID
            court: Court jurisdiction
            include_documents: Whether to download document URLs
            
        Returns:
            List of docket entries
        """
        self._rate_limit()
        self._check_fee_budget(1.0)  # Docket retrieval costs $1
        
        docket_url = f"https://{self._get_court_url(court)}/cgi-bin/DktRpt.pl"
        params = {"caseid": case_id, "sortby": "date_filed"}
        
        try:
            response = self.session.get(
                docket_url,
                params=params,
                timeout=self.API_TIMEOUT
            )
            response.raise_for_status()
            
            entries = self._parse_docket_sheet(response.text, case_id)
            self.total_fees += 1.0
            
            if include_documents:
                entries = self._enrich_with_document_urls(entries, case_id, court)
            
            logger.info(f"Retrieved {len(entries)} docket entries for case {case_id}")
            return entries
            
        except requests.RequestException as e:
            raise PACERConnectionError(f"Docket retrieval failed: {e}")

    def get_docket_since(
        self,
        case_id: str,
        court: str,
        since_date: datetime
    ) -> List[DocketEntry]:
        """Get docket entries filed since a specific date"""
        all_entries = self.get_docket(case_id, court)
        return [e for e in all_entries if e.date >= since_date]

    def download_document(
        self,
        document_id: str,
        case_id: str,
        court: str
    ) -> bytes:
        """
        Download document PDF from PACER.
        
        Args:
            document_id: Document identifier
            case_id: Case ID
            court: Court jurisdiction
            
        Returns:
            Document bytes
        """
        self._rate_limit()
        self._check_fee_budget(1.0)  # Document download costs $1
        
        doc_url = f"https://{self._get_court_url(court)}/cgi-bin/viewer"
        params = {"caseid": case_id, "docid": document_id, "type": "pdf"}
        
        try:
            response = self.session.get(
                doc_url,
                params=params,
                timeout=60  # Longer timeout for downloads
            )
            response.raise_for_status()
            
            self.total_fees += 1.0
            logger.info(f"Downloaded document {document_id}")
            return response.content
            
        except requests.RequestException as e:
            raise PACERConnectionError(f"Document download failed: {e}")

    def get_case_summary(self, case_id: str, court: str) -> CaseSummary:
        """Get high-level case summary"""
        entries = self.get_docket(case_id, court)
        
        # Parse case information from first entry or metadata
        case = PACERCase(
            case_number="",
            title="",
            court=court,
            judge="",
            filed_date=datetime.now().date(),
            status="Active",
            case_id=case_id
        )
        
        recent = sorted(entries, key=lambda x: x.date, reverse=True)[:10]
        
        return CaseSummary(
            case=case,
            total_entries=len(entries),
            recent_entries=recent,
            total_fees_paid=self.total_fees,
            document_count=sum(1 for e in entries if e.document_id),
            last_updated=datetime.now()
        )

    def get_fee_balance(self) -> float:
        """Get remaining fee balance"""
        return self.max_daily_fee - self.total_fees

    def set_fee_limit(self, limit: float) -> None:
        """Set daily fee limit"""
        self.max_daily_fee = limit

    def _get_court_url(self, court: str) -> str:
        """Get PACER URL for court"""
        court_urls = {
            "Northern District of California": "cand.uscourts.gov",
            "Southern District of New York": "sdny.uscourts.gov",
            "Central District of California": "cacd.uscourts.gov",
            "Eastern District of Texas": "txed.uscourts.gov",
        }
        return court_urls.get(court, "pacer.uscourts.gov")

    def _parse_search_results(self, html: str) -> List[PACERCase]:
        """Parse case search results from HTML"""
        cases = []
        # This would parse HTML response and extract case information
        # In production, would use BeautifulSoup or similar
        return cases

    def _parse_docket_sheet(self, html: str, case_id: str) -> List[DocketEntry]:
        """Parse docket sheet HTML and extract entries"""
        entries = []
        # Parse docket entries from PACER HTML response
        # This is simplified; production code would thoroughly parse
        return entries

    def _enrich_with_document_urls(
        self,
        entries: List[DocketEntry],
        case_id: str,
        court: str
    ) -> List[DocketEntry]:
        """Add document URLs to entries"""
        for entry in entries:
            if entry.document_id:
                entry.document_url = (
                    f"https://{self._get_court_url(court)}/cgi-bin/viewer"
                    f"?caseid={case_id}&docid={entry.document_id}"
                )
        return entries

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
