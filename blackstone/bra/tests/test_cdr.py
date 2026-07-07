"""
Tests for BRA CDR Filer — BKGC Art. XXXIII, BKR-11 compliance.
"""
import pytest
from blackstone.bra.cdr import CDRFiler, CDRFilingError


@pytest.fixture
def filer():
    return CDRFiler(seed_founding_cdrs=True)


@pytest.fixture
def fresh_filer():
    return CDRFiler(seed_founding_cdrs=False)


class TestFoundingCDRs:
    def test_three_founding_cdrs_seeded(self, filer):
        register = filer.register()
        assert len(register) == 3

    def test_cdr_00001_exists(self, filer):
        cdr = filer.get("CDR-00001")
        assert "AI-Generated" in cdr.title

    def test_cdr_00002_exists(self, filer):
        cdr = filer.get("CDR-00002")
        assert "BGS" in cdr.title

    def test_cdr_00003_exists(self, filer):
        cdr = filer.get("CDR-00003")
        assert "BCCM" in cdr.title

    def test_all_founding_approved(self, filer):
        for cdr in filer.register():
            assert cdr["status"] == "Approved"


class TestImmutability:
    def test_cdr_record_is_frozen(self, filer):
        cdr = filer.get("CDR-00001")
        with pytest.raises(Exception):  # FrozenInstanceError
            cdr.title = "Modified"  # type: ignore

    def test_filed_cdr_cannot_be_deleted(self, fresh_filer):
        num = fresh_filer.file(
            title="Test CDR",
            filed_by="Governance Board",
            trigger="Test",
            decision="Test decision",
            scope="All agents",
        )
        # No delete method exists — verify AttributeError
        assert not hasattr(fresh_filer, "delete")


class TestFiling:
    def test_file_returns_sequential_number(self, fresh_filer):
        n1 = fresh_filer.file("T1", "GB", "t", "d", "s")
        n2 = fresh_filer.file("T2", "GB", "t", "d", "s")
        assert n1 == "CDR-00001"
        assert n2 == "CDR-00002"

    def test_new_cdr_after_founding(self, filer):
        num = filer.file("New Policy", "GB", "trigger", "decision", "scope")
        assert num == "CDR-00004"

    def test_supersede_marks_old_as_superseded(self, filer):
        new_num = filer.file(
            title="Updated Policy",
            filed_by="GB",
            trigger="update",
            decision="new decision",
            scope="all",
            supersedes_cdr="CDR-00001",
        )
        old = filer.get("CDR-00001")
        assert old.status == "Superseded"
        assert old.superseded_by_cdr == new_num

    def test_supersede_nonexistent_raises(self, filer):
        with pytest.raises(CDRFilingError):
            filer.file("T", "GB", "t", "d", "s", supersedes_cdr="CDR-99999")


class TestRegister:
    def test_register_ordered_by_number(self, filer):
        register = filer.register()
        numbers = [r["cdr_number"] for r in register]
        assert numbers == sorted(numbers)

    def test_next_number_preview(self, filer):
        next_num = filer.next_number()
        assert next_num == "CDR-00004"
        actual = filer.file("Test", "GB", "t", "d", "s")
        assert actual == next_num
