"""
Tests for BRA Constitutional Evidence Ledger — BKGC Art. XIII–XIV compliance.
"""
import pytest
from blackstone.bra.cel import (
    ConstitutionalEvidenceLedger,
    EvidenceDeletionProhibitedError,
    LegalHoldViolationError,
    EvidenceNotFoundError,
)


@pytest.fixture
def cel():
    return ConstitutionalEvidenceLedger()


@pytest.fixture
def ev_id(cel):
    return cel.add(
        "26 U.S.C. § 6213 — Restrictions on assessment",
        source_class="SC-01",
        collected_by="hermes",
        citation="26 U.S.C. § 6213",
        jurisdiction_code="US-FED",
    )


class TestAdd:
    def test_returns_ev_id(self, cel):
        ev_id = cel.add("Test", source_class="SC-02", collected_by="hermes")
        assert ev_id.startswith("EV-")

    def test_ev_id_format(self, cel):
        import re
        ev_id = cel.add("Test", source_class="SC-03", collected_by="hermes")
        assert re.match(r"^EV-\d{8}-\d{4}$", ev_id)

    def test_ai_generated_must_be_sc06(self, cel):
        with pytest.raises(ValueError, match="SC-06"):
            cel.add("AI Summary", source_class="SC-01", collected_by="viktor", is_ai_generated=True)

    def test_ai_generated_sc06_ok(self, cel):
        ev_id = cel.add("AI Summary", source_class="SC-06", collected_by="viktor", is_ai_generated=True)
        item = cel.get(ev_id)
        assert item.is_ai_generated is True

    def test_invalid_source_class_raises(self, cel):
        with pytest.raises(ValueError, match="Unknown source class"):
            cel.add("Test", source_class="SC-99", collected_by="hermes")

    def test_chain_of_custody_initialized(self, cel, ev_id):
        item = cel.get(ev_id)
        assert len(item.chain_of_custody) == 1
        assert item.chain_of_custody[0].event_type == "COLLECTED"


class TestAuthentication:
    def test_authenticate_sets_intact(self, cel, ev_id):
        cel.authenticate(ev_id, "viktor", content_hash="sha256:abc123")
        item = cel.get(ev_id)
        assert item.integrity_status == "INTACT"

    def test_authenticate_sets_reverification_due(self, cel, ev_id):
        cel.authenticate(ev_id, "viktor")
        item = cel.get(ev_id)
        assert item.reverification_due is not None

    def test_authentication_logged_in_custody(self, cel, ev_id):
        cel.authenticate(ev_id, "viktor")
        item = cel.get(ev_id)
        events = [e.event_type for e in item.chain_of_custody]
        assert "AUTHENTICATED" in events

    def test_invalid_reliability_score_raises(self, cel, ev_id):
        with pytest.raises(ValueError, match="0–20"):
            cel.authenticate(ev_id, "viktor", source_reliability_score=25)


class TestNoDeletion:
    def test_delete_raises(self, cel, ev_id):
        with pytest.raises(EvidenceDeletionProhibitedError):
            cel.delete(ev_id)

    def test_deprecated_item_still_in_ledger(self, cel, ev_id):
        cel.authenticate(ev_id, "viktor")
        cel.deprecate(ev_id, "viktor", reason="Superseded")
        item = cel.get(ev_id)
        assert item.is_deprecated is True
        assert item.ev_id == ev_id  # still accessible

    def test_total_count_includes_deprecated(self, cel):
        ev1 = cel.add("A", source_class="SC-01", collected_by="hermes")
        ev2 = cel.add("B", source_class="SC-02", collected_by="hermes")
        cel.authenticate(ev1, "viktor")
        cel.deprecate(ev1, "viktor", reason="Old")
        assert len(cel.list_all()) == 2
        assert len(cel.list_active()) == 1


class TestLegalHold:
    def test_held_item_cannot_be_deprecated(self, cel, ev_id):
        cel.authenticate(ev_id, "viktor")
        cel.place_hold(ev_id, "isiah", "IRS litigation hold")
        with pytest.raises(LegalHoldViolationError):
            cel.deprecate(ev_id, "viktor", reason="test")

    def test_held_item_cannot_be_authenticated(self, cel):
        ev_id = cel.add("Test", source_class="SC-01", collected_by="hermes")
        cel.place_hold(ev_id, "isiah", "hold basis")
        with pytest.raises(LegalHoldViolationError):
            cel.authenticate(ev_id, "viktor")

    def test_release_hold_allows_modification(self, cel, ev_id):
        cel.place_hold(ev_id, "isiah", "test hold")
        cel.release_hold(ev_id, "isiah", "CDR-00004")
        cel.authenticate(ev_id, "viktor")
        item = cel.get(ev_id)
        assert item.integrity_status == "INTACT"


class TestAuditReport:
    def test_audit_report_structure(self, cel, ev_id):
        report = cel.audit_report()
        assert "total_items" in report
        assert "active_items" in report
        assert "deprecated_items" in report
        assert report["total_items"] >= 1
