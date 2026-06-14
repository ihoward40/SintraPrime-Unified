"""Evidence Command Center - Readiness Scoring Engine

Calculates case readiness scores based on evidence completeness,
violation support, chain of custody, timeline, and document quality.

Status: MVP (design validation)
Created: 2026-06-14
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .models import Evidence, Violation, Exhibit, EvidenceStatus, ViolationStatus


@dataclass
class ReadinessScore:
    """Case readiness assessment."""
    __test__ = False  # Prevent pytest from collecting as test
    
    overall_score: float  # 0-100
    readiness_level: str  # NOT_READY, PARTIAL, OPERATIONAL, LITIGATION_READY
    
    # Component scores
    evidence_completeness: float  # 0-25
    violation_support: float  # 0-25
    chain_of_custody: float  # 0-20
    timeline_completeness: float  # 0-15
    document_quality: float  # 0-15
    
    # Breakdown
    total_evidence: int
    approved_evidence: int
    total_violations: int
    confirmed_violations: int
    total_exhibits: int
    
    # Recommendations
    gaps: List[str]
    recommendations: List[str]
    
    def __post_init__(self):
        """Compute overall score and readiness level."""
        self.overall_score = (
            self.evidence_completeness +
            self.violation_support +
            self.chain_of_custody +
            self.timeline_completeness +
            self.document_quality
        )
        
        # Determine readiness level
        if self.overall_score >= 85:
            self.readiness_level = "LITIGATION_READY"
        elif self.overall_score >= 70:
            self.readiness_level = "OPERATIONAL"
        elif self.overall_score >= 40:
            self.readiness_level = "PARTIAL"
        else:
            self.readiness_level = "NOT_READY"


def score_evidence_completeness(
    evidence_items: List[Evidence],
    required_categories: List[str]
) -> tuple[float, List[str]]:
    """
    Score evidence completeness (0-25 points).
    
    Criteria:
    - Has all required evidence categories (15 points)
    - Evidence is approved status (5 points)
    - Evidence has chain of custody (5 points)
    """
    gaps = []
    score = 0.0
    
    if not evidence_items:
        gaps.append("No evidence items present")
        return (0.0, gaps)
    
    # Check for required categories (15 points)
    present_categories = {ev.category for ev in evidence_items}
    missing_categories = set(required_categories) - present_categories
    
    if missing_categories:
        gaps.append(f"Missing evidence categories: {', '.join(missing_categories)}")
        category_score = 15.0 * (len(present_categories) / len(required_categories))
    else:
        category_score = 15.0
    
    score += category_score
    
    # Check approval status (5 points)
    approved_count = sum(1 for ev in evidence_items if ev.status == EvidenceStatus.APPROVED)
    if approved_count == 0:
        gaps.append("No evidence items approved by attorney")
        approval_score = 0.0
    else:
        approval_score = 5.0 * (approved_count / len(evidence_items))
        if approved_count < len(evidence_items):
            gaps.append(f"Only {approved_count}/{len(evidence_items)} evidence items approved")
    
    score += approval_score
    
    # Check chain of custody (5 points)
    chain_count = sum(1 for ev in evidence_items if ev.chain_of_custody)
    if chain_count == 0:
        gaps.append("No evidence has chain of custody")
        chain_score = 0.0
    else:
        chain_score = 5.0 * (chain_count / len(evidence_items))
        if chain_count < len(evidence_items):
            gaps.append(f"Only {chain_count}/{len(evidence_items)} evidence items have chain of custody")
    
    score += chain_score
    
    return (score, gaps)


def score_violation_support(
    violations: List[Violation],
    evidence_items: List[Evidence]
) -> tuple[float, List[str]]:
    """
    Score violation support (0-25 points).
    
    Criteria:
    - Has confirmed violations (10 points)
    - Violations linked to evidence (10 points)
    - High-severity violations present (5 points)
    """
    gaps = []
    score = 0.0
    
    if not violations:
        gaps.append("No violations identified")
        return (0.0, gaps)
    
    # Check for confirmed violations (10 points)
    confirmed_count = sum(
        1 for v in violations 
        if v.status in [ViolationStatus.CONFIRMED, ViolationStatus.APPROVED, ViolationStatus.FILED]
    )
    
    if confirmed_count == 0:
        gaps.append("No violations confirmed")
        confirmed_score = 0.0
    else:
        confirmed_score = 10.0 * min(confirmed_count / 3, 1.0)  # Full score at 3+ confirmed
        if confirmed_count < 3:
            gaps.append(f"Only {confirmed_count} violations confirmed (recommend 3+)")
    
    score += confirmed_score
    
    # Check evidence linkage (10 points)
    linked_count = sum(1 for v in violations if v.linked_evidence)
    if linked_count == 0:
        gaps.append("No violations linked to evidence")
        linkage_score = 0.0
    else:
        linkage_score = 10.0 * (linked_count / len(violations))
        if linked_count < len(violations):
            gaps.append(f"Only {linked_count}/{len(violations)} violations linked to evidence")
    
    score += linkage_score
    
    # Check for high-severity violations (5 points)
    high_severity_count = sum(
        1 for v in violations 
        if v.severity in ["CRITICAL", "HIGH"]
    )
    
    if high_severity_count == 0:
        gaps.append("No high-severity violations (case may have low settlement value)")
        severity_score = 0.0
    else:
        severity_score = 5.0
    
    score += severity_score
    
    return (score, gaps)


def score_chain_of_custody(evidence_items: List[Evidence]) -> tuple[float, List[str]]:
    """
    Score chain of custody integrity (0-20 points).
    
    Criteria:
    - All evidence has chain of custody (10 points)
    - All chains verified (10 points)
    """
    gaps = []
    score = 0.0
    
    if not evidence_items:
        return (0.0, ["No evidence to assess"])
    
    # Check presence (10 points)
    with_chain = sum(1 for ev in evidence_items if ev.chain_of_custody)
    presence_score = 10.0 * (with_chain / len(evidence_items))
    score += presence_score
    
    if with_chain < len(evidence_items):
        gaps.append(f"Only {with_chain}/{len(evidence_items)} evidence items have chain of custody")
    
    # Check integrity (10 points)
    verified_count = 0
    broken_count = 0
    
    for ev in evidence_items:
        if ev.chain_of_custody:
            valid, broken_at, error = ev.verify_chain()
            if valid:
                verified_count += 1
            else:
                broken_count += 1
                gaps.append(f"Evidence {ev.evidence_id}: chain broken at entry {broken_at}")
    
    if with_chain > 0:
        integrity_score = 10.0 * (verified_count / with_chain)
        score += integrity_score
    
    if broken_count > 0:
        gaps.append(f"{broken_count} evidence items have broken chain of custody")
    
    return (score, gaps)


def score_timeline_completeness(
    violations: List[Violation],
    evidence_items: List[Evidence]
) -> tuple[float, List[str]]:
    """
    Score timeline completeness (0-15 points).
    
    Criteria:
    - Violations have dates (10 points)
    - Evidence has acquisition dates (5 points)
    """
    gaps = []
    score = 0.0
    
    # Violation dates (10 points)
    if violations:
        with_dates = sum(1 for v in violations if v.violation_date)
        date_score = 10.0 * (with_dates / len(violations))
        score += date_score
        
        if with_dates < len(violations):
            gaps.append(f"Only {with_dates}/{len(violations)} violations have dates")
    else:
        gaps.append("No violations to assess timeline")
    
    # Evidence acquisition dates (5 points)
    if evidence_items:
        with_dates = sum(1 for ev in evidence_items if ev.date_acquired)
        acq_score = 5.0 * (with_dates / len(evidence_items))
        score += acq_score
        
        if with_dates < len(evidence_items):
            gaps.append(f"Only {with_dates}/{len(evidence_items)} evidence items have acquisition dates")
    else:
        gaps.append("No evidence to assess timeline")
    
    return (score, gaps)


def score_document_quality(
    evidence_items: List[Evidence],
    exhibits: List[Exhibit]
) -> tuple[float, List[str]]:
    """
    Score document quality (0-15 points).
    
    Criteria:
    - Evidence has SHA-256 hashes (5 points)
    - Evidence is properly categorized (5 points)
    - Exhibits created (5 points)
    """
    gaps = []
    score = 0.0
    
    if not evidence_items:
        return (0.0, ["No evidence to assess quality"])
    
    # SHA-256 hashes (5 points)
    with_hash = sum(1 for ev in evidence_items if ev.sha256_hash)
    hash_score = 5.0 * (with_hash / len(evidence_items))
    score += hash_score
    
    if with_hash < len(evidence_items):
        gaps.append(f"Only {with_hash}/{len(evidence_items)} evidence items have SHA-256 hash")
    
    # Categorization (5 points)
    categorized = sum(1 for ev in evidence_items if ev.category and ev.category != "other")
    cat_score = 5.0 * (categorized / len(evidence_items))
    score += cat_score
    
    if categorized < len(evidence_items):
        gaps.append(f"Only {categorized}/{len(evidence_items)} evidence items properly categorized")
    
    # Exhibits (5 points)
    if exhibits:
        exhibit_score = 5.0
    else:
        gaps.append("No exhibits created (evidence not court-ready)")
        exhibit_score = 0.0
    
    score += exhibit_score
    
    return (score, gaps)


def calculate_readiness_score(
    evidence_items: List[Evidence],
    violations: List[Violation],
    exhibits: List[Exhibit],
    required_evidence_categories: Optional[List[str]] = None
) -> ReadinessScore:
    """
    Calculate overall case readiness score.
    
    Args:
        evidence_items: List of evidence in the case
        violations: List of violations identified
        exhibits: List of exhibits created
        required_evidence_categories: Required categories for case type
    
    Returns:
        ReadinessScore with overall score and component breakdowns
    """
    if required_evidence_categories is None:
        required_evidence_categories = ["credit_report", "collection_letter"]
    
    all_gaps = []
    all_recommendations = []
    
    # Score each component
    evidence_score, evidence_gaps = score_evidence_completeness(
        evidence_items, required_evidence_categories
    )
    all_gaps.extend(evidence_gaps)
    
    violation_score, violation_gaps = score_violation_support(
        violations, evidence_items
    )
    all_gaps.extend(violation_gaps)
    
    custody_score, custody_gaps = score_chain_of_custody(evidence_items)
    all_gaps.extend(custody_gaps)
    
    timeline_score, timeline_gaps = score_timeline_completeness(
        violations, evidence_items
    )
    all_gaps.extend(timeline_gaps)
    
    quality_score, quality_gaps = score_document_quality(
        evidence_items, exhibits
    )
    all_gaps.extend(quality_gaps)
    
    # Generate recommendations based on gaps
    if evidence_score < 15:
        all_recommendations.append("Upload missing evidence categories")
    if violation_score < 15:
        all_recommendations.append("Confirm more violations with attorney review")
    if custody_score < 15:
        all_recommendations.append("Complete chain of custody for all evidence")
    if timeline_score < 10:
        all_recommendations.append("Add dates to violations and evidence")
    if quality_score < 10:
        all_recommendations.append("Generate SHA-256 hashes and create exhibits")
    
    # Count statistics
    approved_evidence = sum(1 for ev in evidence_items if ev.status == EvidenceStatus.APPROVED)
    confirmed_violations = sum(
        1 for v in violations 
        if v.status in [ViolationStatus.CONFIRMED, ViolationStatus.APPROVED]
    )
    
    return ReadinessScore(
        overall_score=0.0,  # Will be computed in __post_init__
        readiness_level="",  # Will be computed in __post_init__
        evidence_completeness=evidence_score,
        violation_support=violation_score,
        chain_of_custody=custody_score,
        timeline_completeness=timeline_score,
        document_quality=quality_score,
        total_evidence=len(evidence_items),
        approved_evidence=approved_evidence,
        total_violations=len(violations),
        confirmed_violations=confirmed_violations,
        total_exhibits=len(exhibits),
        gaps=all_gaps,
        recommendations=all_recommendations
    )
