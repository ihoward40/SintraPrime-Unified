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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .legal_nlp import IntentResult, LegalNLPProcessor, NLPResult
    from .persona import PersonaConfig, SeniorPartnerPersona
    from .response_formatter import FormattingConfig, ResponseFormatter
    from .speech_processor import SpeechConfig, SpeechProcessor, TranscriptionResult
    from .voice_engine import SessionManager, VoiceConfig, VoiceEngine
    from .wake_word import WakeWordConfig, WakeWordDetector

_LAZY_EXPORTS = {
    'VoiceEngine': ('.voice_engine', 'VoiceEngine'),
    'VoiceConfig': ('.voice_engine', 'VoiceConfig'),
    'SessionManager': ('.voice_engine', 'SessionManager'),
    'SeniorPartnerPersona': ('.persona', 'SeniorPartnerPersona'),
    'PersonaConfig': ('.persona', 'PersonaConfig'),
    'SpeechProcessor': ('.speech_processor', 'SpeechProcessor'),
    'SpeechConfig': ('.speech_processor', 'SpeechConfig'),
    'TranscriptionResult': ('.speech_processor', 'TranscriptionResult'),
    'LegalNLPProcessor': ('.legal_nlp', 'LegalNLPProcessor'),
    'NLPResult': ('.legal_nlp', 'NLPResult'),
    'IntentResult': ('.legal_nlp', 'IntentResult'),
    'ResponseFormatter': ('.response_formatter', 'ResponseFormatter'),
    'FormattingConfig': ('.response_formatter', 'FormattingConfig'),
    'WakeWordDetector': ('.wake_word', 'WakeWordDetector'),
    'WakeWordConfig': ('.wake_word', 'WakeWordConfig'),
}


def __getattr__(name):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value

__all__ = [
    'FormattingConfig',
    'IntentResult',
    'LegalNLPProcessor',
    'NLPResult',
    'PersonaConfig',
    'ResponseFormatter',
    'SeniorPartnerPersona',
    'SessionManager',
    'SpeechConfig',
    'SpeechProcessor',
    'TranscriptionResult',
    'VoiceConfig',
    'VoiceEngine',
    'WakeWordConfig',
    'WakeWordDetector',
]

__version__ = '1.0.0'
__author__ = 'SintraPrime Legal Technology'
