"""
Intelligent Docket Monitoring System

Real-time monitoring of multiple cases with change detection, significance scoring,
deadline extraction, and deadline management.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Set
import logging
import json
import threading
import time

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class DeadlineType(Enum):
    """Types of legal deadlines"""
    RESPONSE_REQUIRED = "response"
    HEARING = "hearing"
    DISCOVERY = "discovery"
    MOTION = "motion"
    APPEAL = "appeal"
    TRIAL = "trial"
    STATUS_CONFERENCE = "status_conference"
    OTHER = "other"


@dataclass
class AlertConfig:
    """Configuration for case monitoring alerts"""
    alert_on_any_filing: bool = True
    alert_on_hearing: bool = True
    alert_on_judgment: bool = True
    alert_on_motion: bool = True
    alert_on_settlement: bool = True
    alert_on_emergency: bool = True
    minimum_significance_score: float = 0.0
    quiet_hours_start: Optional[str] = "22:00"  # 10 PM
    quiet_hours_end: Optional[str] = "08:00"    # 8 AM
    enable_daily_digest: bool = True
    digest_time: str = "09:00"  # 9 AM
    notification_channels: List[str] = field(default_factory=lambda: ["email", "webhook"])


@dataclass
class MonitoredCase:
    """Represents a monitored case"""
    case_id: str
    client_name: str
    matter_number: str
    court: str
    alert_config: AlertConfig
    created_date: datetime = field(default_factory=datetime.now)
    last_checked: Optional[datetime] = None
    last_docket_hash: Optional[str] = None
    new_entries_since_check: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocketUpdate:
    """Represents a detected change in docket"""
    case_id: str
    timestamp: datetime
    entry: Any  # DocketEntry from pacer_client
    significance_score: float
    update_type: str  # NEW, MODIFIED, DELETED
    is_deadline: bool = False
    deadline: Optional['Deadline'] = None


@dataclass
class Deadline:
    """Represents an extracted deadline"""
    deadline_id: str
    case_id: str
    description: str
    due_date: date
    deadline_type: DeadlineType
    rule_reference: Optional[str] = None
    days_until_due: Optional[int] = None
    is_upcoming: bool = False
    is_overdue: bool = False
    raw_text: str = ""

    def update_status(self) -> None:
        """Update deadline status based on current date"""
        today = date.today()
        self.days_until_due = (self.due_date - today).days
        self.is_upcoming = 0 <= self.days_until_due <= 30
        self.is_overdue = self.days_until_due < 0


@dataclass
class DeadlineRule:
    """Rule for deadline calculation"""
    name: str
    days_from_trigger: int
    trigger_event: str
    jurisdiction: str
    rule_set: str = "FRCP"  # FRCP, FRAP, State Rule, etc.
    excludes_weekends: bool = True
    excludes_holidays: bool = True
    notes: str = ""


class DocketMonitor:
    """
    Intelligent case monitoring system.
    
    Monitors unlimited cases simultaneously, detects changes, scores significance,
    extracts deadlines, and manages alerts.
    """

    def __init__(
        self,
        pacer_client=None,
        courtlistener_client=None,
        check_interval_minutes: int = 15
    ):
        """
        Initialize docket monitor.
        
        Args:
            pacer_client: PACER API client
            courtlistener_client: CourtListener API client
            check_interval_minutes: How often to check for updates
        """
        self.pacer_client = pacer_client
        self.courtlistener_client = courtlistener_client
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        
        self.monitored_cases: Dict[str, MonitoredCase] = {}
        self.docket_snapshots: Dict[str, List[Any]] = {}
        self.detected_updates: Dict[str, List[DocketUpdate]] = {}
        
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Webhook callbacks
        self.update_callbacks: List[Callable[[DocketUpdate], None]] = []

    def add_case(
        self,
        case_id: str,
        client_name: str,
        matter_number: str,
        court: str,
        alert_config: Optional[AlertConfig] = None,
        tags: Optional[List[str]] = None
    ) -> MonitoredCase:
        """
        Add a case to monitoring.
        
        Args:
            case_id: PACER case ID
            client_name: Client name
            matter_number: Internal matter number
            court: Court jurisdiction
            alert_config: Alert configuration
            tags: Optional tags for categorization
            
        Returns:
            Monitored case object
        """
        if case_id in self.monitored_cases:
            logger.warning(f"Case {case_id} already being monitored")
            return self.monitored_cases[case_id]
        
        monitored = MonitoredCase(
            case_id=case_id,
            client_name=client_name,
            matter_number=matter_number,
            court=court,
            alert_config=alert_config or AlertConfig(),
            tags=tags or []
        )
        
        self.monitored_cases[case_id] = monitored
        self.detected_updates[case_id] = []
        
        # Take initial snapshot
        self._take_docket_snapshot(case_id)
        
        logger.info(f"Added case {case_id} for monitoring ({matter_number})")
        return monitored

    def remove_case(self, case_id: str) -> bool:
        """Remove case from monitoring"""
        if case_id not in self.monitored_cases:
            return False
        
        del self.monitored_cases[case_id]
        if case_id in self.docket_snapshots:
            del self.docket_snapshots[case_id]
        if case_id in self.detected_updates:
            del self.detected_updates[case_id]
        
        logger.info(f"Removed case {case_id} from monitoring")
        return True

    def check_updates(self, case_id: str) -> List[DocketUpdate]:
        """
        Check for docket updates on a specific case.
        
        Args:
            case_id: Case to check
            
        Returns:
            List of detected updates
        """
        if case_id not in self.monitored_cases:
            logger.error(f"Case {case_id} not being monitored")
            return []
        
        if not self.pacer_client:
            logger.error("PACER client not configured")
            return []
        
        monitored = self.monitored_cases[case_id]
        court = monitored.court
        
        try:
            # Get current docket
            current_docket = self.pacer_client.get_docket(case_id, court)
            
            # Compare with previous snapshot
            previous_docket = self.docket_snapshots.get(case_id, [])
            updates = self._detect_changes(case_id, previous_docket, current_docket)
            
            # Store snapshot and update metadata
            self.docket_snapshots[case_id] = current_docket
            monitored.last_checked = datetime.now()
            monitored.last_docket_hash = self._hash_docket(current_docket)
            monitored.new_entries_since_check = len(updates)
            
            # Store and process updates
            self.detected_updates[case_id] = updates
            
            # Extract deadlines from new entries
            for update in updates:
                self._extract_deadlines(update)
            
            # Trigger callbacks
            for callback in self.update_callbacks:
                for update in updates:
                    if update.significance_score >= monitored.alert_config.minimum_significance_score:
                        callback(update)
            
            logger.info(f"Detected {len(updates)} updates for case {case_id}")
            return updates
            
        except Exception as e:
            logger.error(f"Failed to check updates for case {case_id}: {e}")
            return []

    def check_all_cases(self) -> Dict[str, List[DocketUpdate]]:
        """Check all monitored cases for updates"""
        all_updates = {}
        for case_id in self.monitored_cases:
            updates = self.check_updates(case_id)
            if updates:
                all_updates[case_id] = updates
        return all_updates

    def score_significance(self, entry: Any) -> float:
        """
        Score the significance of a docket entry (1-10).
        
        Args:
            entry: DocketEntry object
            
        Returns:
            Significance score (0-10)
        """
        score = 1.0
        
        description = entry.description.lower()
        
        # Keywords and weights
        weights = {
            "judgment": 10,
            "final order": 10,
            "verdict": 10,
            "appeal": 9,
            "appeal filed": 9,
            "notice of appeal": 9,
            "emergency": 9,
            "temporary restraining": 9,
            "preliminary injunction": 9,
            "order to show cause": 8,
            "motion": 6,
            "hearing": 7,
            "scheduling": 5,
            "discovery": 4,
            "docket": 2,
            "administrative": 1,
        }
        
        for keyword, weight in weights.items():
            if keyword in description:
                score = max(score, float(weight))
        
        # Boost if major event detected
        if hasattr(entry, 'is_major_event') and entry.is_major_event():
            score = min(10.0, score * 1.5)
        
        # Reduce score for routine filings
        if any(word in description for word in ["affidavit", "certificate", "declaration"]):
            score = min(score, 3.0)
        
        return min(score, 10.0)

    def extract_deadlines(self, entries: List[Any]) -> List[Deadline]:
        """
        Extract deadlines from docket entries.
        
        Args:
            entries: List of docket entries
            
        Returns:
            List of extracted deadlines
        """
        deadlines = []
        
        # Deadline patterns and rules
        patterns = {
            "response": {
                "keywords": ["answer", "response", "reply"],
                "type": DeadlineType.RESPONSE_REQUIRED,
                "rule": "FRCP 12"
            },
            "hearing": {
                "keywords": ["hearing", "motion hearing", "trial date"],
                "type": DeadlineType.HEARING,
                "rule": None
            },
            "discovery": {
                "keywords": ["discovery", "interrogatory", "document production"],
                "type": DeadlineType.DISCOVERY,
                "rule": "FRCP 26-36"
            },
            "motion": {
                "keywords": ["motion", "reply to motion", "opposition"],
                "type": DeadlineType.MOTION,
                "rule": "FRCP 6"
            },
            "appeal": {
                "keywords": ["appeal", "appellate", "notice of appeal"],
                "type": DeadlineType.APPEAL,
                "rule": "FRAP 4"
            }
        }
        
        for entry in entries:
            desc_lower = entry.description.lower()
            
            for pattern_key, pattern_data in patterns.items():
                if any(kw in desc_lower for kw in pattern_data["keywords"]):
                    # Extract date if present in entry
                    deadline_date = self._extract_date_from_text(entry.description)
                    
                    if deadline_date:
                        deadline = Deadline(
                            deadline_id=f"dl_{hash(entry.entry_number)}",
                            case_id="",  # Will be set by caller
                            description=entry.description[:100],
                            due_date=deadline_date,
                            deadline_type=pattern_data["type"],
                            rule_reference=pattern_data["rule"],
                            raw_text=entry.description
                        )
                        deadline.update_status()
                        deadlines.append(deadline)
        
        return deadlines

    def get_upcoming_deadlines(
        self,
        case_id: str,
        days_ahead: int = 30
    ) -> List[Deadline]:
        """Get upcoming deadlines for a case"""
        if case_id not in self.monitored_cases:
            return []
        
        # Extract from recent entries
        current_docket = self.docket_snapshots.get(case_id, [])
        deadlines = self.extract_deadlines(current_docket)
        
        # Filter to upcoming deadlines
        today = date.today()
        upcoming = [
            d for d in deadlines
            if 0 <= (d.due_date - today).days <= days_ahead
        ]
        
        return sorted(upcoming, key=lambda x: x.due_date)

    def register_update_callback(
        self,
        callback: Callable[[DocketUpdate], None]
    ) -> None:
        """Register callback for docket updates"""
        self.update_callbacks.append(callback)
        logger.info("Registered update callback")

    def start_monitoring(self) -> None:
        """Start background monitoring loop"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Started docket monitoring")

    def stop_monitoring(self) -> None:
        """Stop background monitoring loop"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        logger.info("Stopped docket monitoring")

    def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self.check_all_cases()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def _take_docket_snapshot(self, case_id: str) -> None:
        """Take initial docket snapshot"""
        if not self.pacer_client:
            return
        
        try:
            monitored = self.monitored_cases[case_id]
            docket = self.pacer_client.get_docket(case_id, monitored.court)
            self.docket_snapshots[case_id] = docket
            monitored.last_docket_hash = self._hash_docket(docket)
        except Exception as e:
            logger.error(f"Failed to take initial snapshot for {case_id}: {e}")

    def _detect_changes(
        self,
        case_id: str,
        previous: List[Any],
        current: List[Any]
    ) -> List[DocketUpdate]:
        """Detect changes between two docket snapshots"""
        updates = []
        
        previous_ids = {e.entry_number for e in previous}
        current_ids = {e.entry_number for e in current}
        
        # Find new entries
        new_ids = current_ids - previous_ids
        for entry in current:
            if entry.entry_number in new_ids:
                significance = self.score_significance(entry)
                update = DocketUpdate(
                    case_id=case_id,
                    timestamp=datetime.now(),
                    entry=entry,
                    significance_score=significance,
                    update_type="NEW",
                    is_deadline=self._is_deadline_entry(entry)
                )
                updates.append(update)
        
        return updates

    def _extract_deadlines(self, update: DocketUpdate) -> None:
        """Extract deadlines from an update"""
        deadlines = self.extract_deadlines([update.entry])
        if deadlines:
            update.deadline = deadlines[0]
            update.is_deadline = True

    def _is_deadline_entry(self, entry: Any) -> bool:
        """Check if entry contains deadline information"""
        keywords = ["deadline", "due", "must", "shall", "respond", "days", "hours"]
        return any(kw in entry.description.lower() for kw in keywords)

    def _hash_docket(self, docket: List[Any]) -> str:
        """Create hash of docket for comparison"""
        entries_str = "|".join(str(e.entry_number) for e in docket)
        return hashlib.sha256(entries_str.encode()).hexdigest()

    def _extract_date_from_text(self, text: str) -> Optional[date]:
        """Extract date from text"""
        import re
        
        # Simple date patterns (could be enhanced)
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if "/" in pattern:
                        m, d, y = match.groups()
                        return date(int(y), int(m), int(d))
                    else:
                        y, m, d = match.groups()
                        return date(int(y), int(m), int(d))
                except ValueError:
                    continue
        
        return None

    def get_monitored_case(self, case_id: str) -> Optional[MonitoredCase]:
        """Get monitored case by ID"""
        return self.monitored_cases.get(case_id)

    def list_monitored_cases(self) -> List[MonitoredCase]:
        """List all monitored cases"""
        return list(self.monitored_cases.values())

    def get_case_updates(self, case_id: str) -> List[DocketUpdate]:
        """Get detected updates for a case"""
        return self.detected_updates.get(case_id, [])
