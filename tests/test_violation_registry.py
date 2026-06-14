"""Tests for Evidence Command Center - Violation Registry

Tests violation registration, statute tracking, and evidence linkage.
"""

import pytest
from packages.evidence_command_center import (
    Violation, ViolationRegistry,
    Statute, Severity, ViolationStatus,
    create_violation_id
)


class TestViolationRegistry:
    """Test ViolationRegistry functionality."""
    
    def test_empty_registry(self):
        """Test empty registry behavior."""
        registry = ViolationRegistry()
        
        assert registry.get("VIO-NONEXIST") is None
        assert len(registry.get_by_case("C-0001")) == 0
        assert len(registry.get_by_evidence("EV-00001")) == 0
    
    def test_add_and_retrieve_violation(self):
        """Test adding and retrieving violations."""
        registry = ViolationRegistry()
        
        violation = Violation(
            violation_id="VIO-FCRA-2026-00001",
            case_id="C-0001",
            client_id="CLIENT-001",
            statute=Statute.FCRA,
            statute_full_name="Fair Credit Reporting Act",
            statute_citation="15 U.S.C. § 1681"
        )
        
        registry.add(violation)
        
        assert registry.get("VIO-FCRA-2026-00001") == violation
        assert len(registry.get_by_case("C-0001")) == 1
    
    def test_get_by_case(self):
        """Test retrieving violations by case."""
        registry = ViolationRegistry()
        
        violation1 = Violation(
            violation_id="VIO1",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681"
        )
        
        violation2 = Violation(
            violation_id="VIO2",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FDCPA,
            statute_full_name="FDCPA",
            statute_citation="15 USC 1692"
        )
        
        violation3 = Violation(
            violation_id="VIO3",
            case_id="C-0002",
            client_id="CL2",
            statute=Statute.TCPA,
            statute_full_name="TCPA",
            statute_citation="47 USC 227"
        )
        
        registry.add(violation1)
        registry.add(violation2)
        registry.add(violation3)
        
        case1_violations = registry.get_by_case("C-0001")
        case2_violations = registry.get_by_case("C-0002")
        
        assert len(case1_violations) == 2
        assert len(case2_violations) == 1
        assert violation1 in case1_violations
        assert violation2 in case1_violations
        assert violation3 in case2_violations
    
    def test_get_confirmed_violations(self):
        """Test retrieving only confirmed violations."""
        registry = ViolationRegistry()
        
        confirmed = Violation(
            violation_id="VIO1",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            status=ViolationStatus.CONFIRMED
        )
        
        detected = Violation(
            violation_id="VIO2",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FDCPA,
            statute_full_name="FDCPA",
            statute_citation="15 USC 1692",
            status=ViolationStatus.DETECTED
        )
        
        approved = Violation(
            violation_id="VIO3",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.ECOA,
            statute_full_name="ECOA",
            statute_citation="15 USC 1691",
            status=ViolationStatus.APPROVED
        )
        
        registry.add(confirmed)
        registry.add(detected)
        registry.add(approved)
        
        confirmed_list = registry.get_confirmed("C-0001")
        
        assert len(confirmed_list) == 2  # CONFIRMED and APPROVED
        assert confirmed in confirmed_list
        assert approved in confirmed_list
        assert detected not in confirmed_list
    
    def test_get_by_evidence(self):
        """Test retrieving violations by evidence ID."""
        registry = ViolationRegistry()
        
        violation1 = Violation(
            violation_id="VIO1",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            linked_evidence=["EV-00001", "EV-00002"]
        )
        
        violation2 = Violation(
            violation_id="VIO2",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FDCPA,
            statute_full_name="FDCPA",
            statute_citation="15 USC 1692",
            linked_evidence=["EV-00002", "EV-00003"]
        )
        
        violation3 = Violation(
            violation_id="VIO3",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.TCPA,
            statute_full_name="TCPA",
            statute_citation="47 USC 227",
            linked_evidence=["EV-00004"]
        )
        
        registry.add(violation1)
        registry.add(violation2)
        registry.add(violation3)
        
        # EV-00001 supports VIO1
        ev1_violations = registry.get_by_evidence("EV-00001")
        assert len(ev1_violations) == 1
        assert violation1 in ev1_violations
        
        # EV-00002 supports VIO1 and VIO2
        ev2_violations = registry.get_by_evidence("EV-00002")
        assert len(ev2_violations) == 2
        assert violation1 in ev2_violations
        assert violation2 in ev2_violations
    
    def test_generate_id(self):
        """Test ID generation."""
        registry = ViolationRegistry()
        
        id1 = registry.generate_id("FCRA")
        id2 = registry.generate_id("FDCPA")
        
        assert id1 != id2
        assert "VIO-FCRA-2026" in id1
        assert "VIO-FDCPA-2026" in id2


class TestViolationModel:
    """Test Violation model functionality."""
    
    def test_violation_creation(self):
        """Test creating violation with required fields."""
        violation = Violation(
            violation_id="VIO-FCRA-2026-00001",
            case_id="C-0001",
            client_id="CLIENT-001",
            statute=Statute.FCRA,
            statute_full_name="Fair Credit Reporting Act",
            statute_citation="15 U.S.C. § 1681"
        )
        
        assert violation.violation_id == "VIO-FCRA-2026-00001"
        assert violation.statute == Statute.FCRA
        assert violation.status == ViolationStatus.DETECTED
    
    def test_violation_with_full_metadata(self):
        """Test violation with complete metadata."""
        violation = Violation(
            violation_id="VIO-FCRA-2026-00001",
            case_id="C-0001",
            client_id="CLIENT-001",
            statute=Statute.FCRA,
            statute_full_name="Fair Credit Reporting Act",
            statute_citation="15 U.S.C. § 1681",
            subsection="§ 1681s-2(b)",
            violation_type="failure_to_investigate",
            violation_description="Creditor failed to conduct reasonable investigation",
            violation_date="2026-03-15",
            severity=Severity.HIGH,
            linked_evidence=["EV-2026-00001", "EV-2026-00002"],
            primary_evidence_id="EV-2026-00001",
            ai_detected=True,
            ai_confidence=0.92,
            status=ViolationStatus.CONFIRMED,
            statutory_damages_min=100.0,
            statutory_damages_max=1000.0,
            attorneys_fees_eligible=True,
            tags=["credit_bureau", "investigation"]
        )
        
        assert violation.violation_type == "failure_to_investigate"
        assert violation.severity == Severity.HIGH
        assert len(violation.linked_evidence) == 2
        assert violation.ai_confidence == 0.92
        assert violation.statutory_damages_max == 1000.0
    
    def test_statute_types(self):
        """Test different statute types."""
        statutes = [
            (Statute.FCRA, "Fair Credit Reporting Act"),
            (Statute.FDCPA, "Fair Debt Collection Practices Act"),
            (Statute.TCPA, "Telephone Consumer Protection Act"),
            (Statute.RESPA, "Real Estate Settlement Procedures Act"),
            (Statute.TILA, "Truth in Lending Act"),
            (Statute.ECOA, "Equal Credit Opportunity Act"),
            (Statute.UCC, "Uniform Commercial Code"),
        ]
        
        for statute, name in statutes:
            violation = Violation(
                violation_id=f"VIO-{statute.value}-001",
                case_id="C-0001",
                client_id="CL1",
                statute=statute,
                statute_full_name=name,
                statute_citation="Citation"
            )
            assert violation.statute == statute
    
    def test_severity_levels(self):
        """Test different severity levels."""
        severities = [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW
        ]
        
        for severity in severities:
            violation = Violation(
                violation_id="VIO-001",
                case_id="C-0001",
                client_id="CL1",
                statute=Statute.FCRA,
                statute_full_name="FCRA",
                statute_citation="15 USC 1681",
                severity=severity
            )
            assert violation.severity == severity
    
    def test_violation_status_transitions(self):
        """Test violation status lifecycle."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681"
        )
        
        # Default status
        assert violation.status == ViolationStatus.DETECTED
        
        # Transition through statuses
        violation.status = ViolationStatus.ANALYZED
        assert violation.status == ViolationStatus.ANALYZED
        
        violation.status = ViolationStatus.CONFIRMED
        assert violation.status == ViolationStatus.CONFIRMED
        
        violation.status = ViolationStatus.APPROVED
        assert violation.status == ViolationStatus.APPROVED
    
    def test_ai_detection_metadata(self):
        """Test AI detection metadata."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            ai_detected=True,
            ai_confidence=0.87,
            ai_analysis={
                "model": "gpt-4",
                "reasoning": "Pattern matches known FCRA violation",
                "confidence_breakdown": {
                    "statute_match": 0.95,
                    "evidence_support": 0.80
                }
            }
        )
        
        assert violation.ai_detected is True
        assert violation.ai_confidence == 0.87
        assert violation.ai_analysis["model"] == "gpt-4"
    
    def test_human_review_metadata(self):
        """Test human review metadata."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            human_reviewed=True,
            reviewed_by="attorney@firm.com",
            reviewed_at="2026-06-14T15:30:00Z",
            attorney_confidence="HIGH",
            review_notes="Clear violation, strong evidence"
        )
        
        assert violation.human_reviewed is True
        assert violation.reviewed_by == "attorney@firm.com"
        assert violation.attorney_confidence == "HIGH"
    
    def test_damages_tracking(self):
        """Test damages tracking."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            statutory_damages_min=100.0,
            statutory_damages_max=1000.0,
            actual_damages=500.0,
            punitive_damages_eligible=True,
            attorneys_fees_eligible=True,
            settlement_value=2500.0
        )
        
        assert violation.statutory_damages_min == 100.0
        assert violation.statutory_damages_max == 1000.0
        assert violation.actual_damages == 500.0
        assert violation.punitive_damages_eligible is True
        assert violation.settlement_value == 2500.0


class TestViolationIDGeneration:
    """Test violation ID generation utilities."""
    
    def test_create_violation_id_format(self):
        """Test violation ID format."""
        violation_id = create_violation_id(Statute.FCRA, 2026, 1)
        
        assert violation_id == "VIO-FCRA-2026-00001"
    
    def test_create_violation_id_different_statutes(self):
        """Test ID generation for different statutes."""
        fcra_id = create_violation_id(Statute.FCRA, 2026, 1)
        fdcpa_id = create_violation_id(Statute.FDCPA, 2026, 1)
        tcpa_id = create_violation_id(Statute.TCPA, 2026, 1)
        
        assert "FCRA" in fcra_id
        assert "FDCPA" in fdcpa_id
        assert "TCPA" in tcpa_id
    
    def test_create_violation_id_padding(self):
        """Test ID number is zero-padded."""
        violation_id = create_violation_id(Statute.FCRA, 2026, 42)
        
        assert violation_id == "VIO-FCRA-2026-00042"


class TestViolationEdgeCases:
    """Test edge cases and error handling."""
    
    def test_violation_without_evidence_links(self):
        """Test violation can exist without evidence links initially."""
        registry = ViolationRegistry()
        
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            linked_evidence=[]  # No evidence yet
        )
        
        registry.add(violation)
        assert registry.get("VIO-001") == violation
    
    def test_multiple_violations_same_statute(self):
        """Test multiple violations of same statute."""
        registry = ViolationRegistry()
        
        for i in range(1, 6):
            violation = Violation(
                violation_id=f"VIO-FCRA-{i:05d}",
                case_id="C-0001",
                client_id="CL1",
                statute=Statute.FCRA,
                statute_full_name="FCRA",
                statute_citation="15 USC 1681",
                violation_type=f"violation_type_{i}"
            )
            registry.add(violation)
        
        case_violations = registry.get_by_case("C-0001")
        assert len(case_violations) == 5
        
        # All should be FCRA violations
        assert all(v.statute == Statute.FCRA for v in case_violations)
    
    def test_violation_with_multiple_evidence_links(self):
        """Test violation linked to multiple pieces of evidence."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            linked_evidence=[
                "EV-00001",
                "EV-00002",
                "EV-00003",
                "EV-00004"
            ],
            primary_evidence_id="EV-00001"
        )
        
        assert len(violation.linked_evidence) == 4
        assert violation.primary_evidence_id == "EV-00001"
    
    def test_rejected_violation(self):
        """Test rejected violation tracking."""
        violation = Violation(
            violation_id="VIO-001",
            case_id="C-0001",
            client_id="CL1",
            statute=Statute.FCRA,
            statute_full_name="FCRA",
            statute_citation="15 USC 1681",
            status=ViolationStatus.REJECTED,
            rejection_reason="Insufficient evidence to support claim"
        )
        
        assert violation.status == ViolationStatus.REJECTED
        assert "Insufficient evidence" in violation.rejection_reason
