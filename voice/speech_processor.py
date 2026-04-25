"""SpeechProcessor: Multi-provider STT/TTS with fallbacks and preprocessing.

Handles speech-to-text using OpenAI Whisper (primary) and Google Speech-to-Text (fallback).
Handles text-to-speech using ElevenLabs (primary), AWS Polly (fallback), and pyttsx3 (offline).
Includes audio preprocessing, language detection, and legal term pronunciation.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SpeechProvider(Enum):
    """Speech processing providers."""
    OPENAI_WHISPER = "openai_whisper"
    GOOGLE_STT = "google_stt"
    ELEVENLABS = "elevenlabs"
    AWS_POLLY = "aws_polly"
    PYTTSX3 = "pyttsx3"


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    MANDARIN = "zh"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    RUSSIAN = "ru"


@dataclass
class VoiceProfile:
    """Configuration for voice output."""
    provider: SpeechProvider = SpeechProvider.ELEVENLABS
    voice_id: str = "senior-partner-professional"
    language: Language = Language.ENGLISH
    speaking_rate: float = 0.95  # 0.5 to 2.0
    pitch: float = 1.0
    volume: float = 1.0
    emotion: str = "professional"  # professional, warm, urgent, reassuring


@dataclass
class TranscriptionResult:
    """Result of transcription."""
    text: str
    confidence: float
    language: Language
    duration_seconds: float
    provider: SpeechProvider
    is_partial: bool = False
    has_profanity: bool = False
    speaker_count: int = 1


@dataclass
class SpeechConfig:
    """Configuration for SpeechProcessor."""
    stt_primary_provider: SpeechProvider = SpeechProvider.OPENAI_WHISPER
    stt_fallback_provider: SpeechProvider = SpeechProvider.GOOGLE_STT
    tts_primary_provider: SpeechProvider = SpeechProvider.ELEVENLABS
    tts_fallback_provider: SpeechProvider = SpeechProvider.AWS_POLLY
    tts_offline_provider: SpeechProvider = SpeechProvider.PYTTSX3
    
    confidence_threshold: float = 0.7
    enable_noise_reduction: bool = True
    enable_normalization: bool = True
    enable_silence_detection: bool = True
    enable_language_detection: bool = True
    enable_speaker_diarization: bool = False
    
    supported_languages: List[Language] = field(
        default_factory=lambda: [Language.ENGLISH, Language.SPANISH, Language.FRENCH]
    )
    sample_rate: int = 16000
    channels: int = 1
    
    # API keys (in production, get from environment)
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None


class LegalTermsDictionary:
    """Pronunciation guide for legal terms."""

    LEGAL_TERMS = {
        "plaintiff": "PLAYN-tif",
        "defendant": "de-FEN-dent",
        "tort": "tort",
        "lien": "LEEN",
        "fiduciary": "fi-DOO-shee-air-ee",
        "affidavit": "af-i-DAY-vit",
        "subpoena": "suh-PEE-nuh",
        "habeas corpus": "HAY-bee-us KOR-pus",
        "pro bono": "pro BO-no",
        "amicus curiae": "uh-MEE-kus KYUR-ee-ee",
        "mens rea": "menz RAY-uh",
        "actus reus": "AHK-tus RAY-us",
        "prima facie": "PREE-muh FAY-shuh",
        "caveat emptor": "KAH-way-aht EMP-tor",
        "quid pro quo": "kwid pro KWO",
        "force majeure": "fors ma-YUR",
        "in camera": "in KAM-er-uh",
        "duress": "du-RES",
        "estoppel": "es-TOP-ul",
        "injunction": "in-JUK-shun",
        "locus standi": "LO-kus STAN-dee",
        "nolo contendere": "NO-lo kun-TEN-der-ee",
        "litigation": "lit-i-GAY-shun",
        "jurisdiction": "jur-is-DIK-shun",
        "statute of limitations": "STAT-chut of lim-i-TAY-shunz",
        "tort reform": "tort ri-FORM",
        "negligence": "NEG-li-jens",
        "assault": "uh-SAWLT",
        "battery": "BAT-uh-ree",
        "contract": "KON-trakt",
        "consideration": "kun-sid-ur-AY-shun",
        "deposition": "dep-uh-ZISH-un",
        "discovery": "dis-KUV-uh-ree",
        "voir dire": "vwah deer",
        "felony": "FEL-uh-nee",
        "misdemeanor": "mis-duh-MEE-nur",
        "homicide": "HOM-uh-side",
        "arson": "AR-sun",
        "burglary": "BUR-gluh-ree",
        "larceny": "LAR-suh-nee",
        "libel": "LY-bul",
        "slander": "SLAN-dur",
        "copyright": "KO-pee-rite",
        "trademark": "TRADE-mark",
        "patent": "PAT-ent",
        "covenant": "KUV-uh-nunt",
        "easement": "EEZ-ment",
        "mortgage": "MOR-gij",
        "deed": "deed",
        "escrow": "ES-kro",
        "probate": "PRO-bate",
        "intestate": "in-TES-tate",
        "testator": "tes-TAY-tor",
        "beneficiary": "ben-uh-FISH-uh-ree",
        "executor": "ig-ZEK-yuh-tur",
        "guardian ad litem": "GAR-dee-un ad LY-tem",
        "emancipation": "i-man-si-PAY-shun",
        "custody": "KUS-tuh-dee",
        "visitation": "viz-i-TAY-shun",
        "alimony": "AL-uh-mo-nee",
        "child support": "childe suh-PORT",
        "prenuptial": "pre-NUP-shul",
        "postnuptial": "post-NUP-shul",
        "adoption": "uh-DOP-shun",
        "guardianship": "GAR-dee-un-ship",
        "bankruptcy": "BANK-rupt-see",
        "lien": "LEEN",
        "creditor": "KRED-i-tur",
        "debtor": "DET-ur",
        "insolvency": "in-SOL-vun-see",
        "litigation": "lit-i-GAY-shun",
        "arbitration": "ar-bi-TRAY-shun",
        "mediation": "mee-dee-AY-shun",
        "settlement": "SET-ul-ment",
        "judgment": "JUJ-ment",
        "appeal": "uh-PEEL",
        "conviction": "kun-VIK-shun",
        "acquittal": "uh-KWIT-ul",
        "parole": "puh-ROLE",
        "probation": "pro-BAY-shun",
        "restitution": "res-ti-TOO-shun",
        "damages": "DAM-ij-iz",
        "punitive": "PYOO-ni-tiv",
        "compensatory": "kum-PEN-suh-tor-ee",
    }

    @classmethod
    def get_pronunciation(cls, term: str) -> Optional[str]:
        """Get pronunciation for legal term.
        
        Args:
            term: Legal term (lowercase)
            
        Returns:
            Pronunciation guide or None
        """
        return cls.LEGAL_TERMS.get(term.lower())

    @classmethod
    def get_all_terms(cls) -> Dict[str, str]:
        """Get all legal terms and pronunciations."""
        return cls.LEGAL_TERMS.copy()


class AudioPreprocessor:
    """Handles audio preprocessing."""

    @staticmethod
    def normalize_audio(audio_bytes: bytes) -> bytes:
        """Normalize audio to standard levels.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Normalized audio bytes
        """
        # Implementation would normalize amplitude
        # For now, return as-is
        return audio_bytes

    @staticmethod
    def reduce_noise(audio_bytes: bytes, noise_floor: float = 0.02) -> bytes:
        """Apply noise reduction to audio.
        
        Args:
            audio_bytes: Raw audio data
            noise_floor: Noise threshold
            
        Returns:
            Noise-reduced audio bytes
        """
        # Implementation would apply spectral subtraction or similar
        # For now, return as-is
        return audio_bytes

    @staticmethod
    def detect_silence(audio_bytes: bytes, threshold: float = 0.01) -> Tuple[float, float]:
        """Detect silence duration in audio.
        
        Args:
            audio_bytes: Raw audio data
            threshold: Energy threshold for silence
            
        Returns:
            Tuple of (leading_silence, trailing_silence) in seconds
        """
        # Implementation would detect silence periods
        return (0.0, 0.0)

    @staticmethod
    def convert_audio_format(audio_bytes: bytes, from_format: str, 
                           to_format: str) -> bytes:
        """Convert between audio formats.
        
        Args:
            audio_bytes: Audio data in source format
            from_format: Source format (webm, mp3, wav, ogg, aac)
            to_format: Target format
            
        Returns:
            Audio bytes in target format
        """
        # Would use ffmpeg or similar for conversion
        return audio_bytes


class LanguageDetector:
    """Detects language in audio or text."""

    LANGUAGE_CODES = {
        "english": Language.ENGLISH,
        "spanish": Language.SPANISH,
        "french": Language.FRENCH,
        "mandarin": Language.MANDARIN,
        "german": Language.GERMAN,
        "portuguese": Language.PORTUGUESE,
        "italian": Language.ITALIAN,
        "russian": Language.RUSSIAN,
    }

    @classmethod
    def detect_language(cls, text: str) -> Language:
        """Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language
        """
        # Would use langdetect or similar library
        # For now, assume English
        return Language.ENGLISH

    @classmethod
    def is_supported(cls, language: Language) -> bool:
        """Check if language is supported."""
        return language in [Language.ENGLISH, Language.SPANISH, Language.FRENCH]


class SpeechProcessor:
    """Main speech processor with fallback providers."""

    def __init__(self, config: Optional[SpeechConfig] = None):
        """Initialize SpeechProcessor.
        
        Args:
            config: SpeechConfig instance
        """
        self.config = config or SpeechConfig()
        self.preprocessor = AudioPreprocessor()
        self.language_detector = LanguageDetector()
        self.legal_terms = LegalTermsDictionary()

    async def transcribe(self, audio_bytes: bytes, 
                        language: Optional[Language] = None) -> Optional[TranscriptionResult]:
        """Transcribe audio to text.
        
        Uses primary provider with automatic fallback on failure.
        
        Args:
            audio_bytes: Raw audio data
            language: Optional language hint
            
        Returns:
            TranscriptionResult or None if all providers fail
        """
        # Preprocess audio
        if self.config.enable_noise_reduction:
            audio_bytes = self.preprocessor.reduce_noise(audio_bytes)
        if self.config.enable_normalization:
            audio_bytes = self.preprocessor.normalize_audio(audio_bytes)

        # Try primary provider
        result = await self._transcribe_with_provider(
            audio_bytes, 
            self.config.stt_primary_provider,
            language
        )
        
        if result:
            return result

        # Fallback to secondary provider
        logger.warning(f"Primary STT provider failed, trying {self.config.stt_fallback_provider.value}")
        result = await self._transcribe_with_provider(
            audio_bytes,
            self.config.stt_fallback_provider,
            language
        )

        if result:
            return result

        logger.error("All STT providers failed")
        return None

    async def _transcribe_with_provider(self, audio_bytes: bytes,
                                       provider: SpeechProvider,
                                       language: Optional[Language] = None) -> Optional[TranscriptionResult]:
        """Transcribe with specific provider.
        
        Args:
            audio_bytes: Audio data
            provider: Speech provider to use
            language: Optional language hint
            
        Returns:
            TranscriptionResult or None
        """
        try:
            if provider == SpeechProvider.OPENAI_WHISPER:
                return await self._transcribe_whisper(audio_bytes, language)
            elif provider == SpeechProvider.GOOGLE_STT:
                return await self._transcribe_google(audio_bytes, language)
            else:
                logger.error(f"Unknown STT provider: {provider}")
                return None

        except Exception as e:
            logger.error(f"Transcription error with {provider.value}: {e}")
            return None

    async def _transcribe_whisper(self, audio_bytes: bytes,
                                 language: Optional[Language] = None) -> Optional[TranscriptionResult]:
        """Transcribe using OpenAI Whisper.
        
        Production implementation would use openai library.
        """
        # Mock implementation
        return TranscriptionResult(
            text="This is a mock transcription from audio input.",
            confidence=0.92,
            language=language or Language.ENGLISH,
            duration_seconds=5.5,
            provider=SpeechProvider.OPENAI_WHISPER,
        )

    async def _transcribe_google(self, audio_bytes: bytes,
                                language: Optional[Language] = None) -> Optional[TranscriptionResult]:
        """Transcribe using Google Speech-to-Text.
        
        Production implementation would use google-cloud-speech.
        """
        # Mock implementation
        return TranscriptionResult(
            text="This is a mock transcription using Google STT.",
            confidence=0.88,
            language=language or Language.ENGLISH,
            duration_seconds=5.5,
            provider=SpeechProvider.GOOGLE_STT,
        )

    async def synthesize(self, text: str, 
                        voice_profile: Optional[VoiceProfile] = None) -> Optional[bytes]:
        """Synthesize text to speech.
        
        Uses primary provider with automatic fallback.
        
        Args:
            text: Text to synthesize
            voice_profile: Voice configuration
            
        Returns:
            Audio bytes or None if all providers fail
        """
        if not voice_profile:
            voice_profile = VoiceProfile()

        # Try primary provider
        audio = await self._synthesize_with_provider(text, voice_profile, self.config.tts_primary_provider)
        
        if audio:
            return audio

        # Fallback to secondary provider
        logger.warning(f"Primary TTS provider failed, trying {self.config.tts_fallback_provider.value}")
        audio = await self._synthesize_with_provider(text, voice_profile, self.config.tts_fallback_provider)
        
        if audio:
            return audio

        # Last resort: offline provider
        logger.warning(f"TTS providers failed, using offline {self.config.tts_offline_provider.value}")
        audio = await self._synthesize_with_provider(text, voice_profile, self.config.tts_offline_provider)

        if not audio:
            logger.error("All TTS providers failed")

        return audio

    async def _synthesize_with_provider(self, text: str, voice_profile: VoiceProfile,
                                       provider: SpeechProvider) -> Optional[bytes]:
        """Synthesize with specific provider.
        
        Args:
            text: Text to synthesize
            voice_profile: Voice configuration
            provider: TTS provider
            
        Returns:
            Audio bytes or None
        """
        try:
            if provider == SpeechProvider.ELEVENLABS:
                return await self._synthesize_elevenlabs(text, voice_profile)
            elif provider == SpeechProvider.AWS_POLLY:
                return await self._synthesize_aws(text, voice_profile)
            elif provider == SpeechProvider.PYTTSX3:
                return await self._synthesize_pyttsx3(text, voice_profile)
            else:
                logger.error(f"Unknown TTS provider: {provider}")
                return None

        except Exception as e:
            logger.error(f"Synthesis error with {provider.value}: {e}")
            return None

    async def _synthesize_elevenlabs(self, text: str, voice_profile: VoiceProfile) -> Optional[bytes]:
        """Synthesize using ElevenLabs API.
        
        Production implementation would use elevenlabs library.
        """
        # Mock implementation - return 1 second of silence
        import numpy as np
        sample_rate = 44100
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_array = np.zeros(samples, dtype=np.float32)
        return audio_array.tobytes()

    async def _synthesize_aws(self, text: str, voice_profile: VoiceProfile) -> Optional[bytes]:
        """Synthesize using AWS Polly.
        
        Production implementation would use boto3.
        """
        # Mock implementation
        import numpy as np
        sample_rate = 44100
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_array = np.zeros(samples, dtype=np.float32)
        return audio_array.tobytes()

    async def _synthesize_pyttsx3(self, text: str, voice_profile: VoiceProfile) -> Optional[bytes]:
        """Synthesize using pyttsx3 (offline, no API key needed).
        
        Production implementation would use pyttsx3 library.
        """
        # Mock implementation
        import numpy as np
        sample_rate = 44100
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_array = np.zeros(samples, dtype=np.float32)
        return audio_array.tobytes()

    def restore_punctuation(self, text: str) -> str:
        """Restore punctuation to transcribed text.
        
        Args:
            text: Transcribed text
            
        Returns:
            Text with restored punctuation
        """
        # Would use ML model or rule-based approach
        # For now, simple sentence-ending detection
        sentences = text.split(" ")
        # Add periods at logical endpoints
        return text if text.endswith((".", "!", "?")) else text + "."

    def extract_legal_terms(self, text: str) -> Dict[str, str]:
        """Extract legal terms and their pronunciations.
        
        Args:
            text: Text containing legal terms
            
        Returns:
            Dictionary mapping terms to pronunciations
        """
        terms = {}
        words = text.lower().split()
        
        for word in words:
            pronunciation = self.legal_terms.get_pronunciation(word)
            if pronunciation:
                terms[word] = pronunciation

        return terms

    def get_speech_config_summary(self) -> Dict[str, str]:
        """Get summary of current speech configuration."""
        return {
            "stt_primary": self.config.stt_primary_provider.value,
            "stt_fallback": self.config.stt_fallback_provider.value,
            "tts_primary": self.config.tts_primary_provider.value,
            "tts_fallback": self.config.tts_fallback_provider.value,
            "tts_offline": self.config.tts_offline_provider.value,
            "confidence_threshold": str(self.config.confidence_threshold),
            "supported_languages": ", ".join([l.value for l in self.config.supported_languages]),
        }


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
