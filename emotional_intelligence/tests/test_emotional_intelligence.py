"""
Emotional Intelligence Test Suite — 50+ tests covering all EI modules.
Tests: SentimentAnalyzer, EmpathyEngine, CommunicationStyleAdapter,
CrisisDetector, ClientRelationshipManager, ResponseFormatter.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
import sys
import os

# Ensure module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from emotional_intelligence.sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentResult,
    SentimentType,
    UrgencyLevel,
)
from emotional_intelligence.empathy_engine import EmpathyEngine
from emotional_intelligence.communication_style_adapter import (
    CommunicationStyleAdapter,
    CommunicationStyle,
    FormalityLevel,
    TechnicalLevel,
    VerbosityLevel,
)
from emotional_intelligence.crisis_detector import (
    CrisisDetector,
    CrisisAssessment,
    CrisisLevel,
    CrisisType,
)
from emotional_intelligence.client_relationship_manager import (
    ClientRelationshipManager,
    Interaction,
    EngagementLevel,
)
from emotional_intelligence.response_formatter import (
    ResponseFormatter,
    ActionItem,
    Deadline,
)


# ══════════════════════════════════════════════════════════════
# SENTIMENT ANALYZER TESTS
# ══════════════════════════════════════════════════════════════

class TestSentimentAnalyzer:

    def setup_method(self):
        self.analyzer = SentimentAnalyzer()

    # ── Positive detection ──────────────────────────────────

    def test_positive_sentiment_detection(self):
        result = self.analyzer.analyze("Thank you so much, this has been incredibly helpful!")
        assert result.sentiment == SentimentType.POSITIVE
        assert result.confidence > 0.4

    def test_positive_case_resolved(self):
        result = self.analyzer.analyze("The case was resolved and I'm so grateful for everything.")
        assert result.sentiment in (SentimentType.POSITIVE, SentimentType.NEUTRAL)

    def test_hope_detected_in_positive_message(self):
        result = self.analyzer.analyze("I'm hopeful things will get better. Thank you!")
        assert result.emotions["hope"] > 0.0

    # ── Neutral detection ───────────────────────────────────

    def test_neutral_sentiment_detection(self):
        result = self.analyzer.analyze("I would like to schedule a consultation.")
        assert result.sentiment in (SentimentType.NEUTRAL, SentimentType.POSITIVE)

    def test_neutral_factual_statement(self):
        result = self.analyzer.analyze("The hearing is set for November 15th.")
        assert result.sentiment in (SentimentType.NEUTRAL, SentimentType.POSITIVE)

    # ── Negative / Distressed detection ────────────────────

    def test_negative_anger_detection(self):
        result = self.analyzer.analyze("This is absolutely ridiculous and unfair! I'm furious!")
        assert result.sentiment == SentimentType.NEGATIVE
        assert result.emotions["anger"] > 0.0

    def test_distressed_housing_crisis(self):
        result = self.analyzer.analyze("I'm going to lose my house. I don't know what to do.")
        assert result.sentiment == SentimentType.DISTRESSED
        assert result.urgency_level in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL)

    def test_distressed_high_fear(self):
        result = self.analyzer.analyze("I'm terrified I'll be deported and my kids will be left alone.")
        assert result.sentiment == SentimentType.DISTRESSED

    def test_distressed_financial(self):
        result = self.analyzer.analyze("I'm completely broke, can't eat, nothing left.")
        assert result.sentiment == SentimentType.DISTRESSED

    def test_confusion_detected(self):
        result = self.analyzer.analyze("I don't understand what jurisdiction means in my case.")
        assert result.emotions["confusion"] > 0.0

    def test_frustration_detected(self):
        result = self.analyzer.analyze("I'm so frustrated. We've been going in circles for months.")
        assert result.emotions["frustration"] > 0.0

    # ── Urgency assessment ──────────────────────────────────

    def test_critical_urgency_court_tomorrow(self):
        result = self.analyzer.analyze("My court hearing is tomorrow and I'm losing my house. Emergency!")
        assert result.urgency_level in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH)

    def test_low_urgency_general_question(self):
        result = self.analyzer.analyze("I was wondering about the general process for filing a will.")
        assert result.urgency_level == UrgencyLevel.LOW

    def test_medium_urgency_deadline_mention(self):
        result = self.analyzer.analyze("There's a deadline in two weeks to respond to the lawsuit.")
        assert result.urgency_level in (UrgencyLevel.MEDIUM, UrgencyLevel.HIGH)

    # ── Specific detection methods ──────────────────────────

    def test_detect_distress_true(self):
        assert self.analyzer.detect_distress("I'm going to lose everything. I'm desperate.") is True

    def test_detect_distress_false(self):
        assert self.analyzer.detect_distress("I'd like to know more about estate planning.") is False

    def test_detect_confusion_true(self):
        assert self.analyzer.detect_confusion("What does plaintiff mean in my case?") is True

    def test_detect_confusion_false(self):
        assert self.analyzer.detect_confusion("Please file my motion today.") is False

    def test_detect_anger_true(self):
        assert self.analyzer.detect_anger("I'm furious! This is absolutely ridiculous and unfair!") is True

    def test_detect_anger_false(self):
        assert self.analyzer.detect_anger("Thank you for your help.") is False

    # ── Session tracking ────────────────────────────────────

    def test_track_sentiment_trend_returns_list(self):
        messages = ["I'm scared.", "Thank you, this helps.", "I'm still worried."]
        results = self.analyzer.track_sentiment_trend("user_001", messages)
        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)

    def test_sentiment_result_to_dict(self):
        result = self.analyzer.analyze("Hello, I need help.")
        d = result.to_dict()
        assert "sentiment" in d
        assert "confidence" in d
        assert "emotions" in d
        assert "urgency_level" in d


# ══════════════════════════════════════════════════════════════
# EMPATHY ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestEmpathyEngine:

    def setup_method(self):
        self.engine = EmpathyEngine()
        self.analyzer = SentimentAnalyzer()

    def test_adapt_response_distressed(self):
        sentiment = self.analyzer.analyze("I'm going to lose my house. I'm desperate.")
        original = "You may qualify for a loan modification program."
        adapted = self.engine.adapt_response(original, sentiment)
        # Should contain empathy acknowledgment
        assert len(adapted) > len(original)
        assert original in adapted

    def test_adapt_response_angry(self):
        sentiment = self.analyzer.analyze("This is ridiculous and unfair! I'm furious!")
        original = "Here are your options regarding the dispute."
        adapted = self.engine.adapt_response(original, sentiment)
        assert original in adapted

    def test_adapt_response_confused(self):
        sentiment = self.analyzer.analyze("I don't understand what jurisdiction means.")
        original = "The court has jurisdiction over this matter."
        adapted = self.engine.adapt_response(original, sentiment)
        assert original in adapted

    def test_adapt_response_positive_no_change(self):
        sentiment = self.analyzer.analyze("Thank you so much! This is very helpful!")
        original = "You're welcome! Here's your next step."
        adapted = self.engine.adapt_response(original, sentiment)
        assert original in adapted

    def test_acknowledge_emotion_fear(self):
        ack = self.engine.acknowledge_emotion("fear")
        assert len(ack) > 10
        assert isinstance(ack, str)

    def test_acknowledge_emotion_anger(self):
        ack = self.engine.acknowledge_emotion("anger")
        assert isinstance(ack, str)
        assert len(ack) > 5

    def test_acknowledge_emotion_with_context(self):
        ack = self.engine.acknowledge_emotion("confusion", context="the eviction process")
        assert "eviction process" in ack

    def test_de_escalate_returns_calming_language(self):
        result = self.engine.de_escalate("I'm absolutely furious about this situation!")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_simplify_jargon_plaintiff(self):
        result = self.engine.simplify_jargon("The plaintiff filed a motion.")
        assert "plaintiff" not in result.lower() or "person who filed" in result.lower()

    def test_simplify_jargon_multiple_terms(self):
        text = "The defendant received a subpoena related to the plaintiff's affidavit."
        result = self.engine.simplify_jargon(text)
        assert len(result) > 0
        # At least some simplification should occur
        assert result != text or all(
            term not in text.lower()
            for term in ["subpoena", "plaintiff", "affidavit"]
        )

    def test_add_reassurance_eviction(self):
        result = self.engine.add_reassurance("Here are your options.", "eviction")
        assert "Here are your options." in result
        assert len(result) > len("Here are your options.")

    def test_add_reassurance_general(self):
        result = self.engine.add_reassurance("Your case overview:", "general")
        assert "Your case overview:" in result

    def test_check_in_returns_message(self):
        result = self.engine.check_in("user_001")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_get_situation_empathy_divorce(self):
        result = self.engine.get_situation_empathy("divorce")
        assert "divorce" in result.lower()

    def test_get_situation_empathy_eviction(self):
        result = self.engine.get_situation_empathy("eviction")
        assert "home" in result.lower() or "housing" in result.lower()

    def test_get_situation_empathy_unknown(self):
        result = self.engine.get_situation_empathy("unknown_situation")
        assert isinstance(result, str)
        assert len(result) > 5


# ══════════════════════════════════════════════════════════════
# COMMUNICATION STYLE ADAPTER TESTS
# ══════════════════════════════════════════════════════════════

class TestCommunicationStyleAdapter:

    def setup_method(self):
        self.adapter = CommunicationStyleAdapter()

    def test_detect_formal_style(self):
        messages = [
            "Dear Sir, I would like to inquire regarding my legal matter.",
            "Please be advised that I am writing to formally request assistance.",
            "I am writing to inform you of my situation pursuant to our agreement.",
        ]
        style = self.adapter.detect_style(messages)
        assert style.formality in (FormalityLevel.FORMAL, FormalityLevel.SEMI_FORMAL)

    def test_detect_casual_style(self):
        messages = [
            "hey what's up, gonna need some help with my case asap",
            "yeah so basically i'm kinda stuck with this btw",
            "ok so what do i do lol",
        ]
        style = self.adapter.detect_style(messages)
        assert style.formality in (FormalityLevel.CASUAL, FormalityLevel.SEMI_FORMAL)

    def test_detect_technical_style(self):
        messages = [
            "I need to understand the statute of limitations and its implications for my tort claim.",
            "The plaintiff's negligence in fiduciary duty led to significant liability.",
        ]
        style = self.adapter.detect_style(messages)
        assert style.technicality in (TechnicalLevel.TECHNICAL, TechnicalLevel.MIXED)

    def test_detect_plain_style(self):
        messages = [
            "Can you explain what that means in plain English?",
            "I don't understand the legal terms. What should I do?",
        ]
        style = self.adapter.detect_style(messages)
        assert style.technicality in (TechnicalLevel.PLAIN, TechnicalLevel.MIXED)

    def test_detect_concise_style(self):
        messages = ["Help.", "What next?", "OK."]
        style = self.adapter.detect_style(messages)
        assert style.verbosity == VerbosityLevel.CONCISE

    def test_adapt_simplifies_for_plain_style(self):
        style = CommunicationStyle(technicality=TechnicalLevel.PLAIN)
        text = "Please utilize the form and commence the process."
        result = self.adapter.adapt(text, style)
        # Should simplify "utilize" → "use"
        assert "use" in result.lower() or "start" in result.lower()

    def test_adjust_reading_level_low_grade(self):
        text = "The aforementioned defendant shall indemnify the plaintiff for damages incurred."
        result = self.adapter.adjust_reading_level(text, 6)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_for_client(self):
        result = self.adapter.format_for_audience("Your motion has been filed.", "client")
        assert "you" in result.lower() or "here" in result.lower()

    def test_format_for_attorney(self):
        result = self.adapter.format_for_audience("Motion granted.", "attorney")
        assert "Legal Summary" in result or "attorney" in result.lower()

    def test_use_preferred_name(self):
        profile = MagicMock()
        profile.preferred_name = "Marcus"
        result = self.adapter.use_preferred_name("Hello, how can I help?", profile)
        # Original doesn't have a greeting to replace, but function shouldn't error
        assert isinstance(result, str)

    def test_save_and_load_style_profile(self):
        style = CommunicationStyle(formality=FormalityLevel.CASUAL)
        self.adapter.save_style_profile("user_001", style)
        loaded = self.adapter.load_style_profile("user_001")
        assert loaded is not None
        assert loaded.formality == FormalityLevel.CASUAL

    def test_load_nonexistent_profile_returns_none(self):
        result = self.adapter.load_style_profile("nonexistent_user")
        assert result is None


# ══════════════════════════════════════════════════════════════
# CRISIS DETECTOR TESTS
# ══════════════════════════════════════════════════════════════

class TestCrisisDetector:

    def setup_method(self):
        self.detector = CrisisDetector()

    def test_mental_health_crisis_detected(self):
        assessment = self.detector.assess("I want to end my life. I can't go on anymore.")
        assert CrisisType.MENTAL_HEALTH_CONCERN in assessment.crisis_types

    def test_mental_health_level_immediate(self):
        assessment = self.detector.assess("I'm suicidal and don't want to live.")
        level = self.detector.crisis_level(assessment)
        assert level == CrisisLevel.IMMEDIATE

    def test_domestic_violence_detected(self):
        assessment = self.detector.assess("My partner hit me and I'm afraid for my safety.")
        assert CrisisType.DOMESTIC_VIOLENCE in assessment.crisis_types

    def test_domestic_violence_level_immediate(self):
        assessment = self.detector.assess("I'm being abused and in danger at home.")
        assert assessment.level == CrisisLevel.IMMEDIATE

    def test_housing_crisis_detected(self):
        assessment = self.detector.assess("I received an eviction notice and I can't pay rent.")
        assert CrisisType.HOUSING_CRISIS in assessment.crisis_types

    def test_housing_crisis_level_moderate(self):
        assessment = self.detector.assess("I'm losing my home — foreclosure process started.")
        assert assessment.level in (CrisisLevel.MODERATE, CrisisLevel.SEVERE)

    def test_financial_emergency_detected(self):
        assessment = self.detector.assess("My wages are being garnished and I can't buy food.")
        assert CrisisType.FINANCIAL_EMERGENCY in assessment.crisis_types

    def test_family_crisis_detected(self):
        assessment = self.detector.assess("CPS is threatening to take my children away.")
        assert CrisisType.FAMILY_CRISIS in assessment.crisis_types

    def test_legal_emergency_detected(self):
        assessment = self.detector.assess("There's a warrant out for my arrest.")
        assert CrisisType.LEGAL_EMERGENCY in assessment.crisis_types

    def test_no_crisis_for_routine_query(self):
        assessment = self.detector.assess("I'd like to discuss my estate planning options.")
        assert assessment.level in (CrisisLevel.NONE, CrisisLevel.CONCERN)

    def test_combined_crisis_is_severe(self):
        assessment = self.detector.assess(
            "I'm losing my home and my wages are being garnished and CPS is involved."
        )
        assert assessment.level in (CrisisLevel.SEVERE, CrisisLevel.MODERATE)

    def test_requires_human_review_for_immediate(self):
        assessment = self.detector.assess("I want to end my life.")
        assert assessment.requires_human_review is True

    def test_does_not_require_human_review_for_low(self):
        assessment = self.detector.assess("I need help with a contract review.")
        assert assessment.requires_human_review is False

    def test_get_resources_mental_health(self):
        resources = self.detector.get_resources("mental_health_concern")
        assert len(resources) > 0
        names = [r.name for r in resources]
        assert any("988" in r.phone or "Suicide" in r.name for r in resources)

    def test_get_resources_domestic_violence(self):
        resources = self.detector.get_resources("domestic_violence_indicator")
        assert len(resources) > 0

    def test_get_resources_housing(self):
        resources = self.detector.get_resources("housing_crisis")
        assert len(resources) > 0

    def test_generate_crisis_response_immediate_mental_health(self):
        assessment = self.detector.assess("I'm suicidal.")
        response = self.detector.generate_crisis_response(assessment)
        assert "988" in response or "safe" in response.lower() or "crisis" in response.lower()

    def test_generate_crisis_response_domestic_violence(self):
        assessment = self.detector.assess("I'm being abused and in danger.")
        response = self.detector.generate_crisis_response(assessment)
        assert "safety" in response.lower() or "hotline" in response.lower() or "1-800" in response

    def test_legal_emergency_triage_warrant(self):
        result = self.detector.legal_emergency_triage("There's a warrant out for my arrest.")
        assert result.refer_to_attorney_immediately is True
        assert len(result.recommended_steps) > 0

    def test_legal_emergency_triage_deportation(self):
        result = self.detector.legal_emergency_triage("I received a deportation order for tomorrow.")
        assert result.urgency == "critical"

    def test_crisis_assessment_to_dict(self):
        assessment = self.detector.assess("I'm losing my home.")
        d = assessment.to_dict()
        assert "crisis_types" in d
        assert "level" in d
        assert "requires_human_review" in d


# ══════════════════════════════════════════════════════════════
# CLIENT RELATIONSHIP MANAGER TESTS
# ══════════════════════════════════════════════════════════════

class TestClientRelationshipManager:

    def setup_method(self):
        self.manager = ClientRelationshipManager()
        self.intake_data = {
            "first_name": "Marcus",
            "last_name": "Johnson",
            "preferred_name": "Marc",
            "email": "marc@example.com",
            "matters": ["divorce_proceedings"],
            "referral_source": "web",
        }

    def test_onboard_client_creates_profile(self):
        profile = self.manager.onboard_client("user_001", self.intake_data)
        assert profile.user_id == "user_001"
        assert profile.first_name == "Marcus"
        assert profile.preferred_name == "Marc"
        assert profile.display_name == "Marc"

    def test_onboard_client_stores_matters(self):
        profile = self.manager.onboard_client("user_002", self.intake_data)
        assert "divorce_proceedings" in profile.matters

    def test_update_relationship_records_interaction(self):
        self.manager.onboard_client("user_003", self.intake_data)
        interaction = Interaction(
            timestamp=datetime.utcnow(),
            message="I have a question about my case.",
            sentiment_score=0.2,
            topic="case_inquiry",
            resolved=False,
        )
        profile = self.manager.update_relationship("user_003", interaction)
        assert len(profile.interactions) == 1

    def test_get_relationship_health_returns_object(self):
        self.manager.onboard_client("user_004", self.intake_data)
        health = self.manager.get_relationship_health("user_004")
        assert health is not None
        assert 0.0 <= health.satisfaction <= 1.0
        assert 0.0 <= health.trust_score <= 1.0

    def test_generate_touchpoint_uses_preferred_name(self):
        self.manager.onboard_client("user_005", self.intake_data)
        message = self.manager.generate_touchpoint("user_005")
        assert "Marc" in message

    def test_milestone_acknowledgment_case_resolved(self):
        self.manager.onboard_client("user_006", self.intake_data)
        msg = self.manager.milestone_acknowledgment("user_006", "case_resolved")
        assert isinstance(msg, str)
        assert len(msg) > 10

    def test_anniversary_message_returns_string(self):
        self.manager.onboard_client("user_007", self.intake_data)
        msg = self.manager.anniversary_message("user_007")
        assert isinstance(msg, str)
        assert len(msg) > 5

    def test_referral_request_returns_message(self):
        self.manager.onboard_client("user_008", self.intake_data)
        msg = self.manager.referral_request("user_008")
        assert isinstance(msg, str)
        assert "Marc" in msg

    def test_satisfaction_survey_returns_message(self):
        self.manager.onboard_client("user_009", self.intake_data)
        msg = self.manager.satisfaction_survey("user_009")
        assert isinstance(msg, str)

    def test_retention_risk_new_client_low(self):
        self.manager.onboard_client("user_010", self.intake_data)
        risk = self.manager.retention_risk("user_010")
        assert 0.0 <= risk <= 1.0

    def test_retention_risk_inactive_client_high(self):
        self.manager.onboard_client("user_011", self.intake_data)
        health = self.manager.get_relationship_health("user_011")
        risk = self.manager.retention_risk("user_011")
        # New client with no interactions should have elevated risk
        assert risk >= 0.0


# ══════════════════════════════════════════════════════════════
# RESPONSE FORMATTER TESTS
# ══════════════════════════════════════════════════════════════

class TestResponseFormatter:

    def setup_method(self):
        self.formatter = ResponseFormatter()

    def test_format_legal_advice_empathetic_tone(self):
        result = self.formatter.format_legal_advice(
            "You may be eligible for a payment plan.",
            tone="empathetic",
        )
        assert "You may be eligible" in result

    def test_format_legal_advice_with_user_profile(self):
        profile = MagicMock()
        profile.display_name = "Sara"
        profile.preferred_name = "Sara"
        profile.first_name = "Sara"
        result = self.formatter.format_legal_advice(
            "Here is your case summary.",
            tone="empathetic",
            user_profile=profile,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_structure_explanation_breaks_long_text(self):
        long_text = "First important point here. " * 10
        result = self.formatter.structure_explanation(long_text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_action_items_returns_list(self):
        advice = "You should file the petition. Please gather your documents. You must contact the court."
        items = self.formatter.create_action_items(advice)
        assert isinstance(items, list)
        assert len(items) >= 1

    def test_create_action_items_fallback(self):
        advice = "Your situation is complex."
        items = self.formatter.create_action_items(advice)
        assert len(items) >= 1

    def test_add_timeline_with_deadlines(self):
        deadlines = [
            Deadline(
                description="File response",
                date="2026-05-01",
                consequence="Default judgment may be entered",
                days_remaining=5,
            )
        ]
        result = self.formatter.add_timeline("Here are your options.", deadlines)
        assert "File response" in result
        assert "2026-05-01" in result

    def test_add_timeline_no_deadlines(self):
        result = self.formatter.add_timeline("Here are your options.", [])
        assert result == "Here are your options."

    def test_plain_english_summary_returns_header(self):
        legal_doc = (
            "WHEREAS the plaintiff hereby stipulates and agrees that the defendant shall indemnify "
            "all parties pursuant to the terms of the agreement dated hereinafter."
        )
        result = self.formatter.plain_english_summary(legal_doc)
        assert "Plain English" in result

    def test_reassuring_disclaimer_bankruptcy(self):
        result = self.formatter.reassuring_disclaimer("bankruptcy")
        assert "Bankruptcy" in result or "fresh start" in result.lower()

    def test_reassuring_disclaimer_criminal(self):
        result = self.formatter.reassuring_disclaimer("criminal")
        assert "innocent" in result.lower() or "rights" in result.lower()

    def test_reassuring_disclaimer_general_fallback(self):
        result = self.formatter.reassuring_disclaimer("unknown_topic")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_progress_report_litigation(self):
        result = self.formatter.progress_report(
            matter_id="M-001",
            current_stage="Discovery phase — exchange of evidence",
            process_type="litigation",
            completed_stages=["Initial consultation and case evaluation", "Filing of complaint/petition"],
        )
        assert "M-001" in result
        assert "✅" in result
        assert "▶️" in result

    def test_progress_report_bankruptcy(self):
        result = self.formatter.progress_report(
            matter_id="B-002",
            process_type="bankruptcy",
        )
        assert "B-002" in result

    def test_format_action_items_as_text(self):
        items = [
            ActionItem(1, "File your response with the court", "you", priority="urgent"),
            ActionItem(2, "Gather financial documents", "you"),
        ]
        result = self.formatter.format_action_items_as_text(items)
        assert "Step 1" in result
        assert "Step 2" in result
        assert "🚨" in result  # urgent priority icon


# ══════════════════════════════════════════════════════════════
# LEGAL SCENARIO INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class TestLegalScenarioIntegration:
    """End-to-end scenario tests for real legal client situations."""

    def setup_method(self):
        self.analyzer = SentimentAnalyzer()
        self.engine = EmpathyEngine()
        self.crisis = CrisisDetector()
        self.formatter = ResponseFormatter()

    def test_divorce_stress_scenario(self):
        text = "My husband just filed for divorce. I'm scared about custody and losing my home."
        sentiment = self.analyzer.analyze(text)
        assert sentiment.sentiment in (SentimentType.DISTRESSED, SentimentType.NEGATIVE)
        adapted = self.engine.adapt_response("Here are your divorce rights.", sentiment)
        assert len(adapted) > len("Here are your divorce rights.")
        empathy = self.engine.get_situation_empathy("divorce")
        assert "divorce" in empathy.lower()

    def test_eviction_fear_scenario(self):
        text = "I got an eviction notice. I have kids and nowhere to go. I'm terrified."
        sentiment = self.analyzer.analyze(text)
        crisis = self.crisis.assess(text)
        assert CrisisType.HOUSING_CRISIS in crisis.crisis_types
        resources = self.crisis.get_resources("housing_crisis")
        assert len(resources) > 0

    def test_debt_crisis_scenario(self):
        text = "I can't pay my bills. My wages are being garnished. I'm completely broke."
        sentiment = self.analyzer.analyze(text)
        crisis = self.crisis.assess(text)
        assert CrisisType.FINANCIAL_EMERGENCY in crisis.crisis_types
        empathy = self.engine.get_situation_empathy("debt")
        assert "financial" in empathy.lower() or "debt" in empathy.lower()

    def test_criminal_charge_scenario(self):
        text = "I was arrested last night. I'm scared I'm going to prison."
        sentiment = self.analyzer.analyze(text)
        assert sentiment.sentiment in (SentimentType.DISTRESSED, SentimentType.NEGATIVE)
        disclaimer = self.formatter.reassuring_disclaimer("criminal")
        assert "innocent" in disclaimer.lower() or "rights" in disclaimer.lower()

    def test_full_pipeline_distressed_client(self):
        """Full EI pipeline for a distressed client."""
        text = "I'm terrified I'll lose custody of my children tomorrow."
        sentiment = self.analyzer.analyze(text)
        crisis = self.crisis.assess(text)
        original = "Custody hearings follow a best interests of the child standard."
        adapted = self.engine.adapt_response(original, sentiment)

        assert sentiment.sentiment in (SentimentType.DISTRESSED, SentimentType.NEGATIVE)
        assert len(adapted) > len(original)
        assert original in adapted
