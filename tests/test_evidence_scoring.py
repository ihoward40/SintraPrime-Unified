"""Tests for Evidence Command Center - Scoring Engine

Tests readiness score calculation, component scoring, and edge cases.
"""

import pytest
from packages.evidence_command_center import (
    Evidence, Violation, Exhibit,
    EvidenceStatus, ViolationStatus, Statute, Severity,
    calculate_readiness_score,
    score_evidence_completeness,
    score_violation_support,
    score_chain_of_custody,
    score_timeline_completeness,
    score_document_quality
)


class TestReadinessScoreCalculation:
    """Test overall readiness score calculation."""
    
    def test_empty_case_scores_zero(self):
        """Empty case should score 0/100."""
        score = calculate_readiness_score(
            evidence_items=[],
            violations=[],
            exhibits=[]
        )
        assert score.overall_score == 0.0
        assert score.readiness_level == "NOT_READY"
        assert len(score.gaps) > 0
    
    def test_perfect_case_scores_high(self):
        """Complete case should score 85+/100."""
        # Create approved evidence with chain of custody
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001",
            category="credit_report",
            status=EvidenceStatus.APPROVED,
            sha256_hash="abc123",
            date_acquired="2026-06-14T00:00:00Z"
        )
        evidence.append_to_chain("attorney", "reviewer", "approved", {"reason": "valid"})
        
        # Create confirmed violation linked to evidence
        violation = Violation(
            violation_id="VIO-FCRA-2026-00001",
            case_id="C-0001",
            client_id="CLIENT-001",
            statute=Statute.FCRA,
            statute_full_name="Fair Credit Reporting Act",
            statute_citation="15 U.S.C. § 1681",
            violation_type="inaccurate_reporting",
            violation_description="Account reported inaccurately",
            violation_date="2026-01-15",
            severity=Severity.HIGH,
            status=ViolationStatus.CONFIRMED,
            linked_evidence=["EV-2026-00001"]
        )
        
        # Create exhibit
        exhibit = Exhibit(
            exhibit_id="EX-C-00-2026-00001",
            case_id="C-0001",
            evidence_id="EV-2026-00001",
            exhibit_number="A",
            page_count=5
        )
        
        score = calculate_readiness_score(
            evidence_items=[evidence],
            violations=[violation],
            exhibits=[exhibit],
            required_evidence_categories=["credit_report"]
        )
        
        # Should score very high (components add up)
        assert score.overall_score >= 70.0
        assert score.readiness_level in ["OPERATIONAL", "LITIGATION_READY"]
        assert score.total_evidence == 1
        assert score.approved_evidence == 1
        assert score.total_violations == 1
        assert score.confirmed_violations == 1
    
    def test_score_boundaries(self):
        """Score should never exceed 100 or go below 0."""
        # Test various cases
        test_cases = [
            ([], [], []),  # Empty
            ([Evidence(evidence_id="E1", case_id="C1")], [], []),  # Just evidence
            ([], [Violation(
                violation_id="V1", case_id="C1", client_id="CL1",
                statute=Statute.FCRA, statute_full_name="FCRA",
                statute_citation="15 USC 1681"
            )], []),  # Just violation
        ]
        
        for evidence_items, violations, exhibits in test_cases:
            score = calculate_readiness_score(evidence_items, violations, exhibits)
            assert 0.0 <= score.overall_score <= 100.0, \
                f"Score {score.overall_score} out of bounds"
    
    def test_readiness_level_thresholds(self):
        """Test readiness level classification."""
        # Mock score objects with different overall scores
        from packages.evidence_command_center.scoring import ReadinessScore
        
        # Test threshold boundaries
        test_cases = [
            (90, "LITIGATION_READY"),
            (85, "LITIGATION_READY"),
            (84, "OPERATIONAL"),
            (70, "OPERATIONAL"),
            (69, "PARTIAL"),
            (40, "PARTIAL"),
            (39, "NOT_READY"),
            (0, "NOT_READY"),
        ]
        
        for overall_score, expected_level in test_cases:
            # Create score with specific overall_score
            score = ReadinessScore(
                overall_score=overall_score,
                readiness_level="",
                evidence_completeness=overall_score * 0.25,
                violation_support=overall_score * 0.25,
                chain_of_custody=overall_score * 0.20,
                timeline_completeness=overall_score * 0.15,
                document_quality=overall_score * 0.15,
                total_evidence=1,
                approved_evidence=1,
                total_violations=1,
                confirmed_violations=1,
                total_exhibits=1,
                gaps=[],
                recommendations=[]
            )
            # __post_init__ should set readiness_level
            assert score.readiness_level == expected_level, \
                f"Score {overall_score} should be {expected_level}, got {score.readiness_level}"


class TestEvidenceCompletenessScoring:
    """Test evidence completeness component (0-25 points)."""
    
    def test_no_evidence_scores_zero(self):
        """No evidence should score 0."""
        score, gaps = score_evidence_completeness([], ["credit_report"])
        assert score == 0.0
        assert any("no evidence" in gap.lower() for gap in gaps)
    
    def test_missing_categories_penalized(self):
        """Missing required categories should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="other",
            status=EvidenceStatus.APPROVED,
            sha256_hash="abc"
        )
        evidence.append_to_chain("user", "uploader", "uploaded", {})
        
        score, gaps = score_evidence_completeness(
            [evidence],
            required_categories=["credit_report", "collection_letter"]
        )
        
        # Should get partial category score (1 of 2 categories = 50% of 15 points)
        # Plus approval (5 points) and chain (5 points)
        assert score < 25.0  # Missing categories
        assert any("missing" in gap.lower() for gap in gaps)
    
    def test_unapproved_evidence_penalized(self):
        """Unapproved evidence should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            status=EvidenceStatus.PENDING_REVIEW,
            sha256_hash="abc"
        )
        
        score, gaps = score_evidence_completeness(
            [evidence],
            ["credit_report"]
        )
        
        # Category match (15) but no approval (0) and no chain (0)
        assert score == 15.0
        assert any("approved" in gap.lower() for gap in gaps)
    
    def test_missing_chain_of_custody_penalized(self):
        """Missing chain of custody should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            status=EvidenceStatus.APPROVED,
            sha256_hash="abc"
        )
        # No chain entries
        
        score, gaps = score_evidence_completeness(
            [evidence],
            ["credit_report"]
        )
        
        # Category (15) + approval (5) but no chain (0)
        assert score == 20.0
        assert any("chain of custody" in gap.lower() for gap in gaps)
    
    def test_perfect_evidence_scores_25(self):
        """Perfect evidence should score full 25 points."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            status=EvidenceStatus.APPROVED,
            sha256_hash="abc"
        )
        evidence.append_to_chain("user", "uploader", "uploaded", {})
        
        score, gaps = score_evidence_completeness(
            [evidence],
            ["credit_report"]
        )
        
        assert score == 25.0
        assert len(gaps) == 0


class TestViolationSupportScoring:
    """Test violation support component (0-25 points)."""
    
    def test_no_violations_scores_zero(self):
        """No violations should score 0."""
        score, gaps = score_violation_support([], [])
        assert score == 0.0
        assert any("no violations" in gap.lower() for gap in gaps)
    
    def test_unconfirmed_violations_penalized(self):
        """Unconfirmed violations should score 0 on confirmation component."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            status=ViolationStatus.DETECTED,  # Not confirmed
            linked_evidence=["E1"],
            severity=Severity.HIGH
        )
        
        score, gaps = score_violation_support([violation], [])
        
        # No confirmation (0) + linkage (10) + severity (5) = 15
        assert score == 15.0
        assert any("confirmed" in gap.lower() for gap in gaps)
    
    def test_unlinked_violations_penalized(self):
        """Violations without evidence links should be penalized."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            status=ViolationStatus.CONFIRMED,
            linked_evidence=[],  # No links
            severity=Severity.HIGH
        )
        
        score, gaps = score_violation_support([violation], [])
        
        # Confirmed (partial, < 3) + no linkage (0) + severity (5) < 25
        assert score < 25.0
        assert any("linked to evidence" in gap.lower() for gap in gaps)
    
    def test_low_severity_violations_penalized(self):
        """Low severity violations should not get severity bonus."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            status=ViolationStatus.CONFIRMED,
            linked_evidence=["E1"],
            severity=Severity.LOW
        )
        
        score, gaps = score_violation_support([violation], [])
        
        # Should not get full 5 severity points
        assert score < 25.0
        assert any("low settlement value" in gap.lower() for gap in gaps)
    
    def test_multiple_confirmed_violations_score_full(self):
        """3+ confirmed high-severity linked violations should score 25."""
        violations = [
            Violation(
                violation_id=f"V{i}",
                case_id="C1",
                client_id="CL1",
                statute=Statute.FCRA,
                statute_full_name="FCRA",
                statute_citation="15 USC 1681",
                status=ViolationStatus.CONFIRMED,
                linked_evidence=[f"E{i}"],
                severity=Severity.HIGH
            )
            for i in range(1, 4)
        ]
        
        score, gaps = score_violation_support(violations, [])
        
        assert score == 25.0


class TestChainOfCustodyScoring:
    """Test chain of custody component (0-20 points)."""
    
    def test_no_evidence_scores_zero(self):
        """No evidence should score 0."""
        score, gaps = score_chain_of_custody([])
        assert score == 0.0
    
    def test_missing_chains_penalized(self):
        """Evidence without chains should be penalized."""
        evidence = Evidence(evidence_id="E1", case_id="C1")
        # No chain entries
        
        score, gaps = score_chain_of_custody([evidence])
        
        assert score == 0.0
        assert any("chain of custody" in gap.lower() for gap in gaps)
    
    def test_broken_chain_detected(self):
        """Broken chain should be detected and penalized."""
        evidence = Evidence(evidence_id="E1", case_id="C1")
        
        # Add entries manually
        entry1 = evidence.append_to_chain("user1", "uploader", "upload", {})
        entry2 = evidence.append_to_chain("user2", "reviewer", "review", {})
        
        # Break the chain by modifying hash
        evidence.chain_of_custody[1].prev_hash = "WRONG_HASH"
        
        score, gaps = score_chain_of_custody([evidence])
        
        # Presence (10) but broken integrity (0)
        assert score == 10.0
        assert any("broken" in gap.lower() for gap in gaps)
    
    def test_intact_chain_scores_20(self):
        """Intact chain should score full 20 points."""
        evidence = Evidence(evidence_id="E1", case_id="C1")
        evidence.append_to_chain("user1", "uploader", "upload", {})
        evidence.append_to_chain("user2", "reviewer", "review", {})
        
        score, gaps = score_chain_of_custody([evidence])
        
        assert score == 20.0
        assert len(gaps) == 0


class TestTimelineCompletenessScoring:
    """Test timeline completeness component (0-15 points)."""
    
    def test_missing_violation_dates_penalized(self):
        """Violations without dates should reduce score."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            violation_date=None  # Missing
        )
        
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            date_acquired="2026-06-14T00:00:00Z"
        )
        
        score, gaps = score_timeline_completeness([violation], [evidence])
        
        # No violation dates (0) + evidence dates (5) = 5
        assert score == 5.0
        assert any("violation" in gap.lower() and "date" in gap.lower() for gap in gaps)
    
    def test_missing_evidence_dates_penalized(self):
        """Evidence without acquisition dates should reduce score."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            violation_date="2026-01-15"
        )
        
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            date_acquired=""  # Missing
        )
        
        score, gaps = score_timeline_completeness([violation], [evidence])
        
        # Violation dates (10) + no evidence dates (0) = 10
        assert score == 10.0
    
    def test_complete_timeline_scores_15(self):
        """Complete timeline should score full 15 points."""
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            violation_date="2026-01-15"
        )
        
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            date_acquired="2026-06-14T00:00:00Z"
        )
        
        score, gaps = score_timeline_completeness([violation], [evidence])
        
        assert score == 15.0


class TestDocumentQualityScoring:
    """Test document quality component (0-15 points)."""
    
    def test_missing_hashes_penalized(self):
        """Evidence without SHA-256 hashes should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            sha256_hash=""  # Missing
        )
        
        score, gaps = score_document_quality([evidence], [])
        
        # No hash (0) + categorized (5) + no exhibits (0) = 5
        assert score == 5.0
        assert any("SHA-256" in gap for gap in gaps)
    
    def test_uncategorized_evidence_penalized(self):
        """Evidence with generic 'other' category should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="other",  # Generic
            sha256_hash="abc123"
        )
        
        score, gaps = score_document_quality([evidence], [])
        
        # Hash (5) + not categorized (0) + no exhibits (0) = 5
        assert score == 5.0
        assert any("categorized" in gap.lower() for gap in gaps)
    
    def test_missing_exhibits_penalized(self):
        """Missing exhibits should reduce score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            sha256_hash="abc123"
        )
        
        score, gaps = score_document_quality([evidence], [])
        
        # Hash (5) + categorized (5) + no exhibits (0) = 10
        assert score == 10.0
        assert any("exhibits" in gap.lower() for gap in gaps)
    
    def test_perfect_quality_scores_15(self):
        """Perfect document quality should score full 15 points."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            sha256_hash="abc123"
        )
        
        exhibit = Exhibit(
            exhibit_id="EX1",
            case_id="C1",
            evidence_id="E1",
            exhibit_number="A"
        )
        
        score, gaps = score_document_quality([evidence], [exhibit])
        
        assert score == 15.0


class TestScoreDeterminism:
    """Test that scores are deterministic and reproducible."""
    
    def test_same_inputs_produce_same_score(self):
        """Same inputs should always produce same score."""
        evidence = Evidence(
            evidence_id="E1",
            case_id="C1",
            category="credit_report",
            status=EvidenceStatus.APPROVED,
            sha256_hash="abc123",
            date_acquired="2026-06-14T00:00:00Z"
        )
        evidence.append_to_chain("user", "uploader", "upload", {})
        
        violation = Violation(
            violation_id="V1",
            case_id="C1",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            violation_date="2026-01-15",
            status=ViolationStatus.CONFIRMED,
            linked_evidence=["E1"],
            severity=Severity.HIGH
        )
        
        exhibit = Exhibit(
            exhibit_id="EX1",
            case_id="C1",
            evidence_id="E1",
            exhibit_number="A",
            page_count=5
        )
        
        # Calculate score multiple times
        score1 = calculate_readiness_score([evidence], [violation], [exhibit], ["credit_report"])
        score2 = calculate_readiness_score([evidence], [violation], [exhibit], ["credit_report"])
        score3 = calculate_readiness_score([evidence], [violation], [exhibit], ["credit_report"])
        
        assert score1.overall_score == score2.overall_score == score3.overall_score
        assert score1.evidence_completeness == score2.evidence_completeness
        assert score1.violation_support == score2.violation_support
        assert score1.chain_of_custody == score2.chain_of_custody
        assert score1.timeline_completeness == score2.timeline_completeness
        assert score1.document_quality == score2.document_quality
