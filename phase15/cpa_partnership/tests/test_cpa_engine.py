"""Tests for Phase 15C — CPA Partnership Engine."""
import sys, os

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from phase15.cpa_partnership.cpa_engine import (
    CaseType, PartnerStatus, ReferralStatus, FeeStructure,
    CPAPartner, TaxCase, Referral, PartnerScore,
    PartnerRouter, FeeTracker, NotificationAdapter, CPAPartnershipEngine,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tax_partner():
    return CPAPartner(
        partner_id="P001",
        name="Alice CPA",
        firm_name="Alice & Associates",
        email="alice@cpa.com",
        phone="+15551234567",
        license_number="CPA-12345",
        states_licensed=["CA", "NY", "TX"],
        specializations=[CaseType.TAX_PREPARATION, CaseType.IRS_AUDIT, CaseType.TAX_DISPUTE],
        status=PartnerStatus.ACTIVE,
        fee_structure=FeeStructure.PERCENTAGE,
        fee_rate=0.15,
        max_monthly_referrals=20,
        rating=4.8,
        response_time_hours=4.0,
    )


@pytest.fixture
def general_partner():
    return CPAPartner(
        partner_id="P002",
        name="Bob CPA",
        firm_name="Bob's Accounting",
        email="bob@cpa.com",
        states_licensed=["CA"],
        specializations=[],  # General practice
        status=PartnerStatus.ACTIVE,
        fee_structure=FeeStructure.FLAT,
        flat_fee=500.0,
        max_monthly_referrals=10,
        rating=4.0,
        response_time_hours=24.0,
    )


@pytest.fixture
def tax_case():
    return TaxCase(
        case_id="C001",
        client_name="John Taxpayer",
        client_email="john@example.com",
        case_type=CaseType.IRS_AUDIT,
        state="CA",
        estimated_value=10000.0,
        urgency=4,
    )


@pytest.fixture
def engine():
    return CPAPartnershipEngine()


@pytest.fixture
def engine_with_partners(engine, tax_partner, general_partner):
    engine.register_partner(tax_partner)
    engine.register_partner(general_partner)
    return engine


# ---------------------------------------------------------------------------
# CPAPartner tests
# ---------------------------------------------------------------------------

class TestCPAPartner:
    def test_can_accept_referral_active(self, tax_partner):
        assert tax_partner.can_accept_referral() is True

    def test_cannot_accept_when_inactive(self, tax_partner):
        tax_partner.status = PartnerStatus.INACTIVE
        assert tax_partner.can_accept_referral() is False

    def test_cannot_accept_when_at_capacity(self, tax_partner):
        tax_partner.current_month_referrals = tax_partner.max_monthly_referrals
        assert tax_partner.can_accept_referral() is False

    def test_handles_case_type_match(self, tax_partner):
        assert tax_partner.handles_case_type(CaseType.IRS_AUDIT) is True

    def test_handles_case_type_no_match(self, tax_partner):
        assert tax_partner.handles_case_type(CaseType.BOOKKEEPING) is False

    def test_general_partner_handles_all_types(self, general_partner):
        for ct in CaseType:
            assert general_partner.handles_case_type(ct) is True

    def test_is_licensed_in_state(self, tax_partner):
        assert tax_partner.is_licensed_in("CA") is True
        assert tax_partner.is_licensed_in("ca") is True  # case insensitive
        assert tax_partner.is_licensed_in("FL") is False

    def test_is_licensed_no_restrictions(self, general_partner):
        # Empty states_licensed means licensed everywhere
        general_partner.states_licensed = []
        assert general_partner.is_licensed_in("FL") is True

    def test_calculate_fee_percentage(self, tax_partner):
        fee = tax_partner.calculate_fee(10000.0)
        assert fee == 1500.0  # 15% of 10000

    def test_calculate_fee_flat(self, general_partner):
        fee = general_partner.calculate_fee(50000.0)
        assert fee == 500.0  # flat fee regardless of value

    def test_calculate_fee_tiered_low(self):
        p = CPAPartner("P3", "Tiered", "Firm", "t@t.com",
                       fee_structure=FeeStructure.TIERED)
        assert p.calculate_fee(3000.0) == 600.0  # 20% of 3000

    def test_calculate_fee_tiered_mid(self):
        p = CPAPartner("P4", "Tiered", "Firm", "t@t.com",
                       fee_structure=FeeStructure.TIERED)
        fee = p.calculate_fee(10000.0)
        # 20% of 5000 = 1000, 15% of 5000 = 750 → 1750
        assert fee == 1750.0

    def test_calculate_fee_tiered_high(self):
        p = CPAPartner("P5", "Tiered", "Firm", "t@t.com",
                       fee_structure=FeeStructure.TIERED)
        fee = p.calculate_fee(30000.0)
        # 20% of 5k=1000, 15% of 15k=2250, 10% of 10k=1000 → 4250
        assert fee == 4250.0


# ---------------------------------------------------------------------------
# TaxCase tests
# ---------------------------------------------------------------------------

class TestTaxCase:
    def test_is_urgent_high(self, tax_case):
        tax_case.urgency = 4
        assert tax_case.is_urgent() is True

    def test_is_urgent_critical(self, tax_case):
        tax_case.urgency = 5
        assert tax_case.is_urgent() is True

    def test_not_urgent_low(self, tax_case):
        tax_case.urgency = 3
        assert tax_case.is_urgent() is False


# ---------------------------------------------------------------------------
# Referral tests
# ---------------------------------------------------------------------------

class TestReferral:
    def test_accept_updates_partner(self, tax_partner, tax_case):
        ref = Referral("R001", tax_case, tax_partner)
        initial_count = tax_partner.current_month_referrals
        ref.accept()
        assert ref.status == ReferralStatus.ACCEPTED
        assert tax_partner.current_month_referrals == initial_count + 1
        assert ref.accepted_at is not None

    def test_complete_updates_status(self, tax_partner, tax_case):
        ref = Referral("R002", tax_case, tax_partner)
        ref.accept()
        ref.complete(actual_value=8000.0)
        assert ref.status == ReferralStatus.COMPLETED
        assert ref.fee_amount == 1200.0  # 15% of 8000
        assert ref.completed_at is not None

    def test_mark_fee_paid(self, tax_partner, tax_case):
        ref = Referral("R003", tax_case, tax_partner, fee_amount=1500.0)
        ref.accept()
        ref.complete()
        ref.mark_fee_paid()
        assert ref.fee_paid is True
        assert ref.status == ReferralStatus.FEE_PAID
        assert tax_partner.total_fees_earned == 1500.0


# ---------------------------------------------------------------------------
# PartnerRouter tests
# ---------------------------------------------------------------------------

class TestPartnerRouter:
    def test_score_partner_full_match(self, tax_partner, tax_case):
        router = PartnerRouter()
        score = router.score_partner(tax_partner, tax_case)
        assert score.score > 80  # Should score very high

    def test_score_partner_no_state_license(self, tax_partner, tax_case):
        tax_case.state = "FL"  # Not licensed in FL
        router = PartnerRouter()
        score = router.score_partner(tax_partner, tax_case)
        # Should lose state_license points (30)
        assert score.score < 80

    def test_rank_partners_best_first(self, tax_partner, general_partner, tax_case):
        router = PartnerRouter()
        ranked = router.rank_partners([tax_partner, general_partner], tax_case)
        assert len(ranked) == 2
        assert ranked[0].score >= ranked[1].score

    def test_select_best_returns_top(self, tax_partner, general_partner, tax_case):
        router = PartnerRouter()
        best = router.select_best([tax_partner, general_partner], tax_case)
        assert best is not None
        assert best.partner.partner_id == "P001"  # Alice is the specialist

    def test_select_best_no_partners(self, tax_case):
        router = PartnerRouter()
        best = router.select_best([], tax_case)
        assert best is None

    def test_rank_excludes_at_capacity(self, tax_partner, tax_case):
        tax_partner.current_month_referrals = tax_partner.max_monthly_referrals
        router = PartnerRouter()
        ranked = router.rank_partners([tax_partner], tax_case)
        assert len(ranked) == 0

    def test_score_reasons_populated(self, tax_partner, tax_case):
        router = PartnerRouter()
        score = router.score_partner(tax_partner, tax_case)
        assert len(score.reasons) > 0

    def test_capacity_affects_score(self, tax_partner, tax_case):
        router = PartnerRouter()
        score_full = router.score_partner(tax_partner, tax_case)
        tax_partner.current_month_referrals = 18  # Almost full
        score_low = router.score_partner(tax_partner, tax_case)
        assert score_full.score > score_low.score


# ---------------------------------------------------------------------------
# FeeTracker tests
# ---------------------------------------------------------------------------

class TestFeeTracker:
    def test_register_and_get_pending(self, tax_partner, tax_case):
        tracker = FeeTracker()
        ref = Referral("R001", tax_case, tax_partner, fee_amount=1500.0)
        ref.accept()
        ref.complete()
        tracker.register(ref)
        pending = tracker.get_pending_fees()
        assert len(pending) == 1

    def test_total_earned_after_payment(self, tax_partner, tax_case):
        tracker = FeeTracker()
        ref = Referral("R002", tax_case, tax_partner, fee_amount=1000.0)
        ref.accept()
        ref.complete()
        ref.mark_fee_paid()
        tracker.register(ref)
        assert tracker.get_total_earned() == 1000.0

    def test_total_pending(self, tax_partner, tax_case):
        tracker = FeeTracker()
        ref = Referral("R003", tax_case, tax_partner, fee_amount=750.0)
        ref.accept()
        ref.complete()
        tracker.register(ref)
        assert tracker.get_total_pending() == 750.0

    def test_monthly_summary(self, tax_partner, tax_case):
        tracker = FeeTracker()
        ref = Referral("R004", tax_case, tax_partner, fee_amount=500.0)
        ref.accept()
        ref.complete()
        ref.mark_fee_paid()
        tracker.register(ref)
        now = datetime.utcnow()
        summary = tracker.get_monthly_summary(now.year, now.month)
        assert summary["total_referrals"] == 1
        assert summary["completed"] == 1
        assert summary["fees_earned"] == 500.0

    def test_total_earned_by_partner(self, tax_partner, general_partner, tax_case):
        tracker = FeeTracker()
        ref1 = Referral("R005", tax_case, tax_partner, fee_amount=1000.0)
        ref1.accept()
        ref1.complete()
        ref1.mark_fee_paid()
        ref2 = Referral("R006", tax_case, general_partner, fee_amount=500.0)
        ref2.accept()
        ref2.complete()
        ref2.mark_fee_paid()
        tracker.register(ref1)
        tracker.register(ref2)
        assert tracker.get_total_earned(partner_id="P001") == 1000.0
        assert tracker.get_total_earned(partner_id="P002") == 500.0


# ---------------------------------------------------------------------------
# CPAPartnershipEngine tests
# ---------------------------------------------------------------------------

class TestCPAPartnershipEngine:
    def test_register_partner(self, engine, tax_partner):
        result = engine.register_partner(tax_partner)
        assert result.partner_id == "P001"
        assert engine.get_partner("P001") is tax_partner

    def test_list_partners_all(self, engine_with_partners):
        partners = engine_with_partners.list_partners()
        assert len(partners) == 2

    def test_list_partners_active_only(self, engine_with_partners, tax_partner):
        tax_partner.status = PartnerStatus.INACTIVE
        active = engine_with_partners.list_partners(PartnerStatus.ACTIVE)
        assert len(active) == 1

    def test_deactivate_partner(self, engine_with_partners):
        assert engine_with_partners.deactivate_partner("P001") is True
        assert engine_with_partners.get_partner("P001").status == PartnerStatus.INACTIVE

    def test_deactivate_unknown_partner(self, engine):
        assert engine.deactivate_partner("GHOST") is False

    def test_route_case_creates_referral(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        assert referral is not None
        assert referral.status == ReferralStatus.ACCEPTED
        assert referral.fee_amount > 0

    def test_route_case_no_partners(self, engine, tax_case):
        referral = engine.route_case(tax_case)
        assert referral is None

    def test_route_case_selects_specialist(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        # Alice (P001) specializes in IRS_AUDIT, should be selected
        assert referral.partner.partner_id == "P001"

    def test_complete_referral(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        assert engine_with_partners.complete_referral(referral.referral_id, 12000.0) is True
        assert referral.status == ReferralStatus.COMPLETED
        assert referral.fee_amount == 1800.0  # 15% of 12000

    def test_complete_unknown_referral(self, engine):
        assert engine.complete_referral("GHOST") is False

    def test_mark_fee_paid(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        engine_with_partners.complete_referral(referral.referral_id)
        assert engine_with_partners.mark_fee_paid(referral.referral_id) is True
        assert referral.fee_paid is True

    def test_on_referral_created_callback(self, tax_partner, tax_case):
        callback = MagicMock()
        engine = CPAPartnershipEngine(on_referral_created=callback)
        engine.register_partner(tax_partner)
        engine.route_case(tax_case)
        callback.assert_called_once()

    def test_on_fee_earned_callback(self, tax_partner, tax_case):
        callback = MagicMock()
        engine = CPAPartnershipEngine(on_fee_earned=callback)
        engine.register_partner(tax_partner)
        referral = engine.route_case(tax_case)
        engine.complete_referral(referral.referral_id)
        engine.mark_fee_paid(referral.referral_id)
        callback.assert_called_once()

    def test_decline_referral_reroutes(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        original_partner = referral.partner.partner_id
        engine_with_partners.decline_referral(referral.referral_id, "Too busy")
        # Should have been re-routed to the other partner
        assert referral.partner.partner_id != original_partner

    def test_get_ranked_partners(self, engine_with_partners, tax_case):
        ranked = engine_with_partners.get_ranked_partners(tax_case)
        assert len(ranked) == 2
        assert ranked[0].score >= ranked[1].score

    def test_reset_monthly_counts(self, engine_with_partners, tax_partner):
        tax_partner.current_month_referrals = 10
        engine_with_partners.reset_monthly_counts()
        assert tax_partner.current_month_referrals == 0

    def test_get_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats["total_partners"] == 0
        assert stats["total_referrals"] == 0
        assert stats["completion_rate"] == 0.0

    def test_get_stats_with_data(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        engine_with_partners.complete_referral(referral.referral_id)
        engine_with_partners.mark_fee_paid(referral.referral_id)
        stats = engine_with_partners.get_stats()
        assert stats["total_partners"] == 2
        assert stats["total_referrals"] == 1
        assert stats["completed_referrals"] == 1
        assert stats["total_fees_earned"] > 0

    def test_get_partner_leaderboard(self, engine_with_partners, tax_case):
        referral = engine_with_partners.route_case(tax_case)
        engine_with_partners.complete_referral(referral.referral_id)
        engine_with_partners.mark_fee_paid(referral.referral_id)
        board = engine_with_partners.get_partner_leaderboard()
        assert len(board) == 2
        # Partner with fees earned should be first
        assert board[0]["total_fees_earned"] >= board[1]["total_fees_earned"]
