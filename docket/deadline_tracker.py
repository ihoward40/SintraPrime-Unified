"""
Comprehensive Legal Deadline Management System

Federal Rules deadline calculation, statute of limitations, malpractice risk
assessment, and deadline chain tracking.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class DeadlineRule(Enum):
    """Common deadline rules"""
    ANSWER_FRCP12 = ("FRCP 12", 21)  # 21 days to answer
    REPLY_MOTION = ("FRCP 6", 14)  # 14 days to reply
    DISCOVERY_INTERROGATORY = ("FRCP 33", 30)  # 30 days
    MOTION_HEARING = ("FRCP 6", 14)
    NOTICE_APPEAL_CIVIL = ("FRAP 4", 30)  # 30 days civil
    NOTICE_APPEAL_CRIMINAL = ("FRAP 4", 14)  # 14 days criminal
    BRIEF_APPELLANT = ("FRAP 31", 40)
    BRIEF_APPELLEE = ("FRAP 31", 40)


class RiskLevel(Enum):
    """Malpractice risk levels"""
    SAFE = "safe"  # > 14 days
    CAUTION = "caution"  # 7-14 days
    WARNING = "warning"  # 3-7 days
    CRITICAL = "critical"  # < 3 days


@dataclass
class Deadline:
    """Legal deadline"""
    deadline_id: str
    case_id: str
    description: str
    due_date: date
    rule_reference: str
    days_from_event: int
    trigger_event: str
    excludes_weekends: bool = True
    excludes_holidays: bool = True
    jurisdiction: str = "federal"
    days_until_due: Optional[int] = None
    is_upcoming: bool = False
    is_overdue: bool = False

    def calculate_days_remaining(self) -> int:
        """Calculate days until deadline"""
        today = date.today()
        self.days_until_due = (self.due_date - today).days
        self.is_upcoming = 0 <= self.days_until_due <= 30
        self.is_overdue = self.days_until_due < 0
        return self.days_until_due


@dataclass
class RiskReport:
    """Malpractice risk assessment"""
    case_id: str
    report_date: datetime = field(default_factory=datetime.now)
    overall_risk: RiskLevel = RiskLevel.SAFE
    upcoming_deadlines: List[Deadline] = field(default_factory=list)
    critical_deadlines: List[Deadline] = field(default_factory=list)
    statute_of_limitations: Optional[date] = None
    sol_risk_level: RiskLevel = RiskLevel.SAFE
    missed_deadlines: List[Deadline] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class DeadlineChain:
    """Related deadlines triggered by single event"""
    trigger_event: str
    trigger_date: date
    deadlines: List[Deadline] = field(default_factory=list)


class FederalCourtHolidays:
    """Federal court holidays"""
    
    # Holidays observed by federal courts
    HOLIDAYS = {
        (1, 1): "New Year's Day",
        (1, 15): "MLK Jr. Birthday",  # 3rd Monday
        (2, 19): "Presidents Day",  # 3rd Monday
        (5, 26): "Memorial Day",  # Last Monday
        (7, 4): "Independence Day",
        (9, 2): "Labor Day",  # 1st Monday
        (10, 14): "Columbus Day",  # 2nd Monday
        (11, 11): "Veterans Day",
        (11, 28): "Thanksgiving",  # 4th Thursday
        (12, 25): "Christmas",
    }
    
    @staticmethod
    def is_holiday(d: date) -> bool:
        """Check if date is federal holiday"""
        return (d.month, d.day) in FederalCourtHolidays.HOLIDAYS


class DeadlineCalculator:
    """Calculate legal deadlines following Federal Rules"""
    
    @staticmethod
    def is_court_day(d: date) -> bool:
        """Check if date is a court business day"""
        # Exclude weekends (5=Saturday, 6=Sunday)
        if d.weekday() >= 5:
            return False
        
        # Exclude federal holidays
        if FederalCourtHolidays.is_holiday(d):
            return False
        
        return True
    
    @staticmethod
    def add_days_excluding_weekends(start_date: date, days: int) -> date:
        """Add days, excluding weekends"""
        current = start_date
        remaining = days
        
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday-Friday
                remaining -= 1
        
        return current
    
    @staticmethod
    def add_days_excluding_holidays(start_date: date, days: int, jurisdiction: str = "federal") -> date:
        """Add days, excluding weekends and holidays"""
        current = start_date
        remaining = days
        
        while remaining > 0:
            current += timedelta(days=1)
            if DeadlineCalculator.is_court_day(current):
                remaining -= 1
        
        return current
    
    @staticmethod
    def calculate_deadline(
        event_date: date,
        days_offset: int,
        rule_name: str = "",
        exclude_weekends: bool = True,
        exclude_holidays: bool = True,
        jurisdiction: str = "federal"
    ) -> date:
        """
        Calculate deadline date from trigger event.
        
        Args:
            event_date: Date that triggers deadline
            days_offset: Number of days for deadline
            rule_name: FRCP/FRAP rule name
            exclude_weekends: Whether to exclude weekends
            exclude_holidays: Whether to exclude holidays
            jurisdiction: Court jurisdiction
            
        Returns:
            Deadline date
        """
        if exclude_holidays:
            return DeadlineCalculator.add_days_excluding_holidays(
                event_date, days_offset, jurisdiction
            )
        elif exclude_weekends:
            return DeadlineCalculator.add_days_excluding_weekends(
                event_date, days_offset
            )
        else:
            return event_date + timedelta(days=days_offset)


class StatuteOfLimitations:
    """Statute of limitations calculator"""
    
    # SOL by cause of action and state (in years)
    SOL_BY_STATE = {
        "contract": {
            "default": 4,
            "oral": 3,
            "written": 6,
        },
        "tort": {
            "default": 2,
            "personal_injury": 3,
            "negligence": 3,
        },
        "property": {
            "default": 3,
            "real_estate": 10,
            "personal": 3,
        },
        "fraud": {
            "default": 4,
        },
        "defamation": {
            "default": 1,
        }
    }

    @staticmethod
    def get_statute_of_limitations(
        cause_of_action: str,
        state: str,
        incident_date: date
    ) -> Tuple[date, int]:
        """
        Calculate statute of limitations.
        
        Args:
            cause_of_action: Type of claim
            state: State jurisdiction
            incident_date: Date of incident
            
        Returns:
            Tuple of (deadline date, years remaining)
        """
        # Normalize cause of action
        cause_lower = cause_of_action.lower()
        
        # Get SOL years from table
        sol_years = StatuteOfLimitations.SOL_BY_STATE.get(
            cause_lower,
            StatuteOfLimitations.SOL_BY_STATE.get("default", 3)
        )
        
        if isinstance(sol_years, dict):
            sol_years = sol_years.get(
                cause_lower.split("_")[-1],
                sol_years.get("default", 3)
            )
        
        deadline = incident_date + timedelta(days=sol_years * 365)
        years_remaining = (deadline - date.today()).days // 365
        
        return deadline, years_remaining


class DeadlineTracker:
    """
    Comprehensive deadline management system.
    
    Tracks deadlines, calculates dates, assesses risk, and monitors
    statute of limitations.
    """

    def __init__(self):
        """Initialize deadline tracker"""
        self.tracked_deadlines: Dict[str, List[Deadline]] = {}
        self.deadline_chains: Dict[str, DeadlineChain] = {}
        self.risk_reports: Dict[str, RiskReport] = {}

    def calculate_deadline(
        self,
        event_date: date,
        rule: Union[DeadlineRule, str],
        court: str = "federal"
    ) -> date:
        """
        Calculate deadline from rule.
        
        Args:
            event_date: Triggering event date
            rule: Deadline rule
            court: Court jurisdiction
            
        Returns:
            Deadline date
        """
        if isinstance(rule, DeadlineRule):
            rule_name, days = rule.value
        else:
            # Parse rule string like "FRCP 12" -> (12, 21)
            days = self._parse_rule_days(rule)
            rule_name = rule
        
        return DeadlineCalculator.calculate_deadline(
            event_date, days, rule_name, jurisdiction=court
        )

    def get_statute_of_limitations(
        self,
        cause_of_action: str,
        state: str,
        incident_date: date
    ) -> date:
        """Get statute of limitations deadline"""
        deadline, _ = StatuteOfLimitations.get_statute_of_limitations(
            cause_of_action, state, incident_date
        )
        return deadline

    def add_deadline(
        self,
        case_id: str,
        description: str,
        due_date: date,
        rule_reference: str,
        days_from_event: int = 0,
        trigger_event: str = ""
    ) -> Deadline:
        """Add deadline for tracking"""
        deadline = Deadline(
            deadline_id=f"dl_{hash((case_id, due_date))}",
            case_id=case_id,
            description=description,
            due_date=due_date,
            rule_reference=rule_reference,
            days_from_event=days_from_event,
            trigger_event=trigger_event
        )
        
        if case_id not in self.tracked_deadlines:
            self.tracked_deadlines[case_id] = []
        
        self.tracked_deadlines[case_id].append(deadline)
        deadline.calculate_days_remaining()
        
        return deadline

    def get_upcoming_deadlines(
        self,
        case_id: str,
        days_ahead: int = 30
    ) -> List[Deadline]:
        """Get upcoming deadlines for case"""
        if case_id not in self.tracked_deadlines:
            return []
        
        today = date.today()
        upcoming = []
        
        for deadline in self.tracked_deadlines[case_id]:
            days_left = (deadline.due_date - today).days
            if 0 <= days_left <= days_ahead:
                upcoming.append(deadline)
        
        return sorted(upcoming, key=lambda x: x.due_date)

    def assess_malpractice_risk(self, case_id: str) -> RiskReport:
        """
        Assess malpractice risk for case.
        
        Args:
            case_id: Case identifier
            
        Returns:
            Risk assessment report
        """
        report = RiskReport(case_id=case_id)
        
        if case_id not in self.tracked_deadlines:
            return report
        
        today = date.today()
        critical = []
        upcoming = []
        missed = []
        
        for deadline in self.tracked_deadlines[case_id]:
            days_left = (deadline.due_date - today).days
            
            if days_left < 0:
                missed.append(deadline)
            elif days_left <= 3:
                critical.append(deadline)
            elif days_left <= 30:
                upcoming.append(deadline)
        
        # Determine overall risk
        if missed:
            report.overall_risk = RiskLevel.CRITICAL
            report.recommendations.append(f"URGENT: {len(missed)} missed deadlines")
        elif critical:
            report.overall_risk = RiskLevel.CRITICAL
            report.recommendations.append(f"URGENT: {len(critical)} deadlines in < 3 days")
        elif upcoming:
            report.overall_risk = RiskLevel.WARNING
            report.recommendations.append(f"Review {len(upcoming)} upcoming deadlines")
        else:
            report.overall_risk = RiskLevel.SAFE
        
        report.upcoming_deadlines = upcoming
        report.critical_deadlines = critical
        report.missed_deadlines = missed
        
        self.risk_reports[case_id] = report
        return report

    def get_deadline_chains(self, trigger_event: str) -> List[DeadlineChain]:
        """Get related deadlines triggered by event"""
        # Map trigger events to deadline chains
        chains_map = {
            "complaint_filed": [
                DeadlineRule.ANSWER_FRCP12,
                DeadlineRule.DISCOVERY_INTERROGATORY,
                DeadlineRule.MOTION_HEARING,
            ],
            "judgment_entered": [
                DeadlineRule.NOTICE_APPEAL_CIVIL,
                DeadlineRule.BRIEF_APPELLANT,
                DeadlineRule.BRIEF_APPELLEE,
            ],
            "motion_filed": [
                DeadlineRule.REPLY_MOTION,
                DeadlineRule.MOTION_HEARING,
            ]
        }
        
        chains = []
        
        if trigger_event in chains_map:
            for rule in chains_map[trigger_event]:
                chain = DeadlineChain(
                    trigger_event=trigger_event,
                    trigger_date=date.today()
                )
                chains.append(chain)
        
        return chains

    def validate_deadline_compliance(
        self,
        case_id: str
    ) -> Dict[str, Any]:
        """Check deadline compliance for case"""
        if case_id not in self.tracked_deadlines:
            return {"compliant": True, "issues": []}
        
        today = date.today()
        issues = []
        
        for deadline in self.tracked_deadlines[case_id]:
            days_left = (deadline.due_date - today).days
            if days_left < 0:
                issues.append({
                    "deadline": deadline.description,
                    "missed_by": abs(days_left),
                    "severity": "critical"
                })
            elif days_left <= 3:
                issues.append({
                    "deadline": deadline.description,
                    "days_remaining": days_left,
                    "severity": "urgent"
                })
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "compliance_percentage": 100 if not issues else 50
        }

    def _parse_rule_days(self, rule: str) -> int:
        """Parse days from rule reference"""
        rule_days = {
            "FRCP 12": 21,  # Answer
            "FRCP 6": 14,   # Motion reply
            "FRCP 26": 30,  # Interrogatory
            "FRAP 4": 30,   # Appeal civil
            "FRAP 31": 40,  # Brief
        }
        return rule_days.get(rule.upper(), 14)

    def reminder_status(self, days_from_deadline: int) -> str:
        """Get reminder status based on days remaining"""
        if days_from_deadline < 0:
            return "OVERDUE"
        elif days_from_deadline == 0:
            return "DUE TODAY"
        elif days_from_deadline == 1:
            return "DUE TOMORROW"
        elif days_from_deadline <= 3:
            return "CRITICAL"
        elif days_from_deadline <= 7:
            return "URGENT"
        elif days_from_deadline <= 14:
            return "WARNING"
        else:
            return "NORMAL"


# Type hint
from typing import Union
