"""SintraPrime AI Voice Interface — Senior Partner Persona

A complete voice interface system that gives SintraPrime a conversational
"Senior Partner" persona. Users can speak to the system and receive
structured legal and financial guidance with professional voice output.

Key Components:
- VoiceEngine: Async voice processing with streaming support
- SeniorPartnerPersona: AI persona with 30 years of legal expertise
- SpeechProcessor: Multi-provider STT/TTS with fallbacks
- LegalNLPProcessor: Intent classification and entity extraction
- ResponseFormatter: Converts text responses for natural voice delivery
"""

from .voice_engine import VoiceEngine, VoiceConfig, SessionManager
from .persona import SeniorPartnerPersona, PersonaConfig
from .speech_processor import SpeechProcessor, SpeechConfig, TranscriptionResult
from .legal_nlp import LegalNLPProcessor, NLPResult, IntentResult
from .response_formatter import ResponseFormatter, FormattingConfig
from .wake_word import WakeWordDetector, WakeWordConfig

__all__ = [
    'VoiceEngine',
    'VoiceConfig',
    'SessionManager',
    'SeniorPartnerPersona',
    'PersonaConfig',
    'SpeechProcessor',
    'SpeechConfig',
    'TranscriptionResult',
    'LegalNLPProcessor',
    'NLPResult',
    'IntentResult',
    'ResponseFormatter',
    'FormattingConfig',
    'WakeWordDetector',
    'WakeWordConfig',
]

__version__ = '1.0.0'
__author__ = 'SintraPrime Legal Technology'
