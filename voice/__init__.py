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
- LocalVoice: Fully local voice pipeline (enrollment, TTS, transcription,
  dictation, dubbing) with provider-agnostic backend interfaces
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .legal_nlp import IntentResult, LegalNLPProcessor, NLPResult
    from .local_voice import (
        DictationSessionManager,
        DubbingJob,
        DubbingRenderPlan,
        LocalCapability,
        LocalTTSConfig,
        LocalTTSResult,
        LocalTranscriptionResult,
        LocalVoiceBackend,
        LocalVoiceError,
        LocalVoicePipeline,
        LocalVoiceProfile,
        LocalVoiceRegistry,
        ModelNotAvailableError,
        NullLocalVoiceBackend,
        VoiceDesignSpec,
        VoiceEnrollmentManager,
        VoiceProfileNotFoundError,
        VoiceSample,
        build_dubbing_plan,
        create_local_voice_pipeline,
    )
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
    'LocalVoicePipeline': ('.local_voice', 'LocalVoicePipeline'),
    'LocalVoiceBackend': ('.local_voice', 'LocalVoiceBackend'),
    'NullLocalVoiceBackend': ('.local_voice', 'NullLocalVoiceBackend'),
    'LocalVoiceRegistry': ('.local_voice', 'LocalVoiceRegistry'),
    'LocalVoiceProfile': ('.local_voice', 'LocalVoiceProfile'),
    'LocalVoiceError': ('.local_voice', 'LocalVoiceError'),
    'LocalCapability': ('.local_voice', 'LocalCapability'),
    'LocalTTSConfig': ('.local_voice', 'LocalTTSConfig'),
    'LocalTTSResult': ('.local_voice', 'LocalTTSResult'),
    'LocalTranscriptionResult': ('.local_voice', 'LocalTranscriptionResult'),
    'VoiceSample': ('.local_voice', 'VoiceSample'),
    'VoiceDesignSpec': ('.local_voice', 'VoiceDesignSpec'),
    'VoiceEnrollmentManager': ('.local_voice', 'VoiceEnrollmentManager'),
    'VoiceProfileNotFoundError': ('.local_voice', 'VoiceProfileNotFoundError'),
    'ModelNotAvailableError': ('.local_voice', 'ModelNotAvailableError'),
    'DictationSessionManager': ('.local_voice', 'DictationSessionManager'),
    'DubbingJob': ('.local_voice', 'DubbingJob'),
    'DubbingRenderPlan': ('.local_voice', 'DubbingRenderPlan'),
    'build_dubbing_plan': ('.local_voice', 'build_dubbing_plan'),
    'create_local_voice_pipeline': ('.local_voice', 'create_local_voice_pipeline'),
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
    'DictationSessionManager',
    'DubbingJob',
    'DubbingRenderPlan',
    'FormattingConfig',
    'IntentResult',
    'LegalNLPProcessor',
    'LocalCapability',
    'LocalTTSConfig',
    'LocalTTSResult',
    'LocalTranscriptionResult',
    'LocalVoiceBackend',
    'LocalVoiceError',
    'LocalVoicePipeline',
    'LocalVoiceProfile',
    'LocalVoiceRegistry',
    'ModelNotAvailableError',
    'NLPResult',
    'NullLocalVoiceBackend',
    'PersonaConfig',
    'ResponseFormatter',
    'SeniorPartnerPersona',
    'SessionManager',
    'SpeechConfig',
    'SpeechProcessor',
    'TranscriptionResult',
    'VoiceConfig',
    'VoiceDesignSpec',
    'VoiceEngine',
    'VoiceEnrollmentManager',
    'VoiceProfileNotFoundError',
    'VoiceSample',
    'WakeWordConfig',
    'WakeWordDetector',
    'build_dubbing_plan',
    'create_local_voice_pipeline',
]

__version__ = '1.0.0'
__author__ = 'SintraPrime Legal Technology'
