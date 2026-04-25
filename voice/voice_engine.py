"""VoiceEngine: Async voice processing engine with real-time streaming support.

Handles audio capture, speech recognition, persona responses, and speech synthesis.
Supports wake word detection, audio buffering, noise reduction, and session management.
"""

import asyncio
import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
import numpy as np
from collections import deque
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Voice engine event types."""
    WAKE_WORD_DETECTED = "wake_word_detected"
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    PROCESSING_COMPLETE = "processing_complete"
    SPEAKING_STARTED = "speaking_started"
    SPEAKING_COMPLETE = "speaking_complete"
    ERROR_OCCURRED = "error_occurred"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


@dataclass
class VoiceEvent:
    """Event emitted by voice engine."""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None


@dataclass
class VoiceConfig:
    """Configuration for VoiceEngine."""
    sample_rate: int = 16000
    chunk_size: int = 4096
    channels: int = 1
    audio_format: str = "pcm"
    enable_noise_reduction: bool = True
    confidence_threshold: float = 0.7
    buffer_size: int = 10  # chunks to buffer
    wake_words: List[str] = field(default_factory=lambda: ["hey sintraPrime", "counsel"])
    whisper_model: str = "base"
    tts_provider: str = "elevenlabs"  # elevenlabs, aws, pyttsx3
    max_silence_duration: float = 2.0  # seconds
    enable_websocket: bool = True


@dataclass
class SessionData:
    """Tracks conversation context within a session."""
    session_id: str
    created_at: datetime
    client_name: Optional[str] = None
    matter_number: Optional[str] = None
    practice_area: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_interaction(self, user_input: str, assistant_response: str, intent: str = ""):
        """Add interaction to conversation history."""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response,
            "intent": intent,
        })
        self.last_activity = datetime.now()


class AudioBuffer:
    """Manages circular audio buffer with noise reduction."""

    def __init__(self, buffer_size: int, chunk_size: int, enable_noise_reduction: bool = True):
        """Initialize audio buffer.
        
        Args:
            buffer_size: Number of chunks to buffer
            chunk_size: Size of each chunk in samples
            enable_noise_reduction: Whether to apply noise reduction
        """
        self.buffer = deque(maxlen=buffer_size * chunk_size)
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size
        self.enable_noise_reduction = enable_noise_reduction
        self.noise_floor = 0.02

    def add_chunk(self, audio_chunk: np.ndarray) -> None:
        """Add audio chunk to buffer."""
        if self.enable_noise_reduction:
            audio_chunk = self._reduce_noise(audio_chunk)
        # Normalize to -1.0 to 1.0 range
        audio_chunk = np.clip(audio_chunk, -1.0, 1.0)
        self.buffer.extend(audio_chunk)

    def _reduce_noise(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Simple noise reduction using threshold."""
        amplitude = np.abs(audio_chunk)
        noise_mask = amplitude > self.noise_floor
        reduced = audio_chunk * noise_mask.astype(float)
        return reduced

    def get_buffer(self) -> np.ndarray:
        """Get current buffer contents."""
        return np.array(list(self.buffer))

    def is_speech_detected(self) -> bool:
        """Detect if buffer contains speech (energy-based)."""
        audio = self.get_buffer()
        if len(audio) == 0:
            return False
        rms = np.sqrt(np.mean(audio**2))
        return rms > self.noise_floor * 2

    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()


class SessionManager:
    """Manages voice conversation sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, SessionData] = {}
        self.lock = asyncio.Lock()

    async def create_session(self, client_name: Optional[str] = None) -> str:
        """Create new session.
        
        Returns:
            Session ID
        """
        async with self.lock:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = SessionData(
                session_id=session_id,
                created_at=datetime.now(),
                client_name=client_name,
            )
            logger.info(f"Session created: {session_id}")
            return session_id

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session by ID."""
        return self.sessions.get(session_id)

    async def add_interaction(self, session_id: str, user_input: str, 
                             assistant_response: str, intent: str = "") -> bool:
        """Add interaction to session."""
        async with self.lock:
            if session_id not in self.sessions:
                return False
            self.sessions[session_id].add_interaction(user_input, assistant_response, intent)
            return True

    async def end_session(self, session_id: str) -> bool:
        """End session and clean up."""
        async with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Session ended: {session_id}")
                return True
            return False

    async def list_sessions(self) -> List[str]:
        """Get all active session IDs."""
        return list(self.sessions.keys())

    async def update_session_metadata(self, session_id: str, 
                                     matter_number: Optional[str] = None,
                                     practice_area: Optional[str] = None,
                                     client_name: Optional[str] = None) -> bool:
        """Update session metadata."""
        async with self.lock:
            if session_id not in self.sessions:
                return False
            session = self.sessions[session_id]
            if matter_number:
                session.matter_number = matter_number
            if practice_area:
                session.practice_area = practice_area
            if client_name:
                session.client_name = client_name
            return True


class VoiceEngine:
    """Main async voice engine with streaming and real-time processing."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        """Initialize VoiceEngine.
        
        Args:
            config: VoiceConfig instance
        """
        self.config = config or VoiceConfig()
        self.is_running = False
        self.is_listening = False
        self.audio_buffer = AudioBuffer(
            self.config.buffer_size,
            self.config.chunk_size,
            self.config.enable_noise_reduction,
        )
        self.session_manager = SessionManager()
        self.event_handlers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.current_session_id: Optional[str] = None
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.silence_counter = 0
        self.silence_threshold = int(
            self.config.max_silence_duration * self.config.sample_rate / self.config.chunk_size
        )

    async def start(self) -> None:
        """Start voice engine."""
        if self.is_running:
            logger.warning("Voice engine already running")
            return

        self.is_running = True
        self.current_session_id = await self.session_manager.create_session()
        await self._emit_event(EventType.SESSION_STARTED, {
            "session_id": self.current_session_id
        })
        logger.info(f"VoiceEngine started with session {self.current_session_id}")

        # Start background audio processing task
        asyncio.create_task(self._audio_processing_loop())

    async def stop(self) -> None:
        """Stop voice engine."""
        if not self.is_running:
            return

        self.is_running = False
        self.is_listening = False

        if self.current_session_id:
            await self._emit_event(EventType.SESSION_ENDED, {
                "session_id": self.current_session_id
            })
            await self.session_manager.end_session(self.current_session_id)

        logger.info("VoiceEngine stopped")

    async def process_audio(self, audio_data: bytes) -> Optional[str]:
        """Process audio data and return transcription.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text or None if processing fails
        """
        if not self.is_running:
            logger.error("Engine not running")
            return None

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            
            # Add to buffer
            self.audio_buffer.add_chunk(audio_array)

            # Add to processing queue
            await self.audio_queue.put(audio_array)

            await self._emit_event(EventType.TRANSCRIPTION_STARTED, {
                "session_id": self.current_session_id
            })

            # Mock transcription - in production use Whisper/Google Speech-to-Text
            transcription = await self._transcribe_audio(audio_data)
            
            if transcription and len(transcription) > 0:
                confidence = 0.85  # Mock confidence score
                
                await self._emit_event(EventType.TRANSCRIPTION_COMPLETE, {
                    "text": transcription,
                    "confidence": confidence,
                    "session_id": self.current_session_id,
                })
                
                return transcription
            else:
                await self._emit_event(EventType.ERROR_OCCURRED, {
                    "error": "Transcription produced empty result",
                    "session_id": self.current_session_id,
                })
                return None

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await self._emit_event(EventType.ERROR_OCCURRED, {
                "error": str(e),
                "session_id": self.current_session_id,
            })
            return None

    async def speak(self, text: str) -> Optional[bytes]:
        """Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes or None if synthesis fails
        """
        if not self.is_running:
            return None

        try:
            await self._emit_event(EventType.SPEAKING_STARTED, {
                "text": text[:100],  # First 100 chars
                "session_id": self.current_session_id,
            })

            # Mock TTS - in production use ElevenLabs/AWS Polly
            audio_bytes = await self._synthesize_text(text)

            await self._emit_event(EventType.SPEAKING_COMPLETE, {
                "session_id": self.current_session_id,
            })

            return audio_bytes

        except Exception as e:
            logger.error(f"Error speaking: {e}")
            await self._emit_event(EventType.ERROR_OCCURRED, {
                "error": str(e),
                "session_id": self.current_session_id,
            })
            return None

    async def _transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using Whisper.
        
        In production, integrate with OpenAI Whisper or Google Speech-to-Text.
        """
        # Mock implementation
        await asyncio.sleep(0.1)
        return "Sample transcription from audio"

    async def _synthesize_text(self, text: str) -> bytes:
        """Synthesize text to audio using configured TTS provider.
        
        In production, integrate with ElevenLabs or AWS Polly.
        """
        # Mock implementation - return 1 second of silence
        await asyncio.sleep(0.1)
        sample_rate = self.config.sample_rate
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_array = np.zeros(samples, dtype=np.float32)
        return audio_array.tobytes()

    async def _audio_processing_loop(self) -> None:
        """Background loop for audio processing."""
        while self.is_running:
            try:
                # Process queued audio chunks
                if not self.audio_queue.empty():
                    audio_chunk = await asyncio.wait_for(
                        self.audio_queue.get(), timeout=0.1
                    )
                    # Could add additional processing here
                    self.audio_queue.task_done()
                else:
                    await asyncio.sleep(0.01)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")

    def register_event_handler(self, event_type: EventType, 
                              handler: Callable[[VoiceEvent], None]) -> None:
        """Register handler for voice events.
        
        Args:
            event_type: Type of event to handle
            handler: Async or sync callable that receives VoiceEvent
        """
        self.event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit voice event to all registered handlers."""
        event = VoiceEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            session_id=self.current_session_id,
        )

        for handler in self.event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def get_session_history(self) -> Optional[List[Dict[str, str]]]:
        """Get current session's conversation history."""
        if not self.current_session_id:
            return None
        session = await self.session_manager.get_session(self.current_session_id)
        return session.conversation_history if session else None

    def get_audio_level(self) -> float:
        """Get current audio buffer RMS level (0.0 to 1.0)."""
        audio = self.audio_buffer.get_buffer()
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio**2))
        return min(rms, 1.0)

    async def set_client_name(self, name: str) -> bool:
        """Set client name for current session."""
        if not self.current_session_id:
            return False
        return await self.session_manager.update_session_metadata(
            self.current_session_id,
            client_name=name
        )

    async def set_matter_info(self, matter_number: str, practice_area: str) -> bool:
        """Set matter information for current session."""
        if not self.current_session_id:
            return False
        return await self.session_manager.update_session_metadata(
            self.current_session_id,
            matter_number=matter_number,
            practice_area=practice_area
        )


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
