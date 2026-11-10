"""Pytest tests for the local voice pipeline (voice/local_voice.py).

Tests for:
- Voice profile registry (register/get/list/remove/serialization)
- Voice enrollment (sample validation, design specs, stub backend)
- Local TTS synthesis stub (placeholder WAV contract)
- Transcription stub (ModelNotAvailableError)
- Dictation session manager (start/submit/stop with partial results)
- Dubbing job planning (timing-map validation and render plans)
- Pipeline facade wiring
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional, Set

# Import voice modules
import sys
sys.path.insert(0, '/agent/home/SintraPrime-Unified')

from voice.local_voice import (
    DictationSessionManager,
    DubbingJob,
    DubbingSegment,
    DubbingRenderPlan,
    LocalCapability,
    LocalTTSConfig,
    LocalTranscriptionResult,
    LocalVoiceBackend,
    LocalVoicePipeline,
    LocalVoiceProfile,
    LocalVoiceRegistry,
    ModelNotAvailableError,
    DictationError,
    DubbingError,
    EnrollmentError,
    NullLocalVoiceBackend,
    VoiceDesignSpec,
    VoiceEnrollmentManager,
    VoiceProfileNotFoundError,
    VoiceSample,
    build_dubbing_plan,
    create_local_voice_pipeline,
)


# ==================== Helpers ====================

def make_sample(label: str = "sample-1", seconds: float = 4.0,
                sample_rate: int = 16000) -> VoiceSample:
    """Build a fake 16-bit mono PCM sample of the requested length."""
    frames = int(seconds * sample_rate)
    return VoiceSample(
        label=label,
        audio_bytes=b"\x00\x01" * frames,
        sample_rate=sample_rate,
        channels=1,
    )


class FakeStreamingBackend(LocalVoiceBackend):
    """Test backend implementing streaming with canned partials."""

    @property
    def name(self) -> str:
        return "fake-streaming"

    async def capabilities(self) -> Set[LocalCapability]:
        return {
            LocalCapability.TRANSCRIPTION,
            LocalCapability.DICTATION_STREAMING,
        }

    async def enroll_voice(self, samples, design=None) -> Dict[str, Any]:
        return {"artifact": "fake-embedding", "status": "ok"}

    async def synthesize(self, text, profile, config):
        raise ModelNotAvailableError("fake backend has no TTS")

    async def transcribe(self, audio_bytes, language="en"):
        return LocalTranscriptionResult(
            text="full fake transcript",
            confidence=0.99,
            language=language,
            is_partial=False,
            backend=self.name,
        )

    async def transcribe_chunk(self, chunk, context=None):
        idx = (context or {}).get("chunk_index", 0)
        return LocalTranscriptionResult(
            text=f"partial-{idx}",
            confidence=0.8,
            language="en",
            is_partial=True,
            backend=self.name,
        )


# ==================== Registry Tests ====================

class TestLocalVoiceRegistry:
    """Test the local voice profile registry."""

    def test_register_and_get(self):
        """Registered profiles are retrievable by id."""
        registry = LocalVoiceRegistry()
        profile = LocalVoiceProfile(voice_id="v1", display_name="Test Voice")
        registry.register(profile)
        assert registry.get("v1").display_name == "Test Voice"

    def test_get_unknown_raises(self):
        """Getting an unknown id raises VoiceProfileNotFoundError."""
        registry = LocalVoiceRegistry()
        with pytest.raises(VoiceProfileNotFoundError):
            registry.get("nope")

    def test_list_and_remove(self):
        """List returns all profiles; remove deletes by id."""
        registry = LocalVoiceRegistry()
        registry.register(LocalVoiceProfile(voice_id="a", display_name="A"))
        registry.register(LocalVoiceProfile(voice_id="b", display_name="B"))
        assert len(registry.list()) == 2
        assert registry.remove("a") is True
        assert registry.remove("a") is False
        assert [p.voice_id for p in registry.list()] == ["b"]

    def test_serialization_round_trip(self):
        """to_dict/from_dict preserves profiles including design specs."""
        registry = LocalVoiceRegistry()
        design = VoiceDesignSpec(name="design-1", pitch_shift=2.0)
        profile = LocalVoiceProfile(
            voice_id="v9", display_name="Designed", design=design,
            backend_name="null-local-stub",
        )
        registry.register(profile)
        restored = LocalVoiceRegistry.from_dict(registry.to_dict())
        got = restored.get("v9")
        assert got.display_name == "Designed"
        assert got.design is not None
        assert got.design.pitch_shift == 2.0


# ==================== Enrollment Tests ====================

class TestVoiceEnrollment:
    """Test voice enrollment via the stub backend."""

    def test_enroll_with_samples(self):
        """Enrollment stores a profile with sample metadata."""
        manager = VoiceEnrollmentManager()
        profile = asyncio.run(manager.enroll(
            "Isiah Voice", [make_sample(seconds=4.0)], language="en"))
        assert profile.voice_id.startswith("local-")
        assert profile.sample_count == 1
        assert profile.total_sample_seconds == pytest.approx(4.0, abs=0.01)
        assert manager.registry.get(profile.voice_id) is profile

    def test_enroll_rejects_short_samples(self):
        """Samples under the minimum duration raise EnrollmentError."""
        manager = VoiceEnrollmentManager()
        with pytest.raises(EnrollmentError):
            asyncio.run(manager.enroll("Short", [make_sample(seconds=1.0)]))

    def test_enroll_rejects_empty_without_design(self):
        """No samples and no design spec raises EnrollmentError."""
        manager = VoiceEnrollmentManager()
        with pytest.raises(EnrollmentError):
            asyncio.run(manager.enroll("Empty", []))

    def test_enroll_with_design_only(self):
        """A pure parametric design enrolls without audio samples."""
        manager = VoiceEnrollmentManager()
        design = VoiceDesignSpec(name="boardroom", timbre_warmth=0.7)
        profile = asyncio.run(
            manager.enroll("Boardroom", [], design=design))
        assert profile.design is not None
        assert profile.design.timbre_warmth == 0.7

    def test_design_validation(self):
        """Out-of-range design parameters raise EnrollmentError."""
        bad = VoiceDesignSpec(name="bad", pitch_shift=99.0)
        with pytest.raises(EnrollmentError):
            bad.validate()


# ==================== Synthesis Stub Tests ====================

class TestStubSynthesis:
    """Test the stub TTS synthesis contract."""

    def test_synthesize_returns_placeholder_wav(self):
        """Stub returns valid WAV bytes flagged as placeholder."""
        pipeline = create_local_voice_pipeline()
        profile = asyncio.run(
            pipeline.enroll("Narrator", [make_sample(seconds=4.0)]))
        result = asyncio.run(
            pipeline.synthesize("Hello world", profile.voice_id))
        assert result.is_placeholder is True
        assert result.audio_bytes[:4] == b"RIFF"
        assert result.voice_id == profile.voice_id
        assert result.backend == "null-local-stub"

    def test_synthesize_empty_text_raises(self):
        """Empty text raises instead of producing silent audio."""
        from voice.local_voice import LocalVoiceError
        pipeline = create_local_voice_pipeline()
        profile = asyncio.run(
            pipeline.enroll("Narrator", [make_sample(seconds=4.0)]))
        with pytest.raises(LocalVoiceError):
            asyncio.run(pipeline.synthesize("   ", profile.voice_id))

    def test_synthesize_unknown_voice_raises(self):
        """Synthesis with an unenrolled voice id raises."""
        pipeline = create_local_voice_pipeline()
        with pytest.raises(VoiceProfileNotFoundError):
            asyncio.run(pipeline.synthesize("hi", "ghost-voice"))


# ==================== Transcription Stub Tests ====================

class TestStubTranscription:
    """Test the stub transcription behavior."""

    def test_transcribe_raises_not_available(self):
        """Stub transcription raises ModelNotAvailableError honestly."""
        pipeline = create_local_voice_pipeline()
        with pytest.raises(ModelNotAvailableError):
            asyncio.run(pipeline.transcribe(b"\x00" * 32000))

    def test_chunk_transcribe_raises_not_available(self):
        """Stub streaming raises ModelNotAvailableError honestly."""
        backend = NullLocalVoiceBackend()
        with pytest.raises(ModelNotAvailableError):
            asyncio.run(backend.transcribe_chunk(b"\x00" * 1000))

    def test_stub_capabilities_exclude_real_transcription(self):
        """Stub does not advertise TRANSCRIPTION as a real capability."""
        backend = NullLocalVoiceBackend()
        caps = asyncio.run(backend.capabilities())
        assert LocalCapability.TRANSCRIPTION not in caps
        assert LocalCapability.VOICE_ENROLLMENT in caps


# ==================== Dictation Tests ====================

class TestDictationSessions:
    """Test the dictation session manager with a fake streaming backend."""

    def test_start_submit_stop(self):
        """Chunks produce partials; stop returns a transcript summary."""
        manager = DictationSessionManager(backend=FakeStreamingBackend())
        session_id = asyncio.run(manager.start_session(user_id="u1"))
        r1 = asyncio.run(manager.submit_chunk(session_id, b"\x01" * 100))
        r2 = asyncio.run(manager.submit_chunk(session_id, b"\x02" * 100))
        assert r1.is_partial and r1.text == "partial-0"
        assert r2.text == "partial-1"
        summary = asyncio.run(manager.stop_session(session_id))
        assert summary["chunk_count"] == 2
        assert summary["transcript"] == "partial-0 partial-1"

    def test_submit_after_stop_raises(self):
        """Submitting to a stopped session raises DictationError."""
        manager = DictationSessionManager(backend=FakeStreamingBackend())
        session_id = asyncio.run(manager.start_session())
        asyncio.run(manager.stop_session(session_id))
        with pytest.raises(DictationError):
            asyncio.run(manager.submit_chunk(session_id, b"\x01" * 10))

    def test_callbacks_fire(self):
        """on_partial and on_final callbacks are invoked."""
        seen = {"partials": [], "finals": []}
        manager = DictationSessionManager(backend=FakeStreamingBackend())
        session_id = asyncio.run(manager.start_session(
            on_partial=lambda sid, res: seen["partials"].append(res.text),
            on_final=lambda sid, summary: seen["finals"].append(summary),
        ))
        asyncio.run(manager.submit_chunk(session_id, b"\x01" * 10))
        asyncio.run(manager.stop_session(session_id))
        assert seen["partials"] == ["partial-0"]
        assert len(seen["finals"]) == 1

    def test_stub_dictation_raises_on_submit(self):
        """Stub dictation start works; chunk submission raises honestly."""
        pipeline = create_local_voice_pipeline()  # null stub backend
        session_id = asyncio.run(pipeline.dictation.start_session())
        with pytest.raises(ModelNotAvailableError):
            asyncio.run(pipeline.dictation.submit_chunk(session_id, b"\x01" * 10))


# ==================== Dubbing Tests ====================

class TestDubbingPlanning:
    """Test dubbing job planning and timing-map validation."""

    def _enrolled(self) -> LocalVoicePipeline:
        pipeline = create_local_voice_pipeline()
        asyncio.run(pipeline.enroll("Dub Voice", [make_sample(seconds=4.0)]))
        return pipeline

    def _job(self, voice_id: str) -> DubbingJob:
        return DubbingJob(
            source_audio_seconds=60.0,
            target_voice_id=voice_id,
            language="en",
            segments=[
                DubbingSegment(0, 0.0, 10.0, "Hello", "Hola"),
                DubbingSegment(1, 10.0, 25.0, "How are you?"),
            ],
        )

    def test_build_plan(self):
        """A valid job produces an ordered render plan."""
        pipeline = self._enrolled()
        voice_id = pipeline.registry.list()[0].voice_id
        plan = pipeline.plan_dubbing(self._job(voice_id))
        assert isinstance(plan, DubbingRenderPlan)
        assert plan.segment_count == 2
        assert plan.planned_segments[0]["segment_index"] == 0
        assert plan.planned_segments[1]["text"] == "How are you?"
        assert plan.estimated_render_seconds > 0
        assert len(plan.steps) == 5

    def test_unknown_voice_raises(self):
        """Planning with an unenrolled voice raises."""
        pipeline = create_local_voice_pipeline()
        with pytest.raises(VoiceProfileNotFoundError):
            pipeline.plan_dubbing(self._job("ghost-voice"))

    def test_overlapping_segments_raise(self):
        """Overlapping timing segments raise DubbingError."""
        pipeline = self._enrolled()
        voice_id = pipeline.registry.list()[0].voice_id
        job = DubbingJob(
            source_audio_seconds=60.0,
            target_voice_id=voice_id,
            segments=[
                DubbingSegment(0, 0.0, 10.0, "A"),
                DubbingSegment(1, 5.0, 15.0, "B"),
            ],
        )
        with pytest.raises(DubbingError):
            pipeline.plan_dubbing(job)

    def test_segment_beyond_source_raises(self):
        """Segments extending past the source audio raise DubbingError."""
        pipeline = self._enrolled()
        voice_id = pipeline.registry.list()[0].voice_id
        job = DubbingJob(
            source_audio_seconds=10.0,
            target_voice_id=voice_id,
            segments=[DubbingSegment(0, 0.0, 30.0, "Too long")],
        )
        with pytest.raises(DubbingError):
            pipeline.plan_dubbing(job)


# ==================== Facade Tests ====================

class TestPipelineFacade:
    """Test the LocalVoicePipeline facade wiring."""

    def test_factory_defaults_to_stub(self):
        """Factory creates a pipeline with the null stub backend."""
        pipeline = create_local_voice_pipeline()
        assert pipeline.backend.name == "null-local-stub"
        caps = asyncio.run(pipeline.capabilities())
        assert LocalCapability.DUBBING in caps

    def test_shared_registry(self):
        """A passed-in registry is shared across the pipeline."""
        registry = LocalVoiceRegistry()
        pipeline = create_local_voice_pipeline(registry=registry)
        profile = asyncio.run(
            pipeline.enroll("Shared", [make_sample(seconds=4.0)]))
        assert registry.get(profile.voice_id).display_name == "Shared"
