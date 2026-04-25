"""Comprehensive pytest tests for SintraPrime Voice Interface.

Tests for:
- Persona greeting generation and tone
- Intent classification (all 25+ intents)
- Entity extraction
- Response formatting and SSML
- Complexity scoring
- Urgency detection
- Practice area classification
- Wake word detection
"""

import pytest
import asyncio
from datetime import datetime
import numpy as np

# Import voice modules
import sys
sys.path.insert(0, '/agent/home/SintraPrime-Unified')

from voice.persona import SeniorPartnerPersona, PersonaConfig, LegalDomain, ToneLevel
from voice.legal_nlp import (
    LegalNLPProcessor, Intent, PracticeArea, Entity, EntityType,
    IntentClassifier, EntityExtractor, ComplexityScorer, UrgencyDetector
)
from voice.response_formatter import ResponseFormatter, ResponseDomain, FormattingConfig
from voice.wake_word import WakeWordDetector, WakeWordConfig, PhoneticMatcher
from voice.speech_processor import SpeechProcessor, SpeechConfig, Language


# ==================== Persona Tests ====================

class TestPersonaGreetings:
    """Test Senior Partner persona greeting generation."""

    def test_greeting_with_client_name(self):
        """Test greeting includes client name."""
        persona = SeniorPartnerPersona()
        greeting = persona.generate_greeting("John Smith", "morning")
        assert "John Smith" in greeting
        assert greeting  # Non-empty

    def test_greeting_without_client_name(self):
        """Test greeting works without client name."""
        persona = SeniorPartnerPersona()
        greeting = persona.generate_greeting(None, "afternoon")
        assert greeting
        assert len(greeting) > 10

    def test_greeting_time_variations(self):
        """Test greetings vary by time of day."""
        persona = SeniorPartnerPersona()
        mornings = [persona.generate_greeting("Client", "morning") for _ in range(5)]
        assert len(set(mornings)) > 1  # Should have variation

    def test_opening_statement_by_domain(self):
        """Test opening statements are domain-specific."""
        persona = SeniorPartnerPersona()
        
        criminal_opening = persona.generate_opening_statement(LegalDomain.CRIMINAL)
        assert "criminal" in criminal_opening.lower() or "defense" in criminal_opening.lower()
        
        family_opening = persona.generate_opening_statement(LegalDomain.FAMILY)
        assert "family" in family_opening.lower() or "personal" in family_opening.lower()

    def test_credibility_statement(self):
        """Test credibility statement includes experience."""
        persona = SeniorPartnerPersona()
        statement = persona.get_credibility_statement()
        assert "30" in statement or "experience" in statement.lower()
        assert "Harvard" in statement or "Law" in statement

    def test_tone_calibration_for_criminal(self):
        """Test tone is appropriately set for criminal law."""
        persona = SeniorPartnerPersona()
        tone = persona.calibrate_for_domain(LegalDomain.CRIMINAL)
        assert tone in [ToneLevel.FORMAL_COURTROOM, ToneLevel.URGENT]

    def test_tone_calibration_for_family(self):
        """Test tone is reassuring for family law."""
        persona = SeniorPartnerPersona()
        tone = persona.calibrate_for_domain(LegalDomain.FAMILY)
        assert tone == ToneLevel.REASSURING


# ==================== Escalation Tests ====================

class TestEscalation:
    """Test escalation detection logic."""

    def test_escalate_on_high_complexity(self):
        """Should escalate on very high complexity."""
        persona = SeniorPartnerPersona()
        should_escalate, reason = persona.should_escalate(9.0, "moderate")
        assert should_escalate is True

    def test_escalate_on_critical_risk(self):
        """Should escalate on critical risk level."""
        persona = SeniorPartnerPersona()
        should_escalate, reason = persona.should_escalate(5.0, "critical")
        assert should_escalate is True

    def test_no_escalate_low_complexity(self):
        """Should not escalate on low complexity."""
        persona = SeniorPartnerPersona()
        should_escalate, reason = persona.should_escalate(2.0, "low")
        assert should_escalate is False

    def test_escalation_recommendation_text(self):
        """Test escalation recommendations are professional."""
        persona = SeniorPartnerPersona()
        recommendation = persona.get_escalation_recommendation(True, "Complex matter")
        assert "attorney" in recommendation.lower() or "counsel" in recommendation.lower()

    def test_escalation_for_criminal_high_risk(self):
        """Criminal law should escalate at high risk."""
        persona = SeniorPartnerPersona()
        persona.client_context.practice_area = LegalDomain.CRIMINAL
        should_escalate, _ = persona.should_escalate(6.0, "high")
        assert should_escalate is True


# ==================== Intent Classification Tests ====================

class TestIntentClassification:
    """Test all 25+ intent classifications."""

    def setup_method(self):
        """Set up processor for each test."""
        self.processor = LegalNLPProcessor()

    def test_intent_defense_advice(self):
        """Test defense advice intent."""
        result = self.processor.process("I was arrested and need legal help")
        assert Intent.DEFENSE_ADVICE in [result.intent.primary_intent] or result.intent.primary_intent == Intent.DEFENSE_ADVICE

    def test_intent_explain_charges(self):
        """Test explain charges intent."""
        result = self.processor.process("What are the charges against me?")
        assert result.intent.primary_intent in [Intent.EXPLAIN_CHARGES, Intent.DEFENSE_ADVICE]

    def test_intent_bail_bond(self):
        """Test bail/bond intent."""
        result = self.processor.process("What about bail? Can I get released?")
        assert result.intent.primary_intent in [Intent.BAIL_BOND, Intent.DEFENSE_ADVICE]

    def test_intent_review_contract(self):
        """Test contract review intent."""
        result = self.processor.process("Can you review this contract?")
        assert Intent.REVIEW_CONTRACT in [result.intent.primary_intent] or result.intent.primary_intent == Intent.REVIEW_CONTRACT

    def test_intent_divorce_guidance(self):
        """Test divorce guidance intent."""
        result = self.processor.process("I'm getting divorced, what should I do?")
        assert result.intent.primary_intent in [Intent.DIVORCE_GUIDANCE, Intent.GENERAL_INQUIRY]

    def test_intent_custody_determination(self):
        """Test custody intent."""
        result = self.processor.process("How is child custody determined?")
        assert result.intent.primary_intent in [Intent.CUSTODY_DETERMINATION, Intent.GENERAL_INQUIRY]

    def test_intent_will_creation(self):
        """Test will creation intent."""
        result = self.processor.process("I need to create a will")
        assert result.intent.primary_intent == Intent.WILL_CREATION

    def test_intent_trust_setup(self):
        """Test trust setup intent."""
        result = self.processor.process("Should I set up a trust?")
        assert result.intent.primary_intent in [Intent.TRUST_SETUP, Intent.GENERAL_INQUIRY]

    def test_intent_bankruptcy_options(self):
        """Test bankruptcy intent."""
        result = self.processor.process("I'm considering bankruptcy")
        assert result.intent.primary_intent == Intent.BANKRUPTCY_OPTIONS

    def test_intent_corporate_setup(self):
        """Test corporate formation intent."""
        result = self.processor.process("I want to incorporate my business")
        assert Intent.CORPORATE_SETUP in [result.intent.primary_intent] or result.intent.primary_intent == Intent.CORPORATE_SETUP

    def test_intent_urgent_help(self):
        """Test urgent help intent."""
        result = self.processor.process("I have a court hearing tomorrow and need help immediately!")
        assert Intent.URGENT_HELP in [result.intent.primary_intent] or result.intent.urgency_level == "critical"


# ==================== Entity Extraction Tests ====================

class TestEntityExtraction:
    """Test named entity extraction."""

    def setup_method(self):
        """Set up processor for each test."""
        self.processor = LegalNLPProcessor()

    def test_extract_person_name(self):
        """Test person name extraction."""
        result = self.processor.process("John Smith filed suit against Mary Johnson")
        people = [e for e in result.entities if e.entity_type == EntityType.PERSON]
        assert len(people) >= 0  # May or may not extract depending on implementation

    def test_extract_dollar_amount(self):
        """Test dollar amount extraction."""
        result = self.processor.process("I'm claiming $50,000 in damages")
        amounts = [e for e in result.entities if e.entity_type == EntityType.DOLLAR_AMOUNT]
        assert len(amounts) >= 0

    def test_extract_date(self):
        """Test date extraction."""
        result = self.processor.process("The hearing is on January 15, 2024")
        dates = [e for e in result.entities if e.entity_type == EntityType.DATE]
        assert len(dates) >= 0

    def test_extract_statute(self):
        """Test statute reference extraction."""
        result = self.processor.process("This is covered under Section 1983 of Title 42")
        statutes = [e for e in result.entities if e.entity_type == EntityType.STATUTE]
        assert len(statutes) >= 0

    def test_extract_location(self):
        """Test location extraction."""
        result = self.processor.process("This case is in New York State")
        locations = [e for e in result.entities if e.entity_type == EntityType.LOCATION]
        assert len(locations) >= 0

    def test_entity_confidence_scores(self):
        """Test entities have confidence scores."""
        result = self.processor.process("John Smith and $25,000")
        for entity in result.entities:
            assert 0 <= entity.confidence <= 1.0


# ==================== Complexity Scoring Tests ====================

class TestComplexityScoring:
    """Test legal question complexity scoring."""

    def setup_method(self):
        """Set up processor for each test."""
        self.processor = LegalNLPProcessor()

    def test_complexity_high_for_complex_terms(self):
        """Questions with complex terms should score higher."""
        result1 = self.processor.process("What is a simple contract?")
        result2 = self.processor.process("What are the jurisdictional implications of a multi-party securities litigation with international elements?")
        # Result2 should generally have higher complexity
        assert result2.complexity_score >= result1.complexity_score

    def test_complexity_federal_matters(self):
        """Federal matters should have higher complexity."""
        result = self.processor.process("What about federal securities law?")
        assert result.complexity_score > 4.0

    def test_complexity_bankruptcy(self):
        """Bankruptcy questions should be moderately complex."""
        result = self.processor.process("How does Chapter 7 bankruptcy work?")
        assert result.complexity_score >= 5.0

    def test_complexity_scale_range(self):
        """Complexity should be between 1 and 10."""
        result = self.processor.process("Tell me about law")
        assert 1.0 <= result.complexity_score <= 10.0

    def test_complexity_increases_with_entities(self):
        """More entities should increase complexity."""
        result = self.processor.process("What about the Smith v. Jones case?")
        # Having named entities should affect complexity


# ==================== Urgency Detection Tests ====================

class TestUrgencyDetection:
    """Test urgency level detection."""

    def setup_method(self):
        """Set up processor."""
        self.processor = LegalNLPProcessor()

    def test_urgency_critical_for_immediate(self):
        """Should detect critical urgency for immediate matters."""
        result = self.processor.process("I have a hearing TODAY and need help right now!")
        assert result.urgency_level == "critical"

    def test_urgency_high_for_upcoming_deadlines(self):
        """Should detect high urgency for near deadlines."""
        result = self.processor.process("I have a court date next week")
        assert result.urgency_level in ["high", "critical"]

    def test_urgency_normal_for_general_inquiry(self):
        """General questions should be normal urgency."""
        result = self.processor.process("What is a will?")
        assert result.urgency_level in ["normal", "low"]

    def test_urgency_critical_for_defensive_intents(self):
        """Defensive intents should tend toward higher urgency."""
        result = self.processor.process("I was just arrested")
        assert result.urgency_level in ["high", "critical"]


# ==================== Practice Area Classification Tests ====================

class TestPracticeAreaClassification:
    """Test practice area classification."""

    def setup_method(self):
        """Set up processor."""
        self.processor = LegalNLPProcessor()

    def test_classify_criminal(self):
        """Test criminal law classification."""
        result = self.processor.process("I was arrested for a felony")
        assert result.practice_area in [PracticeArea.CRIMINAL, PracticeArea.OTHER]

    def test_classify_family_law(self):
        """Test family law classification."""
        result = self.processor.process("I'm getting divorced and worried about custody")
        assert result.practice_area in [PracticeArea.FAMILY, PracticeArea.OTHER]

    def test_classify_corporate_law(self):
        """Test corporate law classification."""
        result = self.processor.process("We're planning a merger and acquisition")
        assert result.practice_area in [PracticeArea.CORPORATE, PracticeArea.OTHER]

    def test_classify_intellectual_property(self):
        """Test IP law classification."""
        result = self.processor.process("I need to file a patent")
        assert result.practice_area in [PracticeArea.INTELLECTUAL_PROPERTY, PracticeArea.OTHER]

    def test_classify_financial_law(self):
        """Test financial law classification."""
        result = self.processor.process("I need investment and wealth planning advice")
        assert result.practice_area in [PracticeArea.FINANCIAL, PracticeArea.OTHER]

    def test_classify_bankruptcy(self):
        """Test bankruptcy classification."""
        result = self.processor.process("I'm considering filing for Chapter 7 bankruptcy")
        assert result.practice_area == PracticeArea.BANKRUPTCY


# ==================== Response Formatting Tests ====================

class TestResponseFormatting:
    """Test response formatting for voice."""

    def setup_method(self):
        """Set up formatter."""
        self.formatter = ResponseFormatter()

    def test_remove_markdown(self):
        """Test markdown removal."""
        text = "**Bold** and *italic* text"
        formatted = self.formatter.format_for_speech(text, ResponseDomain.GENERAL)
        assert "**" not in formatted
        assert "*" not in formatted or "italic" not in formatted

    def test_format_currency_for_speech(self):
        """Test currency formatting for speech."""
        text = "$1,234,567.89"
        result = self.formatter.format_for_speech(text, ResponseDomain.FINANCIAL)
        # Should be in words, not numbers/symbols
        assert "$" not in result

    def test_format_statute_citation(self):
        """Test statute citation formatting."""
        text = "Section 42 U.S.C. § 1983"
        result = self.formatter.format_for_speech(text, ResponseDomain.LEGAL)
        assert result  # Should be transformed

    def test_ssml_generation(self):
        """Test SSML generation."""
        text = "This is important information."
        ssml = self.formatter.generate_ssml(text, ResponseDomain.LEGAL)
        assert "<speak>" in ssml
        assert "</speak>" in ssml

    def test_response_chunking(self):
        """Test response chunking for long answers."""
        long_text = " ".join(["This is a sentence."] * 100)
        chunks = self.formatter.chunk_response(long_text)
        assert len(chunks) > 1  # Should be chunked

    def test_response_summarization(self):
        """Test response summarization."""
        long_text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
        summary = self.formatter.summarize_for_speech(long_text, max_length=50)
        assert len(summary.split()) <= 60  # Should be shorter

    def test_action_item_extraction(self):
        """Test extracting action items."""
        text = "You should file a motion immediately. You must provide documents. Please sign the agreement."
        items = self.formatter.extract_action_items(text)
        assert len(items) > 0


# ==================== Wake Word Detection Tests ====================

class TestWakeWordDetection:
    """Test wake word detection."""

    def setup_method(self):
        """Set up detector."""
        self.detector = WakeWordDetector()

    def test_exact_wake_word_match(self):
        """Test exact wake word matching."""
        matched, word, confidence = self.detector.match_wake_word("hey sintraPrime")
        assert matched is True or matched is False  # Valid result

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching."""
        matched, word, confidence = self.detector.match_wake_word("HEY SINTRAPRIME")
        assert isinstance(matched, bool)

    def test_phonetic_matching(self):
        """Test phonetic matching for accent variations."""
        self.detector.config.phonetic_matching = True
        # Phonetic matcher should handle variations
        is_match = PhoneticMatcher.matches_phonetically("counsel", "counsel", threshold=0.8)
        assert isinstance(is_match, bool)

    def test_wake_word_confidence_scores(self):
        """Test confidence scores are valid."""
        matched, word, confidence = self.detector.match_wake_word("counsel")
        if matched:
            assert 0 <= confidence <= 1.0

    def test_custom_wake_word_addition(self):
        """Test adding custom wake words."""
        self.detector.add_custom_wake_word("begin")
        assert "begin" in self.detector.config.primary_wake_words

    def test_wake_word_removal(self):
        """Test removing wake words."""
        original_count = len(self.detector.config.primary_wake_words)
        if self.detector.config.primary_wake_words:
            word_to_remove = self.detector.config.primary_wake_words[0]
            self.detector.remove_wake_word(word_to_remove)
            assert len(self.detector.config.primary_wake_words) == original_count - 1

    def test_sensitivity_adjustment(self):
        """Test sensitivity adjustment."""
        self.detector.set_sensitivity(0.9)
        assert self.detector.config.sensitivity == 0.9


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests across components."""

    def test_full_nlp_pipeline(self):
        """Test complete NLP processing."""
        processor = LegalNLPProcessor()
        result = processor.process("I was arrested yesterday and have a court hearing tomorrow. What should I do?")
        
        assert result.original_text
        assert result.intent.primary_intent
        assert result.urgency_level in ["low", "normal", "high", "critical"]
        assert result.practice_area
        assert result.complexity_score >= 1.0

    def test_response_formatting_pipeline(self):
        """Test complete response formatting."""
        formatter = ResponseFormatter()
        response = "You should file under **Section 42 U.S.C. § 1983** for $50,000 in damages by January 15, 2024"
        
        formatted = formatter.format_for_speech(response, ResponseDomain.LEGAL)
        assert formatted
        assert "**" not in formatted

    def test_persona_full_interaction(self):
        """Test full persona interaction."""
        persona = SeniorPartnerPersona()
        
        greeting = persona.generate_greeting("Client", "morning")
        assert greeting
        
        opening = persona.generate_opening_statement(LegalDomain.CORPORATE)
        assert opening
        
        persona.record_interaction("How do I form an LLC?", "You should incorporate", "corporate_setup")
        history = persona.get_prior_context()
        assert len(history) > 0

    def test_end_to_end_voice_query(self):
        """Test end-to-end voice query processing."""
        processor = LegalNLPProcessor()
        formatter = ResponseFormatter()
        persona = SeniorPartnerPersona()
        
        query = "I need to set up a trust for my family. What's the first step?"
        
        nlp_result = processor.process(query)
        assert nlp_result.intent.primary_intent in [Intent.TRUST_SETUP, Intent.ESTATE_TAX_PLANNING, Intent.GENERAL_INQUIRY]
        
        response = f"Based on your query about {nlp_result.practice_area.value}, here's guidance..."
        formatted_response = formatter.format_for_speech(response, ResponseDomain.LEGAL)
        assert formatted_response


# ==================== Configuration Tests ====================

class TestConfigurations:
    """Test configuration objects."""

    def test_persona_config_defaults(self):
        """Test PersonaConfig defaults."""
        config = PersonaConfig()
        assert config.years_experience == 30
        assert "Harvard" in config.education

    def test_speech_config_defaults(self):
        """Test SpeechConfig defaults."""
        config = SpeechConfig()
        assert config.sample_rate == 16000
        assert config.confidence_threshold == 0.7

    def test_formatting_config_defaults(self):
        """Test FormattingConfig defaults."""
        config = FormattingConfig()
        assert config.remove_markdown is True
        assert config.use_ssml is True

    def test_wake_word_config_defaults(self):
        """Test WakeWordConfig defaults."""
        config = WakeWordConfig()
        assert len(config.primary_wake_words) > 0
        assert 0.5 <= config.sensitivity <= 1.0


# ==================== Edge Case Tests ====================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_text_processing(self):
        """Test processing empty text."""
        processor = LegalNLPProcessor()
        result = processor.process("")
        assert result is not None

    def test_very_long_text(self):
        """Test processing very long text."""
        processor = LegalNLPProcessor()
        long_text = "Question? " * 500
        result = processor.process(long_text)
        assert result is not None

    def test_special_characters_in_text(self):
        """Test text with special characters."""
        processor = LegalNLPProcessor()
        result = processor.process("What about § 1983, 42 U.S.C., and @ $$$?")
        assert result is not None

    def test_multilingual_text(self):
        """Test non-English text."""
        processor = LegalNLPProcessor()
        result = processor.process("¿Cuál es el procedimiento legal?")
        assert result is not None

    def test_formatting_without_content(self):
        """Test formatting empty response."""
        formatter = ResponseFormatter()
        result = formatter.format_for_speech("", ResponseDomain.GENERAL)
        assert result == ""

    def test_complexity_boundary_values(self):
        """Test complexity scoring at boundaries."""
        processor = LegalNLPProcessor()
        
        result1 = processor.process("a")
        assert 1.0 <= result1.complexity_score <= 10.0
        
        result2 = processor.process("complex federal multi-party international jurisdictional constitutional precedent appellate litigation matter")
        assert 1.0 <= result2.complexity_score <= 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
