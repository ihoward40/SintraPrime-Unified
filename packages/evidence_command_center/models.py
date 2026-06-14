"""Evidence Command Center - Core Data Models

Pure Python models for evidence, violations, exhibits, and chain of custody.
No database dependencies - prototype validation only.

Status: MVP (design validation)
Created: 2026-06-14
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib
import json
import uuid


class Statute(str, Enum):
    """Federal and state consumer protection statutes."""
    FCRA = "FCRA"
    FDCPA = "FDCPA"
    TCPA = "TCPA"
    RESPA = "RESPA"
    TILA = "TILA"
    ECOA = "ECOA"
    UCC = "UCC"
    STATE_CONSUMER = "STATE_CONSUMER"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class Severity(str, Enum):
    """Violation severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceStatus(str, Enum):
    """Evidence lifecycle status."""
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    TAGGED = "tagged"
    LINKED = "linked"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ViolationStatus(str, Enum):
    """Violation lifecycle status."""
    DETECTED = "DETECTED"
    ANALYZED = "ANALYZED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    LINKED = "LINKED"
    APPROVED = "APPROVED"
    FILED = "FILED"
    RESOLVED = "RESOLVED"


class EvidenceStrength(str, Enum):
    """How well evidence supports a violation."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    CIRCUMSTANTIAL = "CIRCUMSTANTIAL"


@dataclass
class ChainEntry:
    """Single entry in chain of custody."""
    __test__ = False  # Prevent pytest from collecting as test
    
    timestamp: str
    actor: str
    actor_role: str
    action: str
    details: Dict[str, Any]
    prev_hash: str = ""
    entry_hash: str = ""
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry."""
        content = json.dumps({
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "details": self.details,
            "prev_hash": self.prev_hash
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def __post_init__(self):
        """Auto-compute hash if not provided."""
        if not self.entry_hash:
            self.entry_hash = self.compute_hash()


@dataclass
class Evidence:
    """Evidence item with metadata and chain of custody."""
    __test__ = False  # Prevent pytest from collecting as test
    
    # Identity
    evidence_id: str
    case_id: str
    client_id: Optional[str] = None
    
    # Source
    source_type: str = "upload"
    source_reference: Optional[str] = None
    date_acquired: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acquired_by: Optional[str] = None
    
    # File info
    file_name: str = ""
    file_size_bytes: int = 0
    mime_type: str = "application/pdf"
    storage_key: str = ""
    
    # Hash & integrity
    sha256_hash: str = ""
    integrity_verified: bool = False
    last_verified_at: Optional[str] = None
    
    # Classification
    category: str = "other"
    subcategory: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Status
    status: EvidenceStatus = EvidenceStatus.PENDING_REVIEW
    review_status: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    
    # Violation linkage
    linked_violations: List[str] = field(default_factory=list)
    violation_confidence: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Chain of custody
    chain_of_custody: List[ChainEntry] = field(default_factory=list)
    
    # Audit
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""
    
    def append_to_chain(self, actor: str, actor_role: str, action: str, details: Dict[str, Any]) -> ChainEntry:
        """Append action to chain of custody."""
        prev_hash = self.chain_of_custody[-1].entry_hash if self.chain_of_custody else ""
        
        entry = ChainEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            actor_role=actor_role,
            action=action,
            details=details,
            prev_hash=prev_hash
        )
        
        self.chain_of_custody.append(entry)
        return entry
    
    def verify_chain(self) -> tuple[bool, Optional[int], Optional[str]]:
        """Verify integrity of chain of custody."""
        prev_hash = ""
        
        for index, entry in enumerate(self.chain_of_custody):
            # Verify previous hash matches
            if entry.prev_hash != prev_hash:
                return (False, index, f"Chain broken at entry {index}: prev_hash mismatch")
            
            # Recompute and verify hash
            expected_hash = entry.compute_hash()
            if entry.entry_hash != expected_hash:
                return (False, index, f"Entry {index} tampered: hash mismatch")
            
            prev_hash = entry.entry_hash
        
        return (True, None, "Chain of custody intact")


@dataclass
class Violation:
    """Legal violation with statute references and evidence links."""
    __test__ = False  # Prevent pytest from collecting as test
    
    # Identity
    violation_id: str
    case_id: str
    client_id: str
    
    # Statute
    statute: Statute
    statute_full_name: str
    statute_citation: str
    subsection: Optional[str] = None
    
    # Violation details
    violation_type: str = ""
    violation_description: str = ""
    violation_date: Optional[str] = None
    severity: Severity = Severity.MEDIUM
    
    # Evidence linkage
    linked_evidence: List[str] = field(default_factory=list)
    primary_evidence_id: Optional[str] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    
    # AI analysis
    ai_detected: bool = False
    ai_confidence: Optional[float] = None
    ai_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Human review
    human_reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    attorney_confidence: Optional[str] = None
    review_notes: Optional[str] = None
    
    # Status
    status: ViolationStatus = ViolationStatus.DETECTED
    rejection_reason: Optional[str] = None
    
    # Remedies
    statutory_damages_min: Optional[float] = None
    statutory_damages_max: Optional[float] = None
    actual_damages: Optional[float] = None
    punitive_damages_eligible: bool = False
    injunctive_relief: bool = False
    attorneys_fees_eligible: bool = False
    remedy_notes: Optional[str] = None
    
    # Strategy
    settlement_value: Optional[float] = None
    litigation_strategy: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audit
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""


@dataclass
class Exhibit:
    """Court-ready exhibit with numbering and formatting."""
    __test__ = False  # Prevent pytest from collecting as test
    
    # Identity
    exhibit_id: str
    case_id: str
    evidence_id: str
    
    # Designation
    exhibit_number: str
    exhibit_label_format: str = "LETTER"  # LETTER, NUMBER, PREFIX_LETTER, etc.
    sequence_number: int = 1
    exhibit_prefix: Optional[str] = None
    
    # Description
    exhibit_title: str = ""
    exhibit_description: str = ""
    purpose: Optional[str] = None
    relevance_to_violation: Optional[str] = None
    
    # File info
    page_count: int = 0
    page_range: Optional[str] = None
    file_format: str = "PDF"
    storage_key: str = ""
    original_storage_key: str = ""
    
    # Bates numbering
    bates_numbering: bool = False
    bates_prefix: Optional[str] = None
    bates_start: Optional[int] = None
    bates_end: Optional[int] = None
    bates_format: Optional[str] = None
    
    # Packet association
    packet_ids: List[str] = field(default_factory=list)
    primary_packet_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = "CREATED"
    filed_date: Optional[str] = None
    filed_with: Optional[str] = None
    
    # Audit
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""


def generate_letter_label(sequence: int) -> str:
    """Generate letter-based exhibit label (A, B, ..., Z, AA, AB, ...)."""
    result = ""
    while sequence > 0:
        sequence -= 1
        result = chr(65 + (sequence % 26)) + result
        sequence //= 26
    return result


def generate_exhibit_number(
    sequence: int,
    label_format: str = "LETTER",
    prefix: Optional[str] = None
) -> str:
    """Generate exhibit number based on format."""
    if label_format == "LETTER":
        label = generate_letter_label(sequence)
    elif label_format == "NUMBER":
        label = str(sequence)
    elif label_format == "PREFIX_LETTER":
        label = f"{prefix}-{generate_letter_label(sequence)}"
    elif label_format == "PREFIX_NUMBER":
        label = f"{prefix}-{sequence:03d}"
    else:
        label = str(sequence)
    
    return label


# Utility functions
def create_evidence_id(case_id: str, year: int, sequence: int) -> str:
    """Generate evidence ID: EV-{year}-{sequence:05d}"""
    return f"EV-{year}-{sequence:05d}"


def create_violation_id(statute: Statute, year: int, sequence: int) -> str:
    """Generate violation ID: VIO-{statute}-{year}-{sequence:05d}"""
    return f"VIO-{statute.value}-{year}-{sequence:05d}"


def create_exhibit_id(case_id: str, year: int, sequence: int) -> str:
    """Generate exhibit ID: EX-{case}-{year}-{sequence:05d}"""
    case_short = case_id[:4] if len(case_id) >= 4 else case_id
    return f"EX-{case_short}-{year}-{sequence:05d}"
