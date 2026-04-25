"""
Supreme Court of the United States (SCOTUS) Monitoring

Cert petitions, oral arguments, opinions, circuit splits, and justice
voting pattern analysis.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CertStatus(Enum):
    """Status of cert petition"""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    DISMISSED = "dismissed"
    RELISTED = "relisted"


class OpinionType(Enum):
    """Supreme Court opinion types"""
    MAJORITY = "majority"
    CONCURRENCE = "concurrence"
    DISSENT = "dissent"
    PER_CURIAM = "per_curiam"


@dataclass
class CertPetition:
    """Cert petition to Supreme Court"""
    petition_id: str
    case_name: str
    petitioner: str
    respondent: str
    filed_date: date
    lower_court: str
    question_presented: str
    cert_status: CertStatus = CertStatus.PENDING
    granted_date: Optional[date] = None
    denied_date: Optional[date] = None
    circuit_court: Optional[str] = None
    topic: Optional[str] = None
    importance_score: float = 0.0
    related_petitions: List[str] = field(default_factory=list)


@dataclass
class OralArgument:
    """Supreme Court oral argument"""
    argument_id: str
    case_name: str
    case_number: str
    scheduled_date: date
    scheduled_time: str
    estimated_duration_minutes: int = 60
    petitioner_counsel: str = ""
    respondent_counsel: str = ""
    argument_transcript_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    justices_present: List[str] = field(default_factory=list)


@dataclass
class SCOTUSOpinion:
    """Supreme Court opinion"""
    opinion_id: str
    case_name: str
    citation: str
    decision_date: date
    judgment: str  # Affirmed, Reversed, Vacated, etc.
    vote_split: str  # e.g., "6-3" or "9-0"
    majority_author: str
    concurring_justices: List[str] = field(default_factory=list)
    dissenting_justices: List[str] = field(default_factory=list)
    text_url: Optional[str] = None
    importance_score: float = 0.0
    affects_circuit_splits: bool = False


@dataclass
class CircuitSplit:
    """Circuit split in legal interpretation"""
    split_id: str
    legal_issue: str
    question: str
    circuits_agreeing_a: List[str] = field(default_factory=list)
    circuits_agreeing_b: List[str] = field(default_factory=list)
    neutral_circuits: List[str] = field(default_factory=list)
    lead_cases_a: List[str] = field(default_factory=list)
    lead_cases_b: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)
    status: str = "open"  # open, pending_scotus, resolved
    petitions_filed: int = 0


@dataclass
class JusticeVotingPattern:
    """Justice voting statistics"""
    justice_name: str
    court_term: str
    cases_decided: int = 0
    majority_opinions: int = 0
    concurring_opinions: int = 0
    dissenting_opinions: int = 0
    avg_agreement_with_chief: float = 0.0
    liberal_tendency_score: float = 0.5  # 0-1, 0.5 = neutral
    dissent_rate: float = 0.0
    reversal_rate: float = 0.0


class SCOTUSTracker:
    """
    Supreme Court monitoring system.
    
    Tracks cert petitions, oral arguments, opinions, circuit splits,
    and justice voting patterns.
    """

    SCOTUS_API = "https://api.supremecourt.gov"
    SCOTUSBLOG_API = "https://www.scotusblog.com/api"

    def __init__(self):
        """Initialize SCOTUS tracker"""
        self.pending_petitions: Dict[str, CertPetition] = {}
        self.granted_petitions: Dict[str, CertPetition] = {}
        self.oral_arguments: Dict[str, OralArgument] = {}
        self.recent_opinions: Dict[str, SCOTUSOpinion] = {}
        self.circuit_splits: Dict[str, CircuitSplit] = {}
        self.justice_voting_patterns: Dict[str, JusticeVotingPattern] = {}

    def get_pending_cert(
        self,
        topic: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 100
    ) -> List[CertPetition]:
        """
        Get pending cert petitions.
        
        Args:
            topic: Optional topic filter (e.g., "First Amendment", "Civil Rights")
            jurisdiction: Optional lower court jurisdiction
            limit: Maximum results
            
        Returns:
            List of pending petitions
        """
        petitions = list(self.pending_petitions.values())
        
        if topic:
            petitions = [
                p for p in petitions
                if p.topic and topic.lower() in p.topic.lower()
            ]
        
        if jurisdiction:
            petitions = [
                p for p in petitions
                if p.circuit_court and jurisdiction in p.circuit_court
            ]
        
        # Sort by filing date descending
        petitions = sorted(petitions, key=lambda x: x.filed_date, reverse=True)
        
        logger.info(f"Retrieved {len(petitions[:limit])} pending cert petitions")
        return petitions[:limit]

    def get_granted_petitions(
        self,
        limit: int = 50
    ) -> List[CertPetition]:
        """Get recently granted cert petitions"""
        petitions = sorted(
            self.granted_petitions.values(),
            key=lambda x: x.granted_date or date.today(),
            reverse=True
        )
        
        logger.info(f"Retrieved {len(petitions[:limit])} granted petitions")
        return petitions[:limit]

    def get_oral_argument_schedule(
        self,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> List[OralArgument]:
        """
        Get oral argument schedule.
        
        Args:
            month: Optional month filter (1-12)
            year: Optional year filter
            
        Returns:
            List of scheduled arguments
        """
        arguments = list(self.oral_arguments.values())
        
        if month:
            arguments = [a for a in arguments if a.scheduled_date.month == month]
        
        if year:
            arguments = [a for a in arguments if a.scheduled_date.year == year]
        
        arguments = sorted(arguments, key=lambda x: x.scheduled_date)
        
        logger.info(f"Retrieved {len(arguments)} oral arguments")
        return arguments

    def get_recent_opinions(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[SCOTUSOpinion]:
        """
        Get recent Supreme Court opinions.
        
        Args:
            days: Number of days back
            limit: Maximum results
            
        Returns:
            List of recent opinions
        """
        from datetime import timedelta
        
        cutoff = date.today() - timedelta(days=days)
        opinions = [
            o for o in self.recent_opinions.values()
            if o.decision_date >= cutoff
        ]
        
        opinions = sorted(opinions, key=lambda x: x.decision_date, reverse=True)
        
        logger.info(f"Retrieved {len(opinions[:limit])} recent opinions")
        return opinions[:limit]

    def find_circuit_splits(
        self,
        topic: Optional[str] = None,
        status: str = "open"
    ) -> List[CircuitSplit]:
        """
        Find circuit splits on a topic.
        
        Args:
            topic: Optional topic filter
            status: Filter by status (open, pending_scotus, resolved)
            
        Returns:
            List of circuit splits
        """
        splits = list(self.circuit_splits.values())
        
        if topic:
            splits = [
                s for s in splits
                if topic.lower() in s.legal_issue.lower()
            ]
        
        splits = [s for s in splits if s.status == status]
        
        logger.info(f"Found {len(splits)} circuit splits on {topic or 'all topics'}")
        return splits

    def analyze_voting_patterns(
        self,
        justice_name: str,
        court_term: str
    ) -> Optional[JusticeVotingPattern]:
        """
        Get voting pattern analysis for justice.
        
        Args:
            justice_name: Justice name
            court_term: Court term (e.g., "2023-2024")
            
        Returns:
            Voting pattern data
        """
        key = f"{justice_name}_{court_term}"
        
        if key not in self.justice_voting_patterns:
            # Generate from opinion data
            pattern = self._calculate_voting_pattern(justice_name, court_term)
            self.justice_voting_patterns[key] = pattern
            return pattern
        
        return self.justice_voting_patterns[key]

    def track_petition(
        self,
        case_name: str,
        petitioner: str,
        respondent: str,
        filed_date: date,
        lower_court: str,
        question_presented: str,
        topic: Optional[str] = None
    ) -> CertPetition:
        """
        Track a new cert petition.
        
        Args:
            case_name: Case name
            petitioner: Petitioner name
            respondent: Respondent name
            filed_date: Filing date
            lower_court: Lower court that decided case
            question_presented: Legal question
            topic: Optional topic classification
            
        Returns:
            Cert petition object
        """
        petition_id = f"pet_{hash((case_name, filed_date))}"
        
        petition = CertPetition(
            petition_id=petition_id,
            case_name=case_name,
            petitioner=petitioner,
            respondent=respondent,
            filed_date=filed_date,
            lower_court=lower_court,
            question_presented=question_presented,
            topic=topic
        )
        
        self.pending_petitions[petition_id] = petition
        logger.info(f"Tracking cert petition: {case_name}")
        
        return petition

    def grant_petition(self, petition_id: str) -> bool:
        """Mark petition as granted"""
        if petition_id not in self.pending_petitions:
            return False
        
        petition = self.pending_petitions.pop(petition_id)
        petition.cert_status = CertStatus.GRANTED
        petition.granted_date = date.today()
        
        self.granted_petitions[petition_id] = petition
        logger.info(f"Granted petition: {petition.case_name}")
        
        return True

    def deny_petition(self, petition_id: str) -> bool:
        """Mark petition as denied"""
        if petition_id not in self.pending_petitions:
            return False
        
        petition = self.pending_petitions.pop(petition_id)
        petition.cert_status = CertStatus.DENIED
        petition.denied_date = date.today()
        
        logger.info(f"Denied petition: {petition.case_name}")
        return True

    def add_opinion(self, opinion: SCOTUSOpinion) -> None:
        """Add decided opinion"""
        self.recent_opinions[opinion.opinion_id] = opinion
        logger.info(f"Added opinion: {opinion.case_name}")

    def schedule_oral_argument(self, argument: OralArgument) -> None:
        """Schedule oral argument"""
        self.oral_arguments[argument.argument_id] = argument
        logger.info(f"Scheduled oral argument: {argument.case_name}")

    def get_petition_status(self, petition_id: str) -> Optional[str]:
        """Get current status of petition"""
        if petition_id in self.pending_petitions:
            return self.pending_petitions[petition_id].cert_status.value
        elif petition_id in self.granted_petitions:
            return self.granted_petitions[petition_id].cert_status.value
        return None

    def get_case_importance_score(self, case_name: str) -> float:
        """
        Estimate importance of case to legal practice.
        Score based on topic, circuits affected, etc.
        """
        # Find related split
        splits = [s for s in self.circuit_splits.values() if case_name in s.lead_cases_a or case_name in s.lead_cases_b]
        
        if not splits:
            return 0.5  # Neutral importance
        
        split = splits[0]
        # More circuits affected = more important
        circuits_affected = len(set(
            split.circuits_agreeing_a + split.circuits_agreeing_b
        ))
        
        return min(10.0, circuits_affected)

    def _calculate_voting_pattern(
        self,
        justice_name: str,
        court_term: str
    ) -> JusticeVotingPattern:
        """Calculate voting pattern from opinions"""
        pattern = JusticeVotingPattern(
            justice_name=justice_name,
            court_term=court_term
        )
        
        # Analyze opinions to build pattern
        for opinion in self.recent_opinions.values():
            if justice_name in opinion.majority_author:
                pattern.majority_opinions += 1
            if justice_name in opinion.concurring_justices:
                pattern.concurring_opinions += 1
            if justice_name in opinion.dissenting_justices:
                pattern.dissenting_opinions += 1
        
        pattern.cases_decided = (
            pattern.majority_opinions +
            pattern.concurring_opinions +
            pattern.dissenting_opinions
        )
        
        if pattern.cases_decided > 0:
            pattern.dissent_rate = (
                pattern.dissenting_opinions / pattern.cases_decided
            )
        
        return pattern

    def get_petition_related(self, petition_id: str) -> List[CertPetition]:
        """Get related petitions (same circuit, topic, etc)"""
        target = self.pending_petitions.get(petition_id) or self.granted_petitions.get(petition_id)
        if not target:
            return []
        
        related = []
        
        all_petitions = list(self.pending_petitions.values()) + list(self.granted_petitions.values())
        
        for petition in all_petitions:
            if petition.petition_id == petition_id:
                continue
            
            # Same topic
            if target.topic and petition.topic and target.topic.lower() == petition.topic.lower():
                related.append(petition)
            
            # Same circuit
            if target.circuit_court and petition.circuit_court and target.circuit_court == petition.circuit_court:
                related.append(petition)
        
        return list(set(related))

    def get_statistics(self) -> Dict[str, Any]:
        """Get SCOTUS statistics"""
        return {
            "pending_petitions": len(self.pending_petitions),
            "granted_this_term": len([
                p for p in self.granted_petitions.values()
                if p.granted_date and p.granted_date.year == date.today().year
            ]),
            "circuit_splits": len(self.circuit_splits),
            "total_opinions": len(self.recent_opinions),
            "scheduled_arguments": len(self.oral_arguments),
        }
