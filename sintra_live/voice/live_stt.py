"""Live Speech-to-Text (STT) integration for SP-LIVE-001 I2."""

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from pathlib import Path


class STTModelType(Enum):
    """STT model types."""
    LOCAL_WHISPER = "LOCAL_WHISPER"
    LOCAL_VOSK = "LOCAL_VOSK"
    LOCAL_COQUI = "LOCAL_COQUI"
    MOCK = "MOCK"


@dataclass(frozen=True)
class STTConfig:
    """STT configuration."""
    model_type: STTModelType = STTModelType.MOCK
    model_path: Optional[str] = None
    language: str = "en"
    sample_rate: int = 16000
    enable_streaming: bool = True
    enable_partial_results: bool = True
    confidence_threshold: float = 0.5


@dataclass(frozen=True)
class TranscriptionResult:
    """STT transcription result."""
    transcript: str
    confidence: float
    is_final: bool
    segment_id: str
    timestamp: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    model_latency_ms: float = 0.0
    processing_latency_ms: float = 0.0


class STTBackend:
    """Base STT backend interface."""

    def __init__(self, config: STTConfig):
        self.config = config
        self.is_loaded = False

    def load(self) -> bool:
        """Load the STT model."""
        raise NotImplementedError

    def transcribe(self, audio_data: bytes, sample_rate: int) -> TranscriptionResult:
        """Transcribe audio data."""
        raise NotImplementedError

    def transcribe_streaming(self, audio_chunk: bytes, sample_rate: int) -> Optional[TranscriptionResult]:
        """Streaming transcription (partial results)."""
        raise NotImplementedError

    def reset_stream(self):
        """Reset streaming state."""
        raise NotImplementedError


class MockSTTBackend(STTBackend):
    """Mock STT backend for testing and development."""

    def __init__(self, config: STTConfig):
        super().__init__(config)
        self._response_queue: List[str] = [
            "SintraPrime, can you hear me?",
            "Give me the current mission status.",
            "Yes, please proceed.",
            "No, cancel that.",
            "Wait, let me think.",
            "What is the current state?",
        ]
        self._response_index = 0
        self._stream_buffer = ""

    def load(self) -> bool:
        self.is_loaded = True
        return True

    def transcribe(self, audio_data: bytes, sample_rate: int) -> TranscriptionResult:
        start = time.time()
        transcript = self._response_queue[self._response_index % len(self._response_queue)]
        self._response_index += 1

        return TranscriptionResult(
            transcript=transcript,
            confidence=0.95,
            is_final=True,
            segment_id=str(uuid.uuid4()),
            timestamp=time.time(),
            model_latency_ms=(time.time() - start) * 1000,
            processing_latency_ms=5.0
        )

    def transcribe_streaming(self, audio_chunk: bytes, sample_rate: int) -> Optional[TranscriptionResult]:
        start = time.time()
        # Simulate partial transcription
        self._stream_buffer += " partial"

        if len(self._stream_buffer) > 20:
            result = TranscriptionResult(
                transcript=self._stream_buffer.strip(),
                confidence=0.7,
                is_final=False,
                segment_id=str(uuid.uuid4()),
                timestamp=time.time(),
                model_latency_ms=(time.time() - start) * 1000,
                processing_latency_ms=3.0
            )
            return result
        return None

    def reset_stream(self):
        self._stream_buffer = ""


class LocalSTTManager:
    """Manages STT model selection and transcription."""

    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self.backend: Optional[STTBackend] = None
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the appropriate STT backend."""
        if self.config.model_type == STTModelType.MOCK:
            self.backend = MockSTTBackend(self.config)
        else:
            # In real implementation, load appropriate model
            self.backend = MockSTTBackend(self.config)  # Fallback to mock

    def load(self) -> bool:
        """Load the STT model."""
        if self.backend:
            return self.backend.load()
        return False

    def transcribe_segment(self, audio_data: bytes, sample_rate: int) -> TranscriptionResult:
        """Transcribe a complete audio segment."""
        if not self.backend:
            raise RuntimeError("STT backend not initialized")
        return self.backend.transcribe(audio_data, sample_rate)

    def transcribe_streaming(self, audio_chunk: bytes, sample_rate: int) -> Optional[TranscriptionResult]:
        """Process streaming audio chunk."""
        if not self.backend:
            return None
        return self.backend.transcribe_streaming(audio_chunk, sample_rate)

    def reset_stream(self):
        """Reset streaming state."""
        if self.backend:
            self.backend.reset_stream()

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_type": self.config.model_type.value,
            "language": self.config.language,
            "sample_rate": self.config.sample_rate,
            "is_loaded": self.backend.is_loaded if self.backend else False,
            "confidence_threshold": self.config.confidence_threshold
        }


def create_stt_manager(config: STTConfig = None) -> LocalSTTManager:
    """Factory function to create STT manager."""
    return LocalSTTManager(config or STTConfig())