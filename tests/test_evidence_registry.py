"""Tests for Evidence Command Center - Evidence Registry

Tests evidence registration, chain of custody, and hash verification.
"""

import pytest
import hashlib
import json
from packages.evidence_command_center import (
    Evidence, EvidenceRegistry, EvidenceStatus,
    ChainEntry, create_evidence_id
)


class TestEvidenceRegistry:
    """Test EvidenceRegistry functionality."""
    
    def test_empty_registry(self):
        """Test empty registry behavior."""
        registry = EvidenceRegistry()
        
        assert registry.get("EV-NONEXIST") is None
        assert len(registry.get_by_case("C-0001")) == 0
        assert registry.get_by_hash("abc123") is None
    
    def test_add_and_retrieve_evidence(self):
        """Test adding and retrieving evidence."""
        registry = EvidenceRegistry()
        
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001",
            sha256_hash="abc123"
        )
        
        registry.add(evidence)
        
        assert registry.get("EV-2026-00001") == evidence
        assert len(registry.get_by_case("C-0001")) == 1
        assert registry.get_by_hash("abc123") == evidence
    
    def test_duplicate_hash_rejected(self):
        """Test that duplicate hashes are rejected."""
        registry = EvidenceRegistry()
        
        evidence1 = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001",
            sha256_hash="duplicate_hash"
        )
        
        evidence2 = Evidence(
            evidence_id="EV-00002",
            case_id="C-0001",
            sha256_hash="duplicate_hash"  # Same hash
        )
        
        registry.add(evidence1)
        
        with pytest.raises(ValueError, match="already exists"):
            registry.add(evidence2)
    
    def test_get_by_case(self):
        """Test retrieving evidence by case."""
        registry = EvidenceRegistry()
        
        evidence1 = Evidence(evidence_id="EV1", case_id="C-0001", sha256_hash="hash1")
        evidence2 = Evidence(evidence_id="EV2", case_id="C-0001", sha256_hash="hash2")
        evidence3 = Evidence(evidence_id="EV3", case_id="C-0002", sha256_hash="hash3")
        
        registry.add(evidence1)
        registry.add(evidence2)
        registry.add(evidence3)
        
        case1_evidence = registry.get_by_case("C-0001")
        case2_evidence = registry.get_by_case("C-0002")
        
        assert len(case1_evidence) == 2
        assert len(case2_evidence) == 1
        assert evidence1 in case1_evidence
        assert evidence2 in case1_evidence
        assert evidence3 in case2_evidence
    
    def test_get_approved_evidence(self):
        """Test retrieving only approved evidence."""
        registry = EvidenceRegistry()
        
        approved = Evidence(
            evidence_id="EV1",
            case_id="C-0001",
            status=EvidenceStatus.APPROVED,
            sha256_hash="hash1"
        )
        
        pending = Evidence(
            evidence_id="EV2",
            case_id="C-0001",
            status=EvidenceStatus.PENDING_REVIEW,
            sha256_hash="hash2"
        )
        
        registry.add(approved)
        registry.add(pending)
        
        approved_list = registry.get_approved("C-0001")
        
        assert len(approved_list) == 1
        assert approved_list[0].evidence_id == "EV1"
    
    def test_generate_id(self):
        """Test ID generation."""
        registry = EvidenceRegistry()
        
        id1 = registry.generate_id("C-0001")
        id2 = registry.generate_id("C-0001")
        
        assert id1 != id2
        assert "EV-2026" in id1  # Current year
        assert "EV-2026" in id2


class TestChainOfCustody:
    """Test chain of custody functionality."""
    
    def test_empty_chain(self):
        """Test evidence with no chain entries."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        assert len(evidence.chain_of_custody) == 0
        
        valid, broken_at, error = evidence.verify_chain()
        assert valid is True
        assert broken_at is None
    
    def test_append_to_chain(self):
        """Test appending entries to chain."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        entry = evidence.append_to_chain(
            actor="user@example.com",
            actor_role="uploader",
            action="uploaded",
            details={"source": "email"}
        )
        
        assert len(evidence.chain_of_custody) == 1
        assert entry.actor == "user@example.com"
        assert entry.action == "uploaded"
        assert entry.prev_hash == ""  # First entry
        assert entry.entry_hash != ""  # Hash computed
    
    def test_chain_linkage(self):
        """Test chain entries are properly linked."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        entry1 = evidence.append_to_chain("user1", "uploader", "upload", {})
        entry2 = evidence.append_to_chain("user2", "reviewer", "review", {})
        entry3 = evidence.append_to_chain("user3", "attorney", "approve", {})
        
        # Each entry should reference previous hash
        assert entry1.prev_hash == ""
        assert entry2.prev_hash == entry1.entry_hash
        assert entry3.prev_hash == entry2.entry_hash
    
    def test_chain_verification_intact(self):
        """Test verification of intact chain."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        evidence.append_to_chain("user1", "uploader", "upload", {"file": "doc.pdf"})
        evidence.append_to_chain("user2", "reviewer", "review", {"status": "ok"})
        evidence.append_to_chain("user3", "attorney", "approve", {"approved": True})
        
        valid, broken_at, error = evidence.verify_chain()
        
        assert valid is True
        assert broken_at is None
        assert "intact" in error.lower()
    
    def test_chain_verification_detects_tampering(self):
        """Test detection of tampered chain."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        evidence.append_to_chain("user1", "uploader", "upload", {})
        evidence.append_to_chain("user2", "reviewer", "review", {})
        
        # Tamper with first entry
        evidence.chain_of_custody[0].action = "MODIFIED"
        # Hash remains unchanged, creating mismatch
        
        valid, broken_at, error = evidence.verify_chain()
        
        assert valid is False
        assert broken_at == 0
        assert "tampered" in error.lower()
    
    def test_chain_verification_detects_broken_link(self):
        """Test detection of broken chain link."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        evidence.append_to_chain("user1", "uploader", "upload", {})
        evidence.append_to_chain("user2", "reviewer", "review", {})
        
        # Break the link by modifying prev_hash
        evidence.chain_of_custody[1].prev_hash = "WRONG_HASH"
        
        valid, broken_at, error = evidence.verify_chain()
        
        assert valid is False
        assert broken_at == 1
        assert "broken" in error.lower()
    
    def test_hash_computation_deterministic(self):
        """Test hash computation is deterministic."""
        entry1 = ChainEntry(
            timestamp="2026-06-14T12:00:00Z",
            actor="user@example.com",
            actor_role="uploader",
            action="upload",
            details={"file": "document.pdf"},
            prev_hash="abc123"
        )
        
        hash1 = entry1.compute_hash()
        hash2 = entry1.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest
    
    def test_hash_changes_with_content(self):
        """Test hash changes when content changes."""
        entry1 = ChainEntry(
            timestamp="2026-06-14T12:00:00Z",
            actor="user1",
            actor_role="uploader",
            action="upload",
            details={},
            prev_hash=""
        )
        
        entry2 = ChainEntry(
            timestamp="2026-06-14T12:00:00Z",
            actor="user2",  # Different actor
            actor_role="uploader",
            action="upload",
            details={},
            prev_hash=""
        )
        
        assert entry1.compute_hash() != entry2.compute_hash()


class TestEvidenceModel:
    """Test Evidence model functionality."""
    
    def test_evidence_creation(self):
        """Test creating evidence with required fields."""
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001"
        )
        
        assert evidence.evidence_id == "EV-2026-00001"
        assert evidence.case_id == "C-0001"
        assert evidence.status == EvidenceStatus.PENDING_REVIEW
        assert evidence.created_at != ""
    
    def test_evidence_with_full_metadata(self):
        """Test evidence with complete metadata."""
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001",
            client_id="CLIENT-001",
            source_type="upload",
            source_reference="email_attachment",
            date_acquired="2026-06-14T10:00:00Z",
            acquired_by="paralegal@firm.com",
            file_name="credit_report.pdf",
            file_size_bytes=1024000,
            mime_type="application/pdf",
            storage_key="s3://bucket/evidence/credit_report.pdf",
            sha256_hash="abc123def456",
            integrity_verified=True,
            category="credit_report",
            subcategory="Equifax",
            tags=["credit", "bureau", "report"],
            status=EvidenceStatus.APPROVED,
            created_by="system"
        )
        
        assert evidence.file_name == "credit_report.pdf"
        assert evidence.sha256_hash == "abc123def456"
        assert evidence.category == "credit_report"
        assert "credit" in evidence.tags
        assert evidence.status == EvidenceStatus.APPROVED
    
    def test_evidence_violation_linkage(self):
        """Test linking evidence to violations."""
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001"
        )
        
        evidence.linked_violations = ["VIO-FCRA-2026-00001", "VIO-FDCPA-2026-00002"]
        
        assert len(evidence.linked_violations) == 2
        assert "VIO-FCRA-2026-00001" in evidence.linked_violations
    
    def test_evidence_metadata_storage(self):
        """Test arbitrary metadata storage."""
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001"
        )
        
        evidence.metadata = {
            "pages": 15,
            "report_date": "2026-01-15",
            "bureau": "TransUnion",
            "ai_summary": "Credit report showing disputed tradeline"
        }
        
        assert evidence.metadata["pages"] == 15
        assert evidence.metadata["bureau"] == "TransUnion"


class TestEvidenceIDGeneration:
    """Test evidence ID generation utilities."""
    
    def test_create_evidence_id_format(self):
        """Test evidence ID format."""
        evidence_id = create_evidence_id("C-0001", 2026, 1)
        
        assert evidence_id == "EV-2026-00001"
    
    def test_create_evidence_id_padding(self):
        """Test ID number is zero-padded."""
        evidence_id = create_evidence_id("C-0001", 2026, 42)
        
        assert evidence_id == "EV-2026-00042"
    
    def test_create_evidence_id_large_numbers(self):
        """Test ID handles large numbers."""
        evidence_id = create_evidence_id("C-0001", 2026, 99999)
        
        assert evidence_id == "EV-2026-99999"


class TestEvidenceEdgeCases:
    """Test edge cases and error handling."""
    
    def test_evidence_without_hash_allowed(self):
        """Test evidence can be created without hash initially."""
        registry = EvidenceRegistry()
        
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001",
            sha256_hash=""  # No hash yet
        )
        
        # Should be allowed
        registry.add(evidence)
        assert registry.get("EV-00001") == evidence
    
    def test_multiple_evidence_same_case(self):
        """Test multiple evidence items for same case."""
        registry = EvidenceRegistry()
        
        for i in range(1, 6):
            evidence = Evidence(
                evidence_id=f"EV-{i:05d}",
                case_id="C-0001",
                sha256_hash=f"hash{i}"
            )
            registry.add(evidence)
        
        case_evidence = registry.get_by_case("C-0001")
        assert len(case_evidence) == 5
    
    def test_evidence_status_transitions(self):
        """Test evidence can transition through statuses."""
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001"
        )
        
        assert evidence.status == EvidenceStatus.PENDING_REVIEW
        
        evidence.status = EvidenceStatus.REVIEWED
        assert evidence.status == EvidenceStatus.REVIEWED
        
        evidence.status = EvidenceStatus.APPROVED
        assert evidence.status == EvidenceStatus.APPROVED
    
    def test_empty_chain_verification_succeeds(self):
        """Test empty chain verifies successfully."""
        evidence = Evidence(evidence_id="EV1", case_id="C-0001")
        
        valid, broken_at, error = evidence.verify_chain()
        
        assert valid is True
        assert broken_at is None
