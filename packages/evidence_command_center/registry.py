"""Evidence Command Center - Registry Management

In-memory registries for evidence, violations, and exhibits.
No database dependencies - prototype validation only.

Status: MVP (design validation)
Created: 2026-06-14
"""

from typing import List, Optional, Dict
from .models import (
    Evidence, Violation, Exhibit,
    EvidenceStatus, ViolationStatus,
    create_evidence_id, create_violation_id, create_exhibit_id
)
from datetime import datetime


class EvidenceRegistry:
    """In-memory evidence catalog."""
    
    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}
        self._by_case: Dict[str, List[str]] = {}
        self._by_hash: Dict[str, str] = {}
        self._sequence = 0
    
    def add(self, evidence: Evidence) -> Evidence:
        """Add evidence to registry."""
        # Check for duplicate hash
        if evidence.sha256_hash and evidence.sha256_hash in self._by_hash:
            existing_id = self._by_hash[evidence.sha256_hash]
            raise ValueError(
                f"Evidence with hash {evidence.sha256_hash} already exists: {existing_id}"
            )
        
        self._evidence[evidence.evidence_id] = evidence
        
        # Index by case
        if evidence.case_id not in self._by_case:
            self._by_case[evidence.case_id] = []
        self._by_case[evidence.case_id].append(evidence.evidence_id)
        
        # Index by hash
        if evidence.sha256_hash:
            self._by_hash[evidence.sha256_hash] = evidence.evidence_id
        
        return evidence
    
    def get(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        return self._evidence.get(evidence_id)
    
    def get_by_case(self, case_id: str) -> List[Evidence]:
        """Get all evidence for a case."""
        evidence_ids = self._by_case.get(case_id, [])
        return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]
    
    def get_by_hash(self, sha256_hash: str) -> Optional[Evidence]:
        """Get evidence by SHA-256 hash."""
        evidence_id = self._by_hash.get(sha256_hash)
        return self._evidence.get(evidence_id) if evidence_id else None
    
    def get_approved(self, case_id: str) -> List[Evidence]:
        """Get approved evidence for a case."""
        return [
            ev for ev in self.get_by_case(case_id)
            if ev.status == EvidenceStatus.APPROVED
        ]
    
    def generate_id(self, case_id: str) -> str:
        """Generate new evidence ID."""
        self._sequence += 1
        year = datetime.now().year
        return create_evidence_id(case_id, year, self._sequence)


class ViolationRegistry:
    """In-memory violation catalog."""
    
    def __init__(self):
        self._violations: Dict[str, Violation] = {}
        self._by_case: Dict[str, List[str]] = {}
        self._sequence = 0
    
    def add(self, violation: Violation) -> Violation:
        """Add violation to registry."""
        self._violations[violation.violation_id] = violation
        
        # Index by case
        if violation.case_id not in self._by_case:
            self._by_case[violation.case_id] = []
        self._by_case[violation.case_id].append(violation.violation_id)
        
        return violation
    
    def get(self, violation_id: str) -> Optional[Violation]:
        """Get violation by ID."""
        return self._violations.get(violation_id)
    
    def get_by_case(self, case_id: str) -> List[Violation]:
        """Get all violations for a case."""
        violation_ids = self._by_case.get(case_id, [])
        return [self._violations[vid] for vid in violation_ids if vid in self._violations]
    
    def get_confirmed(self, case_id: str) -> List[Violation]:
        """Get confirmed violations for a case."""
        return [
            v for v in self.get_by_case(case_id)
            if v.status in [ViolationStatus.CONFIRMED, ViolationStatus.APPROVED, ViolationStatus.FILED]
        ]
    
    def get_by_evidence(self, evidence_id: str) -> List[Violation]:
        """Get violations supported by specific evidence."""
        return [
            v for v in self._violations.values()
            if evidence_id in v.linked_evidence
        ]
    
    def generate_id(self, statute: str) -> str:
        """Generate new violation ID."""
        self._sequence += 1
        year = datetime.now().year
        from .models import Statute
        statute_enum = Statute(statute) if statute in [s.value for s in Statute] else Statute.OTHER
        return create_violation_id(statute_enum, year, self._sequence)


class ExhibitRegistry:
    """In-memory exhibit catalog."""
    
    def __init__(self):
        self._exhibits: Dict[str, Exhibit] = {}
        self._by_case: Dict[str, List[str]] = {}
        self._by_evidence: Dict[str, List[str]] = {}
        self._sequence = 0
    
    def add(self, exhibit: Exhibit) -> Exhibit:
        """Add exhibit to registry."""
        self._exhibits[exhibit.exhibit_id] = exhibit
        
        # Index by case
        if exhibit.case_id not in self._by_case:
            self._by_case[exhibit.case_id] = []
        self._by_case[exhibit.case_id].append(exhibit.exhibit_id)
        
        # Index by evidence
        if exhibit.evidence_id not in self._by_evidence:
            self._by_evidence[exhibit.evidence_id] = []
        self._by_evidence[exhibit.evidence_id].append(exhibit.exhibit_id)
        
        return exhibit
    
    def get(self, exhibit_id: str) -> Optional[Exhibit]:
        """Get exhibit by ID."""
        return self._exhibits.get(exhibit_id)
    
    def get_by_case(self, case_id: str) -> List[Exhibit]:
        """Get all exhibits for a case."""
        exhibit_ids = self._by_case.get(case_id, [])
        return sorted(
            [self._exhibits[eid] for eid in exhibit_ids if eid in self._exhibits],
            key=lambda ex: ex.sequence_number
        )
    
    def get_by_evidence(self, evidence_id: str) -> List[Exhibit]:
        """Get exhibits created from specific evidence."""
        exhibit_ids = self._by_evidence.get(evidence_id, [])
        return [self._exhibits[eid] for eid in exhibit_ids if eid in self._exhibits]
    
    def generate_id(self, case_id: str) -> str:
        """Generate new exhibit ID."""
        self._sequence += 1
        year = datetime.now().year
        return create_exhibit_id(case_id, year, self._sequence)
    
    def get_next_sequence_number(self, case_id: str) -> int:
        """Get next sequence number for case."""
        exhibits = self.get_by_case(case_id)
        return len(exhibits) + 1
