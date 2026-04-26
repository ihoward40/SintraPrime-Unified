"""Tests for Phase 15A — Autonomous Lead Nurture Engine."""
import sys, os

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call
from phase15.lead_nurture.nurture_engine import (
    Lead, LeadStatus, ChannelType, SequenceStep, SequenceStepType,
    NurtureSequence, OutreachResult, SMSAdapter, VoiceCallAdapter,
    VideoOutreachAdapter, CalendarAdapter, NurtureEngine,
    score_lead, render_template, evaluate_condition, SCORE_RULES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_lead():
    return Lead(
        lead_id="L001",
        name="John Smith",
        phone="+15551234567",
        email="john@example.com",
        practice_area="personal_injury",
        source="google_ads",
    )


@pytest.fixture
def engine():
    return NurtureEngine()


@pytest.fixture
def engine_with_mocks():
    sms = MagicMock(spec=SMSAdapter)
    sms.send.return_value = {"sid": "SM123", "status": "queued"}
    voice = MagicMock(spec=VoiceCallAdapter)
    voice.call.return_value = {"sid": "CA456", "status": "queued"}
    video = MagicMock(spec=VideoOutreachAdapter)
    video.send.return_value = {"video_id": "VID789", "status": "rendering"}
    calendar = MagicMock(spec=CalendarAdapter)
    calendar.generate_booking_link.return_value = "https://calendly.com/sintra/demo?name=John"
    calendar.check_booking.return_value = False
    return NurtureEngine(
        sms_adapter=sms,
        voice_adapter=voice,
        video_adapter=video,
        calendar_adapter=calendar,
    ), sms, voice, video, calendar


# ---------------------------------------------------------------------------
# Lead model tests
# ---------------------------------------------------------------------------

class TestLead:
    def test_is_contactable_with_phone(self, basic_lead):
        assert basic_lead.is_contactable() is True

    def test_is_contactable_opted_out(self, basic_lead):
        basic_lead.opted_out = True
        assert basic_lead.is_contactable() is False

    def test_is_contactable_converted(self, basic_lead):
        basic_lead.status = LeadStatus.CONVERTED
        assert basic_lead.is_contactable() is False

    def test_is_contactable_no_contact_info(self):
        lead = Lead(lead_id="L999", name="Ghost")
        assert lead.is_contactable() is False

    def test_days_since_contact_none(self, basic_lead):
        assert basic_lead.days_since_contact() is None

    def test_days_since_contact_yesterday(self, basic_lead):
        basic_lead.last_contacted_at = datetime.utcnow() - timedelta(days=1)
        assert basic_lead.days_since_contact() == 1


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------

class TestScoring:
    def test_score_personal_injury_referral(self):
        lead = Lead(
            lead_id="L1", name="Alice", phone="+1555", email="a@b.com",
            practice_area="personal_injury", source="referral",
        )
        score = score_lead(lead)
        assert score >= 50  # PI(20) + referral(25) + phone(10) + email(5) = 60

    def test_score_capped_at_100(self):
        lead = Lead(
            lead_id="L2", name="Bob", phone="+1555", email="b@b.com",
            practice_area="personal_injury", source="referral",
            tags=["responded_to_sms", "clicked_link", "visited_pricing"],
        )
        score = score_lead(lead)
        assert score == 100

    def test_score_no_contact_info(self):
        lead = Lead(lead_id="L3", name="Nobody", practice_area="general", source="unknown")
        score = score_lead(lead)
        assert score == 0

    def test_score_google_ads_family_law(self):
        lead = Lead(
            lead_id="L4", name="Carol", phone="+1555",
            practice_area="family_law", source="google_ads",
        )
        score = score_lead(lead)
        assert score == 40  # family_law(15) + google_ads(15) + phone(10)

    def test_score_tag_visited_pricing(self):
        lead = Lead(lead_id="L5", name="Dave", phone="+1555", source="organic",
                    tags=["visited_pricing"])
        score = score_lead(lead)
        assert score >= 25  # visited_pricing(25) alone


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------

class TestTemplateRendering:
    def test_sms_initial_renders_name(self, basic_lead):
        text = render_template("sms_initial", basic_lead)
        assert "John" in text
        assert "personal injury" in text.lower()

    def test_sms_followup_1_renders(self, basic_lead):
        text = render_template("sms_followup_1", basic_lead)
        assert "John" in text

    def test_sms_followup_2_includes_booking_link(self, basic_lead):
        text = render_template("sms_followup_2", basic_lead, booking_link="https://book.me")
        assert "https://book.me" in text

    def test_unknown_template_returns_empty(self, basic_lead):
        text = render_template("nonexistent_template", basic_lead)
        assert text == ""


# ---------------------------------------------------------------------------
# Condition evaluator tests
# ---------------------------------------------------------------------------

class TestConditionEvaluator:
    def test_score_greater_than(self, basic_lead):
        basic_lead.score = 75
        assert evaluate_condition("score > 70", basic_lead) is True
        assert evaluate_condition("score > 80", basic_lead) is False

    def test_score_less_than(self, basic_lead):
        basic_lead.score = 30
        assert evaluate_condition("score < 50", basic_lead) is True

    def test_score_greater_equal(self, basic_lead):
        basic_lead.score = 60
        assert evaluate_condition("score >= 60", basic_lead) is True

    def test_tag_condition(self, basic_lead):
        basic_lead.tags = ["responded_to_sms"]
        assert evaluate_condition("tag:responded_to_sms", basic_lead) is True
        assert evaluate_condition("tag:visited_pricing", basic_lead) is False

    def test_status_condition(self, basic_lead):
        basic_lead.status = LeadStatus.NURTURING
        assert evaluate_condition("status:nurturing", basic_lead) is True

    def test_practice_area_condition(self, basic_lead):
        assert evaluate_condition("practice_area:personal_injury", basic_lead) is True
        assert evaluate_condition("practice_area:criminal_defense", basic_lead) is False

    def test_empty_condition_always_true(self, basic_lead):
        assert evaluate_condition("", basic_lead) is True


# ---------------------------------------------------------------------------
# NurtureEngine tests
# ---------------------------------------------------------------------------

class TestNurtureEngine:
    def test_add_lead_scores_it(self, engine, basic_lead):
        added = engine.add_lead(basic_lead)
        assert added.score > 0
        assert engine.get_lead("L001") is basic_lead

    def test_add_lead_returns_lead(self, engine, basic_lead):
        result = engine.add_lead(basic_lead)
        assert result.lead_id == "L001"

    def test_handle_opt_out(self, engine, basic_lead):
        engine.add_lead(basic_lead)
        assert engine.handle_opt_out("L001") is True
        assert basic_lead.opted_out is True
        assert basic_lead.status == LeadStatus.UNSUBSCRIBED

    def test_handle_opt_out_unknown_lead(self, engine):
        assert engine.handle_opt_out("UNKNOWN") is False

    def test_handle_reply_yes_books_demo(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        eng.add_lead(basic_lead)
        result = eng.handle_reply("L001", "YES")
        assert result is not None
        assert result.demo_booked is True
        assert basic_lead.status == LeadStatus.DEMO_BOOKED

    def test_handle_reply_stop_opts_out(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        eng.add_lead(basic_lead)
        result = eng.handle_reply("L001", "STOP")
        assert result is not None
        assert basic_lead.opted_out is True

    def test_handle_reply_unknown_lead(self, engine):
        result = engine.handle_reply("GHOST", "YES")
        assert result is None

    def test_update_lead_tag(self, engine, basic_lead):
        engine.add_lead(basic_lead)
        assert engine.update_lead_tag("L001", "visited_pricing") is True
        assert "visited_pricing" in basic_lead.tags

    def test_update_lead_tag_unknown(self, engine):
        assert engine.update_lead_tag("GHOST", "tag") is False

    def test_get_hot_leads(self, engine):
        hot = Lead(lead_id="H1", name="Hot", phone="+1555",
                   practice_area="personal_injury", source="referral",
                   tags=["responded_to_sms", "visited_pricing"])
        cold = Lead(lead_id="C1", name="Cold", practice_area="general", source="unknown")
        engine.add_lead(hot)
        engine.add_lead(cold)
        hot_leads = engine.get_hot_leads(min_score=60)
        assert any(l.lead_id == "H1" for l in hot_leads)
        assert not any(l.lead_id == "C1" for l in hot_leads)

    def test_get_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats["total_leads"] == 0
        assert stats["conversion_rate"] == 0.0

    def test_get_stats_with_leads(self, engine, basic_lead):
        engine.add_lead(basic_lead)
        basic_lead.status = LeadStatus.CONVERTED
        stats = engine.get_stats()
        assert stats["total_leads"] == 1
        assert stats["converted"] == 1
        assert stats["conversion_rate"] == 100.0

    def test_process_due_leads_sends_sms(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        # Use a non-PI lead so it uses the default sequence (step 0 = SMS)
        basic_lead.practice_area = "family_law"
        eng.add_lead(basic_lead)
        basic_lead.last_contacted_at = None
        results = eng.process_due_leads()
        assert len(results) >= 1
        assert any(r.channel == ChannelType.SMS for r in results)
        sms.send.assert_called_once()

    def test_process_due_leads_skips_opted_out(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        eng.add_lead(basic_lead)
        basic_lead.opted_out = True
        results = eng.process_due_leads()
        assert len(results) == 0
        sms.send.assert_not_called()

    def test_process_due_leads_respects_delay(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        # Use default sequence (not PI hot-lead) so step 1 has delay_hours=2
        basic_lead.practice_area = "family_law"
        eng.add_lead(basic_lead)
        # Move to step 2 (delay=2h) and set last_contacted to just now
        basic_lead.sequence_step = 1
        basic_lead.last_contacted_at = datetime.utcnow()
        results = eng.process_due_leads()
        assert len(results) == 0  # Not yet due

    def test_on_demo_booked_callback(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        callback = MagicMock()
        eng._on_demo_booked = callback
        eng.add_lead(basic_lead)
        eng.handle_reply("L001", "YES")
        callback.assert_called_once_with(basic_lead)

    def test_on_lead_updated_callback(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        callback = MagicMock()
        eng._on_lead_updated = callback
        eng.add_lead(basic_lead)
        eng.update_lead_tag("L001", "new_tag")
        callback.assert_called_once()

    def test_sms_step_no_phone_fails_gracefully(self, engine_with_mocks):
        eng, sms, voice, video, calendar = engine_with_mocks
        lead = Lead(lead_id="NP1", name="No Phone", email="np@test.com",
                    practice_area="general", source="organic")
        eng.add_lead(lead)
        results = eng.process_due_leads()
        # Should return a failed result, not crash
        failed = [r for r in results if not r.success]
        assert len(failed) >= 1

    def test_voice_step_executes(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        # Use default sequence (not PI hot-lead) — step index 1 is make_call
        basic_lead.practice_area = "family_law"
        eng.add_lead(basic_lead)
        basic_lead.sequence_step = 1
        basic_lead.last_contacted_at = datetime.utcnow() - timedelta(hours=3)
        results = eng.process_due_leads()
        assert any(r.channel == ChannelType.VOICE_CALL for r in results)
        voice.call.assert_called_once()

    def test_video_step_executes(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        # Use default sequence (not PI hot-lead) to reach video step
        basic_lead.practice_area = "family_law"
        eng.add_lead(basic_lead)
        basic_lead.sequence_step = 3  # send_video step
        basic_lead.last_contacted_at = datetime.utcnow() - timedelta(hours=50)
        results = eng.process_due_leads()
        assert any(r.channel == ChannelType.VIDEO for r in results)

    def test_add_custom_sequence(self, engine):
        seq = NurtureSequence(
            sequence_id="custom", name="Custom", practice_area="immigration",
            steps=[
                SequenceStep("c1", SequenceStepType.SEND_SMS, 0, {"template": "sms_initial"})
            ],
        )
        engine.add_sequence(seq)
        lead = Lead(lead_id="IM1", name="Immigrant", phone="+1555",
                    practice_area="immigration", source="organic")
        engine.add_lead(lead)
        # Sequence should be found
        seq_found = engine._get_sequence_for_lead(lead)
        assert seq_found is not None
        assert seq_found.sequence_id == "custom"

    def test_get_results_accumulates(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        eng.add_lead(basic_lead)
        eng.process_due_leads()
        assert len(eng.get_results()) >= 1

    def test_demo_booking_sends_confirmation_sms(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        eng.add_lead(basic_lead)
        eng.handle_reply("L001", "BOOK")
        # Should have sent confirmation SMS
        assert sms.send.call_count >= 1

    def test_lead_status_transitions(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        assert basic_lead.status == LeadStatus.NEW
        eng.add_lead(basic_lead)
        eng.process_due_leads()
        assert basic_lead.status == LeadStatus.NURTURING

    def test_condition_skips_step_when_false(self, engine_with_mocks, basic_lead):
        eng, sms, voice, video, calendar = engine_with_mocks
        # Use default sequence which has a condition on step 4 (index 4 = sms_followup_2, score>=30)
        basic_lead.practice_area = "family_law"
        eng.add_lead(basic_lead)
        # Force low score so condition "score >= 30" fails
        basic_lead.score = 5
        basic_lead.sequence_step = 4  # sms_followup_2 step with condition score>=30
        basic_lead.last_contacted_at = datetime.utcnow() - timedelta(hours=100)
        initial_step = basic_lead.sequence_step
        eng.process_due_leads()
        # Step should advance past the failed condition
        assert basic_lead.sequence_step > initial_step
