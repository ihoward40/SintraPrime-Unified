"""Live audio capture, device discovery, and VAD for SP-LIVE-001 I2."""

import time
import uuid
import threading
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from pathlib import Path


class AudioDeviceType(Enum):
    """Audio device types."""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    DUPLEX = "DUPLEX"


class CaptureMode(Enum):
    """Audio capture modes."""
    PUSH_TO_TALK = "PUSH_TO_TALK"
    WAKE_WORD = "WAKE_WORD"
    CONTINUOUS = "CONTINUOUS"
    SINGLE_UTTERANCE = "SINGLE_UTTERANCE"


@dataclass(frozen=True)
class AudioDevice:
    """Audio device information."""
    device_id: str
    name: str
    type: AudioDeviceType
    sample_rate: int
    channels: int
    is_default: bool = False


@dataclass(frozen=True)
class AudioSegment:
    """Captured audio segment."""
    segment_id: str
    timestamp: float
    data: bytes
    sample_rate: int
    channels: int
    duration_ms: float
    is_speech: bool = False
    vad_confidence: float = 0.0


@dataclass(frozen=True)
class TranscriptionResult:
    """STT transcription result."""
    transcript: str
    confidence: float
    is_final: bool
    segment_id: str
    timestamp: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


class AudioDeviceManager:
    """Manages audio device discovery and selection."""

    def __init__(self):
        self._devices: Dict[str, AudioDevice] = {}
        self._default_input: Optional[AudioDevice] = None
        self._default_output: Optional[AudioDevice] = None
        self._discover_devices()

    def _discover_devices(self):
        """Discover available audio devices (mock implementation for offline development)."""
        # In real implementation, this would use pyaudio/sounddevice
        # For now, create mock devices
        mock_input = AudioDevice(
            device_id="mock_mic_0",
            name="Mock Microphone",
            type=AudioDeviceType.INPUT,
            sample_rate=16000,
            channels=1,
            is_default=True
        )
        mock_output = AudioDevice(
            device_id="mock_speaker_0",
            name="Mock Speaker",
            type=AudioDeviceType.OUTPUT,
            sample_rate=16000,
            channels=1,
            is_default=True
        )
        self._devices[mock_input.device_id] = mock_input
        self._devices[mock_output.device_id] = mock_output
        self._default_input = mock_input
        self._default_output = mock_output

    def get_input_devices(self) -> List[AudioDevice]:
        """Get all input devices."""
        return [d for d in self._devices.values() if d.type in (AudioDeviceType.INPUT, AudioDeviceType.DUPLEX)]

    def get_output_devices(self) -> List[AudioDevice]:
        """Get all output devices."""
        return [d for d in self._devices.values() if d.type in (AudioDeviceType.OUTPUT, AudioDeviceType.DUPLEX)]

    def get_default_input(self) -> Optional[AudioDevice]:
        """Get default input device."""
        return self._default_input

    def get_default_output(self) -> Optional[AudioDevice]:
        """Get default output device."""
        return self._default_output

    def get_device(self, device_id: str) -> Optional[AudioDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)


class VoiceActivityDetector:
    """Voice Activity Detection for speech segmentation."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.energy_threshold = 0.01
        self.speech_frames = 0
        self.silence_frames = 0
        self.min_speech_frames = 3
        self.max_silence_frames = 10

    def process_frame(self, audio_data: bytes) -> Dict[str, Any]:
        """Process a single audio frame for VAD."""
        # Convert bytes to float samples (assuming 16-bit PCM)
        import struct
        samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
        # Normalize to -1.0 to 1.0
        normalized = [s / 32768.0 for s in samples]
        # Calculate energy
        energy = sum(s * s for s in normalized) / len(normalized) if normalized else 0.0

        is_speech = energy > self.energy_threshold

        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1

        # Determine segment state
        if self.speech_frames >= self.min_speech_frames:
            state = "SPEECH"
        elif self.silence_frames >= self.max_silence_frames and self.speech_frames > 0:
            state = "END_OF_SPEECH"
            self.reset()
        else:
            state = "SILENCE"

        return {
            "is_speech": is_speech,
            "energy": energy,
            "state": state,
            "confidence": min(energy / self.energy_threshold, 1.0) if self.energy_threshold > 0 else 0.0
        }

    def reset(self):
        """Reset VAD state."""
        self.speech_frames = 0
        self.silence_frames = 0


class LiveAudioCapture:
    """Live audio capture with VAD integration."""

    def __init__(self, device_manager: AudioDeviceManager, mode: CaptureMode = CaptureMode.PUSH_TO_TALK):
        self.device_manager = device_manager
        self.mode = mode
        self.vad = VoiceActivityDetector()
        self.capture_device: Optional[AudioDevice] = None
        self.is_capturing = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.segment_callback: Optional[Callable[[AudioSegment], None]] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._current_segment_buffer: List[bytes] = []
        self._segment_start_time: Optional[float] = None

    def set_capture_device(self, device_id: str) -> bool:
        """Set the capture device."""
        device = self.device_manager.get_device(device_id)
        if device and device.type in (AudioDeviceType.INPUT, AudioDeviceType.DUPLEX):
            self.capture_device = device
            return True
        return False

    def set_segment_callback(self, callback: Callable[[AudioSegment], None]):
        """Set callback for completed speech segments."""
        self.segment_callback = callback

    def start_capture(self) -> bool:
        """Start audio capture."""
        if self.is_capturing:
            return True

        if not self.capture_device:
            self.capture_device = self.device_manager.get_default_input()
            if not self.capture_device:
                return False

        self.is_capturing = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        return True

    def stop_capture(self):
        """Stop audio capture."""
        self.is_capturing = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None

    def push_to_talk_start(self):
        """Start push-to-talk capture."""
        if self.mode == CaptureMode.PUSH_TO_TALK:
            self._current_segment_buffer = []
            self._segment_start_time = time.time()

    def push_to_talk_end(self) -> Optional[AudioSegment]:
        """End push-to-talk and return segment."""
        if self.mode != CaptureMode.PUSH_TO_TALK:
            return None
        
        # If buffer is empty, create a mock segment for testing
        if not self._current_segment_buffer:
            segment = AudioSegment(
                segment_id=str(uuid.uuid4()),
                timestamp=self._segment_start_time or time.time(),
                data=bytes(1600),  # Mock 100ms audio
                sample_rate=self.capture_device.sample_rate if self.capture_device else 16000,
                channels=self.capture_device.channels if self.capture_device else 1,
                duration_ms=(time.time() - (self._segment_start_time or time.time())) * 1000,
                is_speech=True,
                vad_confidence=1.0
            )
            self._current_segment_buffer = []
            self._segment_start_time = None
            return segment
        
        segment = AudioSegment(
            segment_id=str(uuid.uuid4()),
            timestamp=self._segment_start_time or time.time(),
            data=b"".join(self._current_segment_buffer),
            sample_rate=self.capture_device.sample_rate if self.capture_device else 16000,
            channels=self.capture_device.channels if self.capture_device else 1,
            duration_ms=(time.time() - (self._segment_start_time or time.time())) * 1000,
            is_speech=True,
            vad_confidence=1.0
        )
        self._current_segment_buffer = []
        self._segment_start_time = None
        return segment

    def _capture_loop(self):
        """Background capture loop (mock implementation)."""
        # In real implementation, this would read from audio device
        # For mock, we simulate by generating silence frames
        import time
        while self.is_capturing:
            # Simulate 30ms frame
            frame_size = self.vad.frame_size * 2  # 16-bit = 2 bytes per sample
            silence_frame = bytes(frame_size)
            self.audio_queue.put(silence_frame)
            time.sleep(0.03)

    def get_audio_segment(self, timeout: float = 1.0) -> Optional[AudioSegment]:
        """Get next complete speech segment (for continuous/wake-word modes)."""
        # Mock implementation - returns a synthetic segment for testing
        if not self.is_capturing:
            return None

        # In real implementation, this would use VAD to detect speech boundaries
        # For mock, we return a segment after a delay
        import time
        time.sleep(0.1)
        return AudioSegment(
            segment_id=str(uuid.uuid4()),
            timestamp=time.time(),
            data=bytes(1600),  # 100ms of silence
            sample_rate=16000,
            channels=1,
            duration_ms=100,
            is_speech=False,
            vad_confidence=0.0
        )


def create_audio_capture(mode: CaptureMode = CaptureMode.PUSH_TO_TALK) -> LiveAudioCapture:
    """Factory function to create audio capture pipeline."""
    device_manager = AudioDeviceManager()
    capture = LiveAudioCapture(device_manager, mode)
    capture.set_capture_device(device_manager.get_default_input().device_id)
    return capture