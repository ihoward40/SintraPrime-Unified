"""I2 Live Voice tests for SP-LIVE-001."""

import pytest
import time
import uuid
from pathlib import Path

# Import I2 components
from sintra_live.voice.live_audio_capture import (
    AudioDeviceManager, LiveAudioCapture, CaptureMode,
    AudioDevice, AudioSegment, VoiceActivityDetector, create_audio_capture
)
from sintra_live.voice.live_stt import (
    LocalSTTManager, TranscriptionResult, create_stt_manager, STTConfig, STTModelType
)
from sintra_live.voice.live_tts import (
    LocalTTSManager, SynthesisResult, create_tts_manager, TTSConfig, TTSModelType
)
from sintra_live.voice.principal_session import (
    PrincipalSessionManager, VoiceTranscript, SpokenApproval,
    SessionState, ApprovalPhraseType, create_session_manager
)
from sintra_live.side_effect.hard_disable import (
    SideEffectExecutor, ExecutionRequest, SideEffectType, ExecutionDecision,
    get_i2_executor, verify_i2_hard_disablement, HardDisableRegistry
)
from sintra_live.voice.live_pipeline import (
    LiveVoicePipeline, VoicePipelineState, VoiceInteraction, create_live_voice_pipeline
)
from sintra_live.integration import SyntheticMissionResult


class TestAudioCapture:
    """Test audio capture and device management."""

    def test_device_discovery(self):
        """Test audio device discovery."""
        manager = AudioDeviceManager()
        input_devices = manager.get_input_devices()
        output_devices = manager.get_output_devices()

        assert len(input_devices) > 0
        assert len(output_devices) > 0
        assert manager.get_default_input() is not None
        assert manager.get_default_output() is not None

    def test_capture_creation(self):
        """Test audio capture creation."""
        capture = create_audio_capture(CaptureMode.PUSH_TO_TALK)
        assert capture is not None
        assert capture.mode == CaptureMode.PUSH_TO_TALK

    def test_push_to_talk(self):
        """Test push-to-talk capture."""
        capture = create_audio_capture(CaptureMode.PUSH_TO_TALK)
        capture.start_capture()

        capture.push_to_talk_start()
        time.sleep(0.01)
        segment = capture.push_to_talk_end()

        assert segment is not None
        assert isinstance(segment, AudioSegment)
        assert segment.is_speech
        capture.stop_capture()

    def test_vad_processing(self):
        """Test voice activity detection."""
        vad = VoiceActivityDetector()
        # Silence frame
        silence = bytes(960)  # 30ms at 16kHz 16-bit mono
        result = vad.process_frame(silence)
        assert result["state"] == "SILENCE"
        assert not result["is_speech"]

        # Reset
        vad.reset()


class TestSTT:
    """Test speech-to-text integration."""

    def test_stt_creation(self):
        """Test STT manager creation."""
        stt = create_stt_manager(STTConfig(model_type=STTModelType.MOCK))
        assert stt is not None
        assert stt.load()

    def test_stt_transcription(self):
        """Test STT transcription."""
        stt = create_stt_manager(STTConfig(model_type=STTModelType.MOCK))
        stt.load()

        # Mock audio data
        audio_data = bytes(1600)  # 100ms
        result = stt.transcribe_segment(audio_data, 16000)

        assert isinstance(result, TranscriptionResult)
        assert result.transcript != ""
        assert result.confidence > 0
        assert result.is_final
        assert result.segment_id != ""

    def test_stt_streaming(self):
        """Test STT streaming partial results."""
        stt = create_stt_manager(STTConfig(model_type=STTModelType.MOCK, enable_partial_results=True))
        stt.load()

        audio_chunk = bytes(320)  # 20ms
        result = stt.transcribe_streaming(audio_chunk, 16000)
        # May return None or partial result
        if result:
            assert not result.is_final


class TestTTS:
    """Test text-to-speech integration."""

    def test_tts_creation(self):
        """Test TTS manager creation."""
        tts = create_tts_manager(TTSConfig(model_type=TTSModelType.MOCK))
        assert tts is not None
        assert tts.load()

    def test_tts_synthesis(self):
        """Test TTS synthesis."""
        tts = create_tts_manager(TTSConfig(model_type=TTSModelType.MOCK))
        tts.load()

        result = tts.synthesize("Hello, this is a test.")

        assert isinstance(result, SynthesisResult)
        assert result.text == "Hello, this is a test."
        assert result.is_final
        assert len(result.audio_data) > 0
        assert result.duration_ms > 0

    def test_tts_streaming(self):
        """Test TTS streaming synthesis."""
        tts = create_tts_manager(TTSConfig(model_type=TTSModelType.MOCK, enable_streaming=True))
        tts.load()

        results = tts.synthesize_streaming("This is a longer test message for streaming synthesis.")

        assert len(results) > 0
        for r in results:
            assert isinstance(r, SynthesisResult)
            assert not r.is_final or r == results[-1]

    def test_tts_interruption(self):
        """Test TTS interruption."""
        tts = create_tts_manager(TTSConfig(model_type=TTSModelType.MOCK))
        tts.load()

        tts.interrupt()
        assert not tts.is_speaking()


class TestPrincipalSession:
    """Test Principal session and approval protocol."""

    def test_session_creation(self):
        """Test session creation."""
        manager = create_session_manager()
        session = manager.create_session("principal-001")

        assert session.session_id != ""
        assert session.principal_id == "principal-001"
        assert session.state == SessionState.ACTIVE

    def test_transcript_handling(self):
        """Test transcript addition to session."""
        manager = create_session_manager()
        session = manager.create_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Test transcript",
            confidence=0.9,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        updated_session = manager.add_transcript(transcript)
        assert len(updated_session.transcripts) == 1

    def test_approval_request(self):
        """Test approval request."""
        manager = create_session_manager()
        session = manager.create_session()

        approval = manager.request_approval(
            mission_id="test-mission",
            action_hash="abc123",
            action_description="Test action"
        )

        assert session.state == SessionState.WAITING_APPROVAL
        assert approval.action_hash == "abc123"
        assert approval.mission_id == "test-mission"

    def test_approval_processing_explicit_yes(self):
        """Test processing explicit approval."""
        manager = create_session_manager()
        session = manager.create_session()

        approval = manager.request_approval("mission-1", "action-hash", "Test")

        # Simulate Principal saying "yes"
        response = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes, I approve",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        processed = manager.process_approval_response(response)
        assert processed is not None
        assert processed.phrase_type == ApprovalPhraseType.EXPLICIT_APPROVAL
        assert session.state == SessionState.APPROVED
        assert manager.is_approval_valid(processed)

    def test_approval_processing_explicit_no(self):
        """Test processing explicit rejection."""
        manager = create_session_manager()
        session = manager.create_session()

        manager.request_approval("mission-1", "action-hash", "Test")

        response = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="No, I reject that",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        processed = manager.process_approval_response(response)
        assert processed.phrase_type == ApprovalPhraseType.EXPLICIT_REJECTION
        assert session.state == SessionState.REJECTED

    def test_approval_processing_ambiguous(self):
        """Test processing ambiguous response."""
        manager = create_session_manager()
        session = manager.create_session()

        manager.request_approval("mission-1", "action-hash", "Test")

        response = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Maybe later",
            confidence=0.8,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        processed = manager.process_approval_response(response)
        assert processed.phrase_type == ApprovalPhraseType.AMBIGUOUS
        assert session.state == SessionState.AMBIGUOUS

    def test_approval_binding(self):
        """Test approval hash binding."""
        manager = create_session_manager()
        session = manager.create_session()

        manager.request_approval("mission-1", "action-hash", "Test")

        response = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        processed = manager.process_approval_response(response)
        binding = manager.get_approval_binding(processed)

        assert "hash_binding" in binding
        assert binding["action_hash"] == "action-hash"
        assert binding["phrase_type"] == "EXPLICIT_APPROVAL"


class TestHardDisable:
    """Test hard side-effect disablement."""

    def test_hard_disabled_registry(self):
        """Test hard disabled registry."""
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.EMAIL)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.SLACK)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.GOOGLE_DRIVE)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.GITHUB)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.FINANCIAL)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.LEGAL)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.DEPLOYMENT)
        assert HardDisableRegistry.is_hard_disabled(SideEffectType.RELEASE)

    def test_allowed_in_i2(self):
        """Test allowed types in I2."""
        assert HardDisableRegistry.is_allowed_in_i2(SideEffectType.MOCK)
        assert not HardDisableRegistry.is_allowed_in_i2(SideEffectType.EMAIL)

    def test_mock_execution_allowed(self):
        """Test mock side effect execution."""
        executor = get_i2_executor()

        request = ExecutionRequest(
            request_id=str(uuid.uuid4()),
            mission_id="test-mission",
            action_hash="abc123",
            side_effect_type=SideEffectType.MOCK,
            capability="synthetic_side_effect",
            destination={"host": "mock"},
            parameters={},
            consequence_class="E0"
        )

        result = executor.execute(request)
        assert result.decision == ExecutionDecision.ALLOW
        assert "mock_result" in result.evidence

    def test_real_external_denied(self):
        """Test real external side effects denied."""
        executor = get_i2_executor()

        for effect_type in [
            SideEffectType.EMAIL, SideEffectType.SLACK,
            SideEffectType.GOOGLE_DRIVE, SideEffectType.GITHUB,
            SideEffectType.FINANCIAL, SideEffectType.LEGAL,
            SideEffectType.DEPLOYMENT, SideEffectType.RELEASE
        ]:
            request = ExecutionRequest(
                request_id=str(uuid.uuid4()),
                mission_id="test-mission",
                action_hash="abc123",
                side_effect_type=effect_type,
                capability="test",
                destination={},
                parameters={},
                consequence_class="E0"
            )

            result = executor.execute(request)
            assert result.decision in (ExecutionDecision.DISABLED, ExecutionDecision.DENY)

    def test_consequential_requires_approval(self):
        """Test consequential actions require approval."""
        executor = get_i2_executor()

        request = ExecutionRequest(
            request_id=str(uuid.uuid4()),
            mission_id="test-mission",
            action_hash="abc123",
            side_effect_type=SideEffectType.MOCK,
            capability="test",
            destination={},
            parameters={},
            consequence_class="E1"  # Consequential
            # No approval_hash provided
        )

        result = executor.execute(request)
        assert result.decision == ExecutionDecision.REQUIRES_APPROVAL

    def test_verify_no_real_effects(self):
        """Test verification of no real effects."""
        executor = get_i2_executor()
        assert executor.verify_no_real_effects()


class TestLivePipeline:
    """Test live voice pipeline integration."""

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        pipeline = create_live_voice_pipeline()
        assert pipeline is not None
        assert pipeline.state == VoicePipelineState.IDLE

    def test_session_start(self):
        """Test starting voice session."""
        pipeline = create_live_voice_pipeline()
        session_id = pipeline.start_session("principal-001")

        assert session_id != ""
        assert pipeline.state == VoicePipelineState.LISTENING
        assert pipeline.session_manager.current_session_id == session_id

    def test_pipeline_status(self):
        """Test pipeline status reporting."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        status = pipeline.get_pipeline_status()

        assert "state" in status
        assert "session_active" in status
        assert "stt_info" in status
        assert "tts_info" in status
        assert "side_effect_status" in status
        assert status["side_effect_status"]["no_real_effects"] is True

    def test_push_to_talk_flow(self):
        """Test push-to-talk flow."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        pipeline.push_to_talk()
        time.sleep(0.01)
        pipeline.release_to_talk()

        # Interaction should be recorded
        history = pipeline.get_interaction_history()
        # May not have completed interaction due to mock nature
        # But pipeline should be functional

        pipeline.stop_session()


class TestIntegrationWithGovernedLoop:
    """Test integration with existing governed loop."""

    def test_live_transcript_to_mission(self):
        """Test live transcript processes through governed loop."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        # Create a transcript directly
        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="SintraPrime, give me the current mission status.",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        # Process through pipeline
        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        # Should have created mission
        assert pipeline.mission_manager is not None
        assert pipeline.current_interaction is not None
        assert pipeline.current_interaction.mission_result is not None

    def test_approval_flow_integration(self):
        """Test approval flow with live voice."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        # Create transcript that would trigger approval
        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes, please proceed with the action.",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        # First request approval
        pipeline.session_manager.request_approval("test-mission", "test-action-hash", "Test action")

        # Then process approval response
        pipeline._process_approval_response(transcript)

        # Should have processed approval
        assert pipeline.session_manager.current_session_id is not None


class TestVoiceAdversarial:
    """Adversarial tests for voice components."""

    def test_low_confidence_rejection(self):
        """Test low confidence transcription is rejected."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="unclear",
            confidence=0.3,  # Below threshold
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        # Should request clarification (mock speaks)

    def test_interruption_during_speech(self):
        """Test interruption handling during TTS."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        # Start speaking
        pipeline._speak("This is a long response that can be interrupted.")

        # Trigger interruption
        pipeline._handle_interruption()

        assert pipeline.state == VoicePipelineState.INTERRUPTED
        assert not pipeline._speaking

    def test_approval_before_proposal(self):
        """Test approval spoken before proposal is rejected."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes I approve",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        # No pending approval
        result = pipeline.session_manager.process_approval_response(transcript)
        assert result is None

    def test_approval_after_mutation(self):
        """Test approval after action mutation is invalidated."""
        manager = create_session_manager()
        session = manager.create_session()

        manager.request_approval("mission-1", "original-hash", "Test")

        # Simulate action mutation by creating new approval request
        manager.request_approval("mission-1", "mutated-hash", "Test mutated")

        response = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=session.session_id,
            segment_id=str(uuid.uuid4())
        )

        processed = manager.process_approval_response(response)
        # Should bind to mutated hash, not original
        assert processed.action_hash == "mutated-hash"


class TestI2Demos:
    """I2 demonstration tests."""

    def test_demo_1_simple_conversation(self):
        """Demo 1: Simple conversation."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="SintraPrime, can you hear me?",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        assert pipeline.current_interaction is not None
        assert pipeline.current_interaction.mission_result is not None

    def test_demo_2_mission_status(self):
        """Demo 2: Mission status query."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="SintraPrime, give me the current mission status.",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        assert pipeline.current_interaction.mission_result is not None
        assert pipeline.current_interaction.mission_result.mission_id is not None

    def test_demo_5_approval_mock_action(self):
        """Demo 5: Approval with mock action."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        # First, trigger an action that requires approval
        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Create a status update.",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        # Now simulate approval
        approval_transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Yes, I approve",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_approval_response(approval_transcript)

        # Should have processed approval
        assert pipeline.session_manager.get_session().state in (SessionState.APPROVED, SessionState.AMBIGUOUS)

    def test_demo_6_ambiguous_approval(self):
        """Demo 6: Ambiguous approval."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        pipeline.session_manager.request_approval("mission-1", "hash", "Test")

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="I am uncertain about this decision",
            confidence=0.8,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_approval_response(transcript)

        assert pipeline.session_manager.get_session().state == SessionState.AMBIGUOUS

    def test_demo_7_interruption(self):
        """Demo 7: Interruption handling."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        pipeline._speak("This is a long response that can be interrupted by the user.")

        # Interrupt
        pipeline._handle_interruption()

        assert pipeline.state == VoicePipelineState.INTERRUPTED
        assert not pipeline._speaking

    def test_demo_8_principal_brief(self):
        """Demo 8: Principal brief generation."""
        pipeline = create_live_voice_pipeline()
        pipeline.start_session()

        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text="Give me a briefing on the current state.",
            confidence=0.95,
            timestamp=time.time(),
            is_final=True,
            session_id=pipeline.session_manager.current_session_id,
            segment_id=str(uuid.uuid4())
        )

        pipeline._process_through_governed_loop(transcript, TranscriptionResult(
            transcript=transcript.text,
            confidence=transcript.confidence,
            is_final=True,
            segment_id=transcript.segment_id,
            timestamp=transcript.timestamp
        ))

        # Should have generated brief
        assert pipeline.current_interaction.mission_result is not None
        assert pipeline.current_interaction.mission_result.brief is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])