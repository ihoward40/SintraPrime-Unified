"""LocalVoice: Fully local voice pipeline for SintraPrime voice system.

Provider-agnostic interfaces for on-device voice capabilities: voice
enrollment/cloning, parametric voice design, dictation (streaming
transcription), offline transcription, TTS synthesis, and dubbing job
planning. Everything is designed for 100% local execution with no cloud
round-trip.

ORIGINAL CODE NOTICE: this module was written from scratch for
SintraPrime-Unified. It defines clean abstract contracts that real local
models must satisfy, plus a transparent local stub backend used where no
model is wired yet. The stub never pretends to do model work: enrollment
bookkeeping runs locally, synthesis emits a deterministic placeholder tone
track clearly flagged as such, and transcription raises
ModelNotAvailableError with an actionable message.

Components:
- LocalVoiceBackend: abstract backend contract for local models
- NullLocalVoiceBackend: honest local stub (no model wired)
- LocalVoiceRegistry: local store of enrolled voice profiles
- VoiceEnrollmentManager: enroll/clone voices from local audio samples
- DictationSessionManager: streaming dictation with partial results
- DubbingJob / build_dubbing_plan: dubbing render plans from timing maps
- LocalVoicePipeline: facade wiring registry + backend
"""

import io
import logging
import math
import struct
import uuid
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ==================== Errors ====================

class LocalVoiceError(Exception):
    """Base error for the local voice pipeline."""


class EnrollmentError(LocalVoiceError):
    """Raised when voice enrollment fails validation or backend enrollment."""


class ModelNotAvailableError(LocalVoiceError):
    """Raised when no local model is wired for the requested capability."""


class VoiceProfileNotFoundError(LocalVoiceError):
    """Raised when a voice profile id is not present in the registry."""


class DictationError(LocalVoiceError):
    """Raised for dictation session errors."""


class DubbingError(LocalVoiceError):
    """Raised when a dubbing job spec is invalid."""


# ==================== Enums ====================

class LocalCapability(Enum):
    """Capabilities a local voice backend may advertise."""
    VOICE_ENROLLMENT = "voice_enrollment"
    VOICE_DESIGN = "voice_design"
    TTS_SYNTHESIS = "tts_synthesis"
    TRANSCRIPTION = "transcription"
    DICTATION_STREAMING = "dictation_streaming"
    DUBBING = "dubbing"


# ==================== Data Models ====================

@dataclass
class VoiceDesignSpec:
    """Parametric voice design specification.

    Describes a synthetic voice by adjustable parameters rather than by a
    cloned sample. A backend with VOICE_DESIGN capability maps these onto a
    real voice model; the stub backend stores them as profile metadata.
    """
    name: str
    language: str = "en"
    timbre_warmth: float = 0.5  # 0.0 (bright) .. 1.0 (warm)
    pitch_shift: float = 0.0     # semitones, -12.0 .. +12.0
    speaking_rate: float = 1.0   # 0.5 .. 2.0
    breathiness: float = 0.2     # 0.0 .. 1.0

    def validate(self) -> None:
        """Validate parameter ranges.

        Raises:
            EnrollmentError if any parameter is out of range.
        """
        if not 0.0 <= self.timbre_warmth <= 1.0:
            raise EnrollmentError("timbre_warmth must be in [0.0, 1.0]")
        if not -12.0 <= self.pitch_shift <= 12.0:
            raise EnrollmentError("pitch_shift must be in [-12.0, 12.0]")
        if not 0.5 <= self.speaking_rate <= 2.0:
            raise EnrollmentError("speaking_rate must be in [0.5, 2.0]")
        if not 0.0 <= self.breathiness <= 1.0:
            raise EnrollmentError("breathiness must be in [0.0, 1.0]")


@dataclass
class VoiceSample:
    """One local audio sample used for voice enrollment."""
    label: str
    audio_bytes: bytes
    sample_rate: int = 16000
    channels: int = 1

    def duration_seconds(self) -> float:
        """Estimate duration assuming 16-bit PCM.

        Returns:
            Estimated duration in seconds (0.0 for empty samples).
        """
        if not self.audio_bytes or self.sample_rate <= 0:
            return 0.0
        bytes_per_second = self.sample_rate * self.channels * 2  # 16-bit
        return len(self.audio_bytes) / bytes_per_second


@dataclass
class LocalVoiceProfile:
    """An enrolled local voice profile."""
    voice_id: str
    display_name: str
    language: str = "en"
    sample_count: int = 0
    total_sample_seconds: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    design: Optional[VoiceDesignSpec] = None
    backend_name: str = "unknown"
    backend_artifact: Optional[Dict[str, Any]] = None


@dataclass
class LocalTTSConfig:
    """Configuration for local speech synthesis."""
    sample_rate: int = 16000
    speaking_rate: float = 1.0
    pitch: float = 1.0
    audio_format: str = "wav"


@dataclass
class LocalTTSResult:
    """Result of local speech synthesis."""
    audio_bytes: bytes
    sample_rate: int
    duration_seconds: float
    voice_id: str
    backend: str
    is_placeholder: bool = False


@dataclass
class LocalTranscriptionResult:
    """Result of local transcription."""
    text: str
    confidence: float
    language: str
    is_partial: bool = False
    backend: str = "unknown"


@dataclass
class DubbingSegment:
    """One timed segment of a dubbing job."""
    index: int
    start_seconds: float
    end_seconds: float
    source_text: str
    target_text: Optional[str] = None

    def duration_seconds(self) -> float:
        """Segment duration in seconds."""
        return max(0.0, self.end_seconds - self.start_seconds)


@dataclass
class DubbingJob:
    """Dubbing job spec: source audio + target voice + timing map."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_audio_seconds: float = 0.0
    target_voice_id: str = ""
    language: str = "en"
    segments: List[DubbingSegment] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DubbingRenderPlan:
    """Render plan derived from a DubbingJob."""
    job_id: str
    target_voice_id: str
    source_audio_seconds: float
    segment_count: int
    planned_segments: List[Dict[str, Any]] = field(default_factory=list)
    estimated_render_seconds: float = 0.0
    steps: List[str] = field(default_factory=list)


# ==================== Backend Interface ====================

class LocalVoiceBackend(ABC):
    """Abstract contract every local voice model backend must satisfy.

    Concrete backends (e.g. a local TTS model, a local STT model, or a
    combined engine) implement the capabilities they actually support and
    advertise them via capabilities(). Unsupported operations must raise
    ModelNotAvailableError, never silently degrade.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name used for logging and result attribution."""

    @abstractmethod
    async def capabilities(self) -> Set[LocalCapability]:
        """Return the set of capabilities this backend actually provides."""

    @abstractmethod
    async def enroll_voice(
        self,
        samples: List[VoiceSample],
        design: Optional[VoiceDesignSpec] = None,
    ) -> Dict[str, Any]:
        """Enroll a voice from local samples and/or a design spec.

        Args:
            samples: Local audio samples for cloning.
            design: Optional parametric voice design.

        Returns:
            Backend-side artifact dict (e.g. embedding path), JSON-serializable.

        Raises:
            ModelNotAvailableError if enrollment is unsupported.
            EnrollmentError if the inputs are rejected.
        """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        profile: LocalVoiceProfile,
        config: LocalTTSConfig,
    ) -> LocalTTSResult:
        """Synthesize text to speech with an enrolled profile.

        Raises:
            ModelNotAvailableError if synthesis is unsupported.
        """

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
    ) -> LocalTranscriptionResult:
        """Transcribe a complete audio buffer.

        Raises:
            ModelNotAvailableError if transcription is unsupported.
        """

    async def transcribe_chunk(
        self,
        chunk: bytes,
        context: Optional[Dict[str, Any]] = None,
    ) -> LocalTranscriptionResult:
        """Transcribe one streaming chunk (partial result).

        Default implementation raises; backends with DICTATION_STREAMING
        override this.

        Raises:
            ModelNotAvailableError if streaming is unsupported.
        """
        raise ModelNotAvailableError(
            f"Backend '{self.name}' does not support streaming transcription."
        )


# ==================== Stub Backend ====================

def _build_placeholder_wav(duration_seconds: float, sample_rate: int = 16000) -> bytes:
    """Build a deterministic placeholder tone WAV.

    This is intentionally NOT speech: a clearly-marked stand-in used until a
    real local TTS model is wired. Callers must check is_placeholder.

    Args:
        duration_seconds: Length of the tone.
        sample_rate: Sample rate for the WAV.

    Returns:
        Valid WAV bytes containing a 440 Hz sine tone.
    """
    duration_seconds = max(0.25, min(duration_seconds, 60.0))
    frame_count = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(frame_count):
            sample = int(8000 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            wav.writeframes(struct.pack("<h", sample))
    return buffer.getvalue()


class NullLocalVoiceBackend(LocalVoiceBackend):
    """Transparent local stub backend used where no model is wired yet.

    Honest by design:
    - Enrollment bookkeeping runs locally (profile registered, no embedding).
    - Synthesis returns a deterministic placeholder tone WAV with
      is_placeholder=True. It is never presented as real speech.
    - Transcription and streaming transcription raise ModelNotAvailableError
      with an actionable message.
    """

    @property
    def name(self) -> str:
        return "null-local-stub"

    async def capabilities(self) -> Set[LocalCapability]:
        return {
            LocalCapability.VOICE_ENROLLMENT,
            LocalCapability.VOICE_DESIGN,
            LocalCapability.TTS_SYNTHESIS,
            LocalCapability.DICTATION_STREAMING,
            LocalCapability.DUBBING,
        }

    async def enroll_voice(
        self,
        samples: List[VoiceSample],
        design: Optional[VoiceDesignSpec] = None,
    ) -> Dict[str, Any]:
        total = sum(s.duration_seconds() for s in samples)
        logger.info(
            "NullLocalVoiceBackend: registered %d sample(s) (%.1fs) locally; "
            "no embedding computed.",
            len(samples), total,
        )
        return {
            "artifact": None,
            "status": "profile_registered_locally",
            "sample_seconds": round(total, 2),
            "designed": design is not None,
        }

    async def synthesize(
        self,
        text: str,
        profile: LocalVoiceProfile,
        config: LocalTTSConfig,
    ) -> LocalTTSResult:
        if not text or not text.strip():
            raise LocalVoiceError("Cannot synthesize empty text.")
        # Deterministic placeholder length scales with text length.
        duration = 0.5 + 0.05 * len(text)
        audio = _build_placeholder_wav(duration, config.sample_rate)
        logger.warning(
            "NullLocalVoiceBackend: returning PLACEHOLDER tone audio "
            "(is_placeholder=True); wire a real local TTS model for speech."
        )
        return LocalTTSResult(
            audio_bytes=audio,
            sample_rate=config.sample_rate,
            duration_seconds=duration,
            voice_id=profile.voice_id,
            backend=self.name,
            is_placeholder=True,
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
    ) -> LocalTranscriptionResult:
        raise ModelNotAvailableError(
            "No local transcription model is wired. NullLocalVoiceBackend is a "
            "stub: replace it with a backend implementing transcribe() (e.g. a "
            "local Whisper-class model) to enable transcription."
        )


# ==================== Registry ====================

class LocalVoiceRegistry:
    """Local store of enrolled voice profiles.

    In-memory by default; serialize with to_dict()/from_dict() for
    persistence (JSON file, database row, etc.).
    """

    def __init__(self):
        self._profiles: Dict[str, LocalVoiceProfile] = {}

    def register(self, profile: LocalVoiceProfile) -> LocalVoiceProfile:
        """Register (or replace) a voice profile.

        Args:
            profile: Profile to store.

        Returns:
            The stored profile.
        """
        self._profiles[profile.voice_id] = profile
        logger.info("Registered local voice profile %s", profile.voice_id)
        return profile

    def get(self, voice_id: str) -> LocalVoiceProfile:
        """Get a profile by id.

        Raises:
            VoiceProfileNotFoundError if the id is unknown.
        """
        try:
            return self._profiles[voice_id]
        except KeyError:
            raise VoiceProfileNotFoundError(
                f"Voice profile '{voice_id}' is not enrolled."
            ) from None

    def list(self) -> List[LocalVoiceProfile]:
        """List all enrolled profiles."""
        return list(self._profiles.values())

    def remove(self, voice_id: str) -> bool:
        """Remove a profile.

        Returns:
            True if a profile was removed, False if it did not exist.
        """
        if voice_id in self._profiles:
            del self._profiles[voice_id]
            logger.info("Removed local voice profile %s", voice_id)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to a JSON-compatible dict."""
        profiles = []
        for p in self._profiles.values():
            profiles.append({
                "voice_id": p.voice_id,
                "display_name": p.display_name,
                "language": p.language,
                "sample_count": p.sample_count,
                "total_sample_seconds": p.total_sample_seconds,
                "created_at": p.created_at,
                "backend_name": p.backend_name,
                "backend_artifact": p.backend_artifact,
                "design": vars(p.design) if p.design else None,
            })
        return {"profiles": profiles}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalVoiceRegistry":
        """Restore a registry from to_dict() output."""
        registry = cls()
        for item in data.get("profiles", []):
            design_data = item.get("design")
            design = VoiceDesignSpec(**design_data) if design_data else None
            registry.register(LocalVoiceProfile(
                voice_id=item["voice_id"],
                display_name=item["display_name"],
                language=item.get("language", "en"),
                sample_count=item.get("sample_count", 0),
                total_sample_seconds=item.get("total_sample_seconds", 0.0),
                created_at=item.get("created_at", datetime.now().isoformat()),
                design=design,
                backend_name=item.get("backend_name", "unknown"),
                backend_artifact=item.get("backend_artifact"),
            ))
        return registry


# ==================== Enrollment ====================

class VoiceEnrollmentManager:
    """Enroll/clone voice profiles from local audio samples."""

    MIN_SAMPLE_SECONDS = 3.0

    def __init__(
        self,
        registry: Optional[LocalVoiceRegistry] = None,
        backend: Optional[LocalVoiceBackend] = None,
    ):
        self.registry = registry or LocalVoiceRegistry()
        self.backend = backend or NullLocalVoiceBackend()

    async def enroll(
        self,
        display_name: str,
        samples: List[VoiceSample],
        language: str = "en",
        design: Optional[VoiceDesignSpec] = None,
        min_sample_seconds: float = MIN_SAMPLE_SECONDS,
    ) -> LocalVoiceProfile:
        """Enroll a voice profile from local samples and/or a design spec.

        Args:
            display_name: Human-readable profile name.
            samples: Local audio samples for cloning (may be empty when
                enrolling a pure design spec).
            language: Language code.
            design: Optional parametric voice design.
            min_sample_seconds: Minimum total sample audio required when
                samples are provided.

        Returns:
            The enrolled LocalVoiceProfile.

        Raises:
            EnrollmentError if validation fails.
            ModelNotAvailableError if the backend lacks enrollment support.
        """
        if not display_name or not display_name.strip():
            raise EnrollmentError("display_name is required.")
        if design is not None:
            design.validate()

        total_seconds = sum(s.duration_seconds() for s in samples)
        if samples and total_seconds < min_sample_seconds:
            raise EnrollmentError(
                f"Need at least {min_sample_seconds:.1f}s of sample audio; "
                f"got {total_seconds:.2f}s."
            )
        if not samples and design is None:
            raise EnrollmentError(
                "Provide at least one audio sample or a voice design spec."
            )

        caps = await self.backend.capabilities()
        if LocalCapability.VOICE_ENROLLMENT not in caps:
            raise ModelNotAvailableError(
                f"Backend '{self.backend.name}' does not support enrollment."
            )

        artifact = await self.backend.enroll_voice(samples, design)
        profile = LocalVoiceProfile(
            voice_id=f"local-{uuid.uuid4().hex[:12]}",
            display_name=display_name.strip(),
            language=language,
            sample_count=len(samples),
            total_sample_seconds=round(total_seconds, 2),
            design=design,
            backend_name=self.backend.name,
            backend_artifact=artifact,
        )
        self.registry.register(profile)
        logger.info("Enrolled local voice '%s' as %s", display_name, profile.voice_id)
        return profile


# ==================== Dictation ====================

@dataclass
class DictationSessionState:
    """Mutable state of one dictation session."""
    session_id: str
    user_id: Optional[str]
    language: str
    started_at: str
    chunks: List[bytes] = field(default_factory=list)
    partials: List[str] = field(default_factory=list)
    active: bool = True


class DictationSessionManager:
    """Manage streaming dictation sessions with partial results.

    Sessions accept PCM audio chunks, forward them to the backend for partial
    transcription, and keep a running transcript. Works with any backend
    advertising DICTATION_STREAMING.
    """

    def __init__(self, backend: Optional[LocalVoiceBackend] = None):
        self.backend = backend or NullLocalVoiceBackend()
        self._sessions: Dict[str, DictationSessionState] = {}

    async def start_session(
        self,
        user_id: Optional[str] = None,
        language: str = "en",
        on_partial: Optional[Callable[[str, LocalTranscriptionResult], None]] = None,
        on_final: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> str:
        """Start a dictation session.

        Args:
            user_id: Optional owner id.
            language: Language code.
            on_partial: Optional callback(session_id, partial_result).
            on_final: Optional callback(session_id, summary).

        Returns:
            The new session id.

        Raises:
            ModelNotAvailableError if streaming is unsupported.
        """
        caps = await self.backend.capabilities()
        if LocalCapability.DICTATION_STREAMING not in caps:
            raise ModelNotAvailableError(
                f"Backend '{self.backend.name}' does not support dictation."
            )
        session_id = f"dict-{uuid.uuid4().hex[:12]}"
        state = DictationSessionState(
            session_id=session_id,
            user_id=user_id,
            language=language,
            started_at=datetime.now().isoformat(),
        )
        self._sessions[session_id] = state
        # Store callbacks on the state object dynamically for simplicity.
        state_callbacks = {"on_partial": on_partial, "on_final": on_final}
        setattr(state, "_callbacks", state_callbacks)
        logger.info("Started dictation session %s", session_id)
        return session_id

    def _require_active(self, session_id: str) -> DictationSessionState:
        state = self._sessions.get(session_id)
        if state is None or not state.active:
            raise DictationError(f"Dictation session '{session_id}' is not active.")
        return state

    async def submit_chunk(
        self,
        session_id: str,
        audio_chunk: bytes,
    ) -> LocalTranscriptionResult:
        """Submit one audio chunk and get a partial transcription.

        Args:
            session_id: Active dictation session id.
            audio_chunk: Raw PCM audio bytes.

        Returns:
            Partial transcription result.

        Raises:
            DictationError if the session is unknown or stopped.
            ModelNotAvailableError if the backend cannot stream.
        """
        state = self._require_active(session_id)
        if not audio_chunk:
            raise DictationError("Empty audio chunk.")
        state.chunks.append(audio_chunk)
        result = await self.backend.transcribe_chunk(
            audio_chunk,
            {"session_id": session_id, "chunk_index": len(state.chunks) - 1},
        )
        if result.text:
            state.partials.append(result.text)
        callbacks = getattr(state, "_callbacks", {})
        if callbacks.get("on_partial"):
            callbacks["on_partial"](session_id, result)
        return result

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop a session and return a summary.

        Args:
            session_id: Active dictation session id.

        Returns:
            Summary dict with chunk count, bytes, and running transcript.
        """
        state = self._require_active(session_id)
        state.active = False
        total_bytes = sum(len(c) for c in state.chunks)
        summary = {
            "session_id": session_id,
            "user_id": state.user_id,
            "language": state.language,
            "started_at": state.started_at,
            "stopped_at": datetime.now().isoformat(),
            "chunk_count": len(state.chunks),
            "total_bytes": total_bytes,
            "transcript": " ".join(state.partials).strip(),
        }
        callbacks = getattr(state, "_callbacks", {})
        if callbacks.get("on_final"):
            callbacks["on_final"](session_id, summary)
        logger.info(
            "Stopped dictation session %s (%d chunks)",
            session_id, len(state.chunks),
        )
        return summary


# ==================== Dubbing ====================

def build_dubbing_plan(
    job: DubbingJob,
    registry: LocalVoiceRegistry,
    render_speed_factor: float = 1.5,
) -> DubbingRenderPlan:
    """Build a render plan for a dubbing job.

    Validates the target voice exists, segments are ordered and
    non-overlapping, and the timing map fits the source audio.

    Args:
        job: Dubbing job spec.
        registry: Voice registry (target voice must be enrolled).
        render_speed_factor: Estimated seconds of render per second of audio.

    Returns:
        DubbingRenderPlan with per-segment synthesis order.

    Raises:
        VoiceProfileNotFoundError if the target voice is not enrolled.
        DubbingError if the timing map is invalid.
    """
    profile = registry.get(job.target_voice_id)  # raises if unknown

    if job.source_audio_seconds <= 0:
        raise DubbingError("source_audio_seconds must be positive.")
    if not job.segments:
        raise DubbingError("Dubbing job must contain at least one segment.")

    ordered = sorted(job.segments, key=lambda s: s.start_seconds)
    planned: List[Dict[str, Any]] = []
    total_planned = 0.0
    for i, seg in enumerate(ordered):
        if seg.end_seconds <= seg.start_seconds:
            raise DubbingError(
                f"Segment {seg.index}: end must be after start."
            )
        if i > 0 and seg.start_seconds < ordered[i - 1].end_seconds:
            raise DubbingError(
                f"Segment {seg.index}: overlaps previous segment."
            )
        if seg.end_seconds > job.source_audio_seconds:
            raise DubbingError(
                f"Segment {seg.index}: extends beyond source audio "
                f"({job.source_audio_seconds}s)."
            )
        text = seg.target_text or seg.source_text
        planned.append({
            "order": i,
            "segment_index": seg.index,
            "start_seconds": seg.start_seconds,
            "end_seconds": seg.end_seconds,
            "text": text,
            "voice_id": profile.voice_id,
        })
        total_planned += seg.duration_seconds()

    steps = [
        f"validate target voice '{profile.display_name}' ({profile.voice_id})",
        f"align {len(planned)} segment(s) against {job.source_audio_seconds}s source",
        "synthesize each segment with the target voice (local TTS)",
        "time-stretch/compress synthesized segments to fit the timing map",
        "mix dubbed track over source audio and export",
    ]
    return DubbingRenderPlan(
        job_id=job.job_id,
        target_voice_id=profile.voice_id,
        source_audio_seconds=job.source_audio_seconds,
        segment_count=len(planned),
        planned_segments=planned,
        estimated_render_seconds=round(total_planned * render_speed_factor, 2),
        steps=steps,
    )


# ==================== Pipeline Facade ====================

class LocalVoicePipeline:
    """Facade wiring the registry, enrollment, dictation, and dubbing pieces.

    This is the single entry point most callers need: it holds one backend
    and one registry, and exposes enrollment, synthesis, transcription,
    dictation sessions, and dubbing planning.
    """

    def __init__(
        self,
        backend: Optional[LocalVoiceBackend] = None,
        registry: Optional[LocalVoiceRegistry] = None,
    ):
        self.backend = backend or NullLocalVoiceBackend()
        self.registry = registry or LocalVoiceRegistry()
        self.enrollment = VoiceEnrollmentManager(self.registry, self.backend)
        self.dictation = DictationSessionManager(self.backend)

    async def capabilities(self) -> Set[LocalCapability]:
        """Advertised backend capabilities."""
        return await self.backend.capabilities()

    async def enroll(
        self,
        display_name: str,
        samples: List[VoiceSample],
        language: str = "en",
        design: Optional[VoiceDesignSpec] = None,
    ) -> LocalVoiceProfile:
        """Enroll a voice profile from local samples and/or a design spec."""
        return await self.enrollment.enroll(display_name, samples, language, design)

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        config: Optional[LocalTTSConfig] = None,
    ) -> LocalTTSResult:
        """Synthesize text with an enrolled voice profile.

        Raises:
            VoiceProfileNotFoundError if the voice is not enrolled.
        """
        profile = self.registry.get(voice_id)
        return await self.backend.synthesize(
            text, profile, config or LocalTTSConfig()
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
    ) -> LocalTranscriptionResult:
        """Transcribe a complete audio buffer (raises if no model wired)."""
        return await self.backend.transcribe(audio_bytes, language)

    def plan_dubbing(
        self,
        job: DubbingJob,
        render_speed_factor: float = 1.5,
    ) -> DubbingRenderPlan:
        """Build a render plan for a dubbing job."""
        return build_dubbing_plan(job, self.registry, render_speed_factor)


def create_local_voice_pipeline(
    backend: Optional[LocalVoiceBackend] = None,
    registry: Optional[LocalVoiceRegistry] = None,
) -> LocalVoicePipeline:
    """Create a LocalVoicePipeline.

    Args:
        backend: Local model backend; defaults to NullLocalVoiceBackend
            (honest stub) until a real local model is wired.
        registry: Shared voice registry; a new one is created if omitted.

    Returns:
        Configured LocalVoicePipeline.
    """
    return LocalVoicePipeline(backend=backend, registry=registry)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
