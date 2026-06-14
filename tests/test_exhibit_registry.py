"""Tests for Evidence Command Center - Exhibit Management

Tests exhibit creation, numbering, ordering, and manifest generation.
"""

import pytest
from packages.evidence_command_center import (
    Evidence, Exhibit, ExhibitRegistry,
    generate_letter_label, generate_exhibit_number,
    create_exhibit_from_evidence, batch_create_exhibits,
    generate_exhibit_manifest, get_exhibit_stats
)


class TestLetterLabelGeneration:
    """Test exhibit letter label generation (A, B, ..., Z, AA, AB, ...)."""
    
    def test_single_letters(self):
        """Test single letter labels."""
        assert generate_letter_label(1) == "A"
        assert generate_letter_label(2) == "B"
        assert generate_letter_label(26) == "Z"
    
    def test_double_letters(self):
        """Test double letter labels."""
        assert generate_letter_label(27) == "AA"
        assert generate_letter_label(28) == "AB"
        assert generate_letter_label(52) == "AZ"
        assert generate_letter_label(53) == "BA"
    
    def test_triple_letters(self):
        """Test triple letter labels."""
        assert generate_letter_label(703) == "AAA"


class TestExhibitNumberGeneration:
    """Test exhibit number formatting."""
    
    def test_letter_format(self):
        """Test LETTER format."""
        assert generate_exhibit_number(1, "LETTER") == "A"
        assert generate_exhibit_number(26, "LETTER") == "Z"
        assert generate_exhibit_number(27, "LETTER") == "AA"
    
    def test_number_format(self):
        """Test NUMBER format."""
        assert generate_exhibit_number(1, "NUMBER") == "1"
        assert generate_exhibit_number(99, "NUMBER") == "99"
    
    def test_prefix_letter_format(self):
        """Test PREFIX_LETTER format."""
        assert generate_exhibit_number(1, "PREFIX_LETTER", "Plaintiff") == "Plaintiff-A"
        assert generate_exhibit_number(2, "PREFIX_LETTER", "Plaintiff") == "Plaintiff-B"
    
    def test_prefix_number_format(self):
        """Test PREFIX_NUMBER format."""
        assert generate_exhibit_number(1, "PREFIX_NUMBER", "DEF") == "DEF-001"
        assert generate_exhibit_number(42, "PREFIX_NUMBER", "DEF") == "DEF-042"


class TestExhibitRegistry:
    """Test ExhibitRegistry functionality."""
    
    def test_empty_registry(self):
        """Test empty registry behavior."""
        registry = ExhibitRegistry()
        
        assert registry.get("EX-NONEXIST") is None
        assert len(registry.get_by_case("C-0001")) == 0
        assert len(registry.get_by_evidence("EV-00001")) == 0
    
    def test_add_and_retrieve_exhibit(self):
        """Test adding and retrieving exhibits."""
        registry = ExhibitRegistry()
        
        exhibit = Exhibit(
            exhibit_id="EX-C-00-2026-00001",
            case_id="C-0001",
            evidence_id="EV-2026-00001",
            exhibit_number="A",
            sequence_number=1
        )
        
        registry.add(exhibit)
        
        assert registry.get("EX-C-00-2026-00001") == exhibit
        assert len(registry.get_by_case("C-0001")) == 1
        assert len(registry.get_by_evidence("EV-2026-00001")) == 1
    
    def test_exhibits_sorted_by_sequence(self):
        """Test that exhibits are returned in sequence order."""
        registry = ExhibitRegistry()
        
        # Add exhibits out of order
        exhibit_c = Exhibit(
            exhibit_id="EX3",
            case_id="C-0001",
            evidence_id="EV3",
            exhibit_number="C",
            sequence_number=3
        )
        exhibit_a = Exhibit(
            exhibit_id="EX1",
            case_id="C-0001",
            evidence_id="EV1",
            exhibit_number="A",
            sequence_number=1
        )
        exhibit_b = Exhibit(
            exhibit_id="EX2",
            case_id="C-0001",
            evidence_id="EV2",
            exhibit_number="B",
            sequence_number=2
        )
        
        registry.add(exhibit_c)
        registry.add(exhibit_a)
        registry.add(exhibit_b)
        
        exhibits = registry.get_by_case("C-0001")
        
        assert len(exhibits) == 3
        assert exhibits[0].exhibit_number == "A"
        assert exhibits[1].exhibit_number == "B"
        assert exhibits[2].exhibit_number == "C"
    
    def test_generate_id_increments(self):
        """Test ID generation increments properly."""
        registry = ExhibitRegistry()
        
        id1 = registry.generate_id("C-0001")
        id2 = registry.generate_id("C-0001")
        id3 = registry.generate_id("C-0002")
        
        assert id1 != id2 != id3
        assert "2026" in id1  # Current year
    
    def test_next_sequence_number(self):
        """Test sequence number tracking."""
        registry = ExhibitRegistry()
        
        assert registry.get_next_sequence_number("C-0001") == 1
        
        registry.add(Exhibit(
            exhibit_id="EX1",
            case_id="C-0001",
            evidence_id="EV1",
            exhibit_number="A",
            sequence_number=1
        ))
        
        assert registry.get_next_sequence_number("C-0001") == 2
        
        registry.add(Exhibit(
            exhibit_id="EX2",
            case_id="C-0001",
            evidence_id="EV2",
            exhibit_number="B",
            sequence_number=2
        ))
        
        assert registry.get_next_sequence_number("C-0001") == 3
    
    def test_multiple_exhibits_per_evidence(self):
        """Test multiple exhibits can reference same evidence."""
        registry = ExhibitRegistry()
        
        exhibit1 = Exhibit(
            exhibit_id="EX1",
            case_id="C-0001",
            evidence_id="EV-00001",
            exhibit_number="A",
            sequence_number=1,
            page_range="1-5"
        )
        
        exhibit2 = Exhibit(
            exhibit_id="EX2",
            case_id="C-0001",
            evidence_id="EV-00001",  # Same evidence
            exhibit_number="B",
            sequence_number=2,
            page_range="6-10"
        )
        
        registry.add(exhibit1)
        registry.add(exhibit2)
        
        exhibits = registry.get_by_evidence("EV-00001")
        assert len(exhibits) == 2


class TestExhibitCreation:
    """Test creating exhibits from evidence."""
    
    def test_create_exhibit_from_evidence(self):
        """Test basic exhibit creation."""
        registry = ExhibitRegistry()
        
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001",
            file_name="credit_report.pdf",
            category="credit_report",
            storage_key="evidence/C-0001/EV-2026-00001/credit_report.pdf",
            created_by="attorney@firm.com"
        )
        evidence.metadata = {"pages": 10}
        
        exhibit = create_exhibit_from_evidence(
            evidence=evidence,
            case_id="C-0001",
            exhibit_registry=registry,
            label_format="LETTER"
        )
        
        assert exhibit.evidence_id == "EV-2026-00001"
        assert exhibit.exhibit_number == "A"
        assert exhibit.sequence_number == 1
        assert exhibit.page_count == 10
        assert exhibit.created_by == "attorney@firm.com"
        
        # Should be in registry
        assert registry.get(exhibit.exhibit_id) == exhibit
    
    def test_exhibit_title_generation(self):
        """Test exhibit title is generated from evidence."""
        registry = ExhibitRegistry()
        
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001",
            category="collection_letter",
            file_name="collection_notice.pdf"
        )
        
        exhibit = create_exhibit_from_evidence(
            evidence=evidence,
            case_id="C-0001",
            exhibit_registry=registry
        )
        
        assert "Collection Letter" in exhibit.exhibit_title
    
    def test_bates_numbering(self):
        """Test Bates numbering is applied correctly."""
        registry = ExhibitRegistry()
        
        evidence = Evidence(
            evidence_id="EV-00001",
            case_id="C-0001",
            category="credit_report"
        )
        evidence.metadata = {"pages": 5}
        
        exhibit = create_exhibit_from_evidence(
            evidence=evidence,
            case_id="C-0001",
            exhibit_registry=registry,
            bates_prefix="JONES"
        )
        
        assert exhibit.bates_numbering is True
        assert exhibit.bates_prefix == "JONES"
        assert exhibit.bates_start == 1
        assert exhibit.bates_end == 5
    
    def test_bates_numbering_continues_sequence(self):
        """Test Bates numbering continues across multiple exhibits."""
        registry = ExhibitRegistry()
        
        # First exhibit: pages 1-5
        evidence1 = Evidence(evidence_id="EV1", case_id="C-0001", category="report")
        evidence1.metadata = {"pages": 5}
        
        exhibit1 = create_exhibit_from_evidence(
            evidence=evidence1,
            case_id="C-0001",
            exhibit_registry=registry,
            bates_prefix="CASE"
        )
        
        assert exhibit1.bates_start == 1
        assert exhibit1.bates_end == 5
        
        # Second exhibit: should start at 6
        evidence2 = Evidence(evidence_id="EV2", case_id="C-0001", category="letter")
        evidence2.metadata = {"pages": 3}
        
        exhibit2 = create_exhibit_from_evidence(
            evidence=evidence2,
            case_id="C-0001",
            exhibit_registry=registry,
            bates_prefix="CASE"
        )
        
        assert exhibit2.bates_start == 6
        assert exhibit2.bates_end == 8
    
    def test_batch_create_exhibits(self):
        """Test batch creation of exhibits."""
        registry = ExhibitRegistry()
        
        evidence_items = [
            Evidence(evidence_id=f"EV-{i}", case_id="C-0001", category="document")
            for i in range(1, 4)
        ]
        
        exhibits = batch_create_exhibits(
            evidence_items=evidence_items,
            case_id="C-0001",
            exhibit_registry=registry
        )
        
        assert len(exhibits) == 3
        assert exhibits[0].exhibit_number == "A"
        assert exhibits[1].exhibit_number == "B"
        assert exhibits[2].exhibit_number == "C"
        
        # All should be in registry
        assert len(registry.get_by_case("C-0001")) == 3


class TestExhibitManifest:
    """Test exhibit manifest generation."""
    
    def test_empty_manifest(self):
        """Test manifest for empty exhibit list."""
        manifest = generate_exhibit_manifest([])
        assert "No exhibits" in manifest
    
    def test_manifest_formatting(self):
        """Test manifest is properly formatted."""
        exhibits = [
            Exhibit(
                exhibit_id="EX1",
                case_id="C-0001",
                evidence_id="EV1",
                exhibit_number="A",
                sequence_number=1,
                exhibit_title="Credit Report dated 2026-01-15",
                page_count=10
            ),
            Exhibit(
                exhibit_id="EX2",
                case_id="C-0001",
                evidence_id="EV2",
                exhibit_number="B",
                sequence_number=2,
                exhibit_title="Collection Letter",
                page_count=2
            )
        ]
        
        manifest = generate_exhibit_manifest(exhibits)
        
        assert "TABLE OF EXHIBITS" in manifest
        assert "Exhibit" in manifest
        assert "Description" in manifest
        assert "Pages" in manifest
        assert "A" in manifest
        assert "B" in manifest
        assert "Credit Report" in manifest
        assert "Collection Letter" in manifest
    
    def test_manifest_page_ranges(self):
        """Test manifest calculates page ranges correctly."""
        exhibits = [
            Exhibit(
                exhibit_id="EX1",
                case_id="C-0001",
                evidence_id="EV1",
                exhibit_number="A",
                sequence_number=1,
                exhibit_title="Doc A",
                page_count=5
            ),
            Exhibit(
                exhibit_id="EX2",
                case_id="C-0001",
                evidence_id="EV2",
                exhibit_number="B",
                sequence_number=2,
                exhibit_title="Doc B",
                page_count=3
            )
        ]
        
        manifest = generate_exhibit_manifest(exhibits)
        
        # First exhibit: pages 1-5
        assert "1-5" in manifest
        # Second exhibit: pages 6-8
        assert "6-8" in manifest
    
    def test_manifest_respects_sequence_order(self):
        """Test manifest respects exhibit sequence order."""
        exhibits = [
            Exhibit(
                exhibit_id="EX3",
                case_id="C-0001",
                evidence_id="EV3",
                exhibit_number="C",
                sequence_number=3,
                exhibit_title="Third",
                page_count=1
            ),
            Exhibit(
                exhibit_id="EX1",
                case_id="C-0001",
                evidence_id="EV1",
                exhibit_number="A",
                sequence_number=1,
                exhibit_title="First",
                page_count=1
            ),
            Exhibit(
                exhibit_id="EX2",
                case_id="C-0001",
                evidence_id="EV2",
                exhibit_number="B",
                sequence_number=2,
                exhibit_title="Second",
                page_count=1
            )
        ]
        
        manifest = generate_exhibit_manifest(exhibits)
        
        # Should be sorted A, B, C
        lines = manifest.split("\n")
        a_line = next(i for i, line in enumerate(lines) if line.startswith("A"))
        b_line = next(i for i, line in enumerate(lines) if line.startswith("B"))
        c_line = next(i for i, line in enumerate(lines) if line.startswith("C"))
        
        assert a_line < b_line < c_line


class TestExhibitStatistics:
    """Test exhibit statistics calculation."""
    
    def test_empty_stats(self):
        """Test stats for empty exhibit list."""
        stats = get_exhibit_stats([])
        
        assert stats["total_exhibits"] == 0
        assert stats["total_pages"] == 0
        assert stats["bates_range"] is None
        assert stats["formats"] == []
    
    def test_basic_stats(self):
        """Test basic statistics."""
        exhibits = [
            Exhibit(
                exhibit_id="EX1",
                case_id="C-0001",
                evidence_id="EV1",
                exhibit_number="A",
                page_count=10,
                file_format="PDF"
            ),
            Exhibit(
                exhibit_id="EX2",
                case_id="C-0001",
                evidence_id="EV2",
                exhibit_number="B",
                page_count=5,
                file_format="PDF"
            )
        ]
        
        stats = get_exhibit_stats(exhibits)
        
        assert stats["total_exhibits"] == 2
        assert stats["total_pages"] == 15
        assert "PDF" in stats["formats"]
    
    def test_bates_range_calculation(self):
        """Test Bates range is calculated correctly."""
        exhibits = [
            Exhibit(
                exhibit_id="EX1",
                case_id="C-0001",
                evidence_id="EV1",
                exhibit_number="A",
                page_count=5,
                bates_numbering=True,
                bates_prefix="CASE",
                bates_start=1,
                bates_end=5
            ),
            Exhibit(
                exhibit_id="EX2",
                case_id="C-0001",
                evidence_id="EV2",
                exhibit_number="B",
                page_count=3,
                bates_numbering=True,
                bates_prefix="CASE",
                bates_start=6,
                bates_end=8
            )
        ]
        
        stats = get_exhibit_stats(exhibits)
        
        assert stats["bates_range"] == "CASE-0001 to CASE-0008"
    
    def test_multiple_formats(self):
        """Test multiple file formats are tracked."""
        exhibits = [
            Exhibit(exhibit_id="EX1", case_id="C-0001", evidence_id="EV1",
                   exhibit_number="A", file_format="PDF"),
            Exhibit(exhibit_id="EX2", case_id="C-0001", evidence_id="EV2",
                   exhibit_number="B", file_format="DOCX"),
            Exhibit(exhibit_id="EX3", case_id="C-0001", evidence_id="EV3",
                   exhibit_number="C", file_format="PDF")
        ]
        
        stats = get_exhibit_stats(exhibits)
        
        assert len(stats["formats"]) == 2
        assert "PDF" in stats["formats"]
        assert "DOCX" in stats["formats"]


class TestExhibitEdgeCases:
    """Test edge cases and error handling."""
    
    def test_duplicate_exhibit_numbers_prevented(self):
        """Test that duplicate exhibit numbers are prevented by sequence tracking."""
        registry = ExhibitRegistry()
        
        evidence1 = Evidence(evidence_id="EV1", case_id="C-0001", category="doc1")
        evidence2 = Evidence(evidence_id="EV2", case_id="C-0001", category="doc2")
        
        exhibit1 = create_exhibit_from_evidence(evidence1, "C-0001", registry)
        exhibit2 = create_exhibit_from_evidence(evidence2, "C-0001", registry)
        
        # Should have different exhibit numbers
        assert exhibit1.exhibit_number != exhibit2.exhibit_number
        assert exhibit1.sequence_number == 1
        assert exhibit2.sequence_number == 2
    
    def test_evidence_to_exhibit_linkage_preserved(self):
        """Test evidence-to-exhibit linkage is preserved."""
        registry = ExhibitRegistry()
        
        evidence = Evidence(
            evidence_id="EV-2026-00001",
            case_id="C-0001",
            sha256_hash="abc123def456",
            storage_key="evidence/original.pdf"
        )
        
        exhibit = create_exhibit_from_evidence(evidence, "C-0001", registry)
        
        assert exhibit.evidence_id == "EV-2026-00001"
        assert exhibit.original_storage_key == "evidence/original.pdf"
        
        # Should be retrievable by evidence ID
        retrieved = registry.get_by_evidence("EV-2026-00001")
        assert len(retrieved) == 1
        assert retrieved[0].exhibit_id == exhibit.exhibit_id
