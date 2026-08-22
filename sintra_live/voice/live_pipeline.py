"""Live voice integration pipeline for SP-LIVE-001 I2.

This module connects all live voice components with the existing
governed operating loop, maintaining all C1 authority controls.
"""

import time
import uuid
import threading
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

# Import existing governed loop components
from sintra_live.integration import run_synthetic_mission, SyntheticMissionResult
from sintra_live.mission.mission_manager import MissionManager, MissionState, MissionStateMachine, MissionScope
from sintra_live.identity.principal_fixture import PrincipalFixture
from sintra_live.evidence.evidence_chain import EvidenceChain
from sintra_live.approval.approval import ApprovalManager, ActionEnvelope, ApprovalState

# Import new live voice components
from sintra_live.voice.live_audio_capture import (
    LiveAudioCapture, AudioDeviceManager, CaptureMode, AudioSegment, create_audio_capture
)
from sintra_live.voice.live_stt import LocalSTTManager, TranscriptionResult, create_stt_manager, STTConfig, STTModelType
from sintra_live.voice.live_tts import LocalTTSManager, SynthesisResult, create_tts_manager, TTSConfig, TTSModelType
from sintra_live.voice.principal_session import (
    PrincipalSessionManager, VoiceTranscript, SpokenApproval, SessionState,
    ApprovalPhraseType, create_session_manager
)
from sintra_live.side_effect.hard_disable import (
    SideEffectExecutor, ExecutionRequest, SideEffectType, ExecutionDecision,
    get_i2_executor, verify_i2_hard_disablement
)


class VoicePipelineState(Enum):
    """Voice pipeline states."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    PROCESSING = "PROCESSING"
    GENERATING_RESPONSE = "GENERATING_RESPONSE"
    SPEAKING = "SPEAKING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


@dataclass
class VoiceInteraction:
    """Single voice interaction record."""
    interaction_id: str
    mission_id: str
    session_id: str
    user_transcript: Optional[VoiceTranscript] = None
    stt_result: Optional[TranscriptionResult] = None
    mission_result: Optional[SyntheticMissionResult] = None
    response_text: str = ""
    tts_result: Optional[SynthesisResult] = None
    approval: Optional[SpokenApproval] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    state: VoicePipelineState = VoicePipelineState.IDLE
    error: Optional[str] = None


class LiveVoicePipeline:
    """Main live voice pipeline integrating all components."""

    def __init__(
        self,
        stt_config: STTConfig = None,
        tts_config: TTSConfig = None,
        capture_mode: CaptureMode = CaptureMode.PUSH_TO_TALK
    ):
        # Initialize components
        self.audio_capture = create_audio_capture(capture_mode)
        self.stt_manager = create_stt_manager(stt_config)
        self.tts_manager = create_tts_manager(tts_config)
        self.session_manager = create_session_manager()
        self.side_effect_executor = get_i2_executor()

        # Pipeline state
        self.state = VoicePipelineState.IDLE
        self.current_interaction: Optional[VoiceInteraction] = None
        self.interaction_history: List[VoiceInteraction] = []
        self.mission_manager: Optional[MissionManager] = None
        self.evidence_chain: Optional[EvidenceChain] = None
        self.approval_manager: Optional[ApprovalManager] = None

        # Callbacks
        self.on_transcript: Optional[Callable[[VoiceTranscript], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
        self.on_state_change: Optional[Callable[[VoicePipelineState], None]] = None
        self.on_approval_request: Optional[Callable[[str, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Interruption handling
        self._interrupt_event = threading.Event()
        self._speaking = False

        # Set up TTS interrupt callback
        self.tts_manager.set_interrupt_callback(self._handle_interruption)

        # Set up audio capture callback
        self.audio_capture.set_segment_callback(self._on_audio_segment)

    def _set_state(self, new_state: VoicePipelineState):
        """Update pipeline state."""
        self.state = new_state
        if self.on_state_change:
            self.on_state_change(new_state)

    def _handle_interruption(self):
        """Handle speech interruption."""
        self._interrupt_event.set()
        self._speaking = False
        self._set_state(VoicePipelineState.INTERRUPTED)

    def _on_audio_segment(self, segment: AudioSegment):
        """Callback for completed audio segment."""
        if self.state == VoicePipelineState.LISTENING:
            self._process_audio_segment(segment)

    def _process_audio_segment(self, segment: AudioSegment):
        """Process captured audio segment through STT."""
        self._set_state(VoicePipelineState.TRANSCRIBING)

        # Transcribe
        stt_result = self.stt_manager.transcribe_segment(segment.data, segment.sample_rate)

        # Create voice transcript
        transcript = VoiceTranscript(
            transcript_id=str(uuid.uuid4()),
            text=stt_result.transcript,
            confidence=stt_result.confidence,
            timestamp=stt_result.timestamp,
            is_final=stt_result.is_final,
            session_id=self.session_manager.current_session_id or "",
            segment_id=segment.segment_id,
            alternatives=stt_result.alternatives
        )

        # Add to session
        session = self.session_manager.add_transcript(transcript)

        if self.on_transcript:
            self.on_transcript(transcript)

        # Check for low confidence
        if stt_result.confidence < 0.5:
            self._speak("I didn't catch that clearly. Could you repeat?")
            self._set_state(VoicePipelineState.LISTENING)
            return

        # Process through governed loop
        self.current_interaction = VoiceInteraction(
            interaction_id=str(uuid.uuid4()),
            mission_id="",
            session_id=self.session_manager.current_session_id or ""
        )
        self._process_through_governed_loop(transcript, stt_result)

    def _process_through_governed_loop(self, transcript: VoiceTranscript, stt_result: TranscriptionResult):
        """Process transcript through the governed operating loop."""
        self._set_state(VoicePipelineState.PROCESSING)

        # Initialize mission if needed
        if not self.mission_manager:
            state_machine = MissionStateMachine()
            self.mission_manager = MissionManager(state_machine)
            self.evidence_chain = EvidenceChain(self.mission_manager.get_mission_id())
            self.approval_manager = ApprovalManager(self.mission_manager.get_mission_id())

        # Create interaction record if not exists
        if not self.current_interaction:
            self.current_interaction = VoiceInteraction(
                interaction_id=str(uuid.uuid4()),
                mission_id=self.mission_manager.get_mission_id() if self.mission_manager else "",
                session_id=self.session_manager.current_session_id or ""
            )

        # Create synthetic voice input for existing integration
        from sintra_live.voice.synthetic_voice_io import SyntheticVoiceInputAdapter, create_voice_fixture

        # Convert live transcript to synthetic format for existing pipeline
        voice_fixture = create_voice_fixture()
        voice_fixture["transcript"] = transcript.text
        voice_fixture["confidence"] = transcript.confidence
        voice_fixture["request_id"] = transcript.transcript_id
        voice_fixture["session_id"] = self.session_manager.current_session_id or ""
        voice_fixture["principal_id"] = "principal-001"

        # Run through existing governed loop (pass fixture dict, not adapter output)
        try:
            mission_result = run_synthetic_mission(voice_fixture)
            self.current_interaction.mission_id = mission_result.mission_id
            self.current_interaction.mission_result = mission_result
            self.current_interaction.stt_result = stt_result
            self.current_interaction.user_transcript = transcript

            # Generate response from mission result
            response_text = self._generate_response(mission_result)

            # Check if approval is needed
            if mission_result.test_results.get("approval_required_before_execution"):
                self._request_approval(mission_result, transcript)
            else:
                self._speak(response_text)

        except Exception as e:
            self._handle_error(str(e))

    def _generate_response(self, mission_result: SyntheticMissionResult) -> str:
        """Generate spoken response from mission result."""
        if mission_result.brief:
            # Use the principal brief as response
            return mission_result.brief.written_text[:500]  # Limit length for speech
        elif mission_result.test_results.get("mission_complete"):
            return "Mission completed successfully."
        else:
            return "I'm processing your request."

    def _request_approval(self, mission_result: SyntheticMissionResult, transcript: VoiceTranscript):
        """Request spoken approval for consequential action."""
        self._set_state(VoicePipelineState.WAITING_APPROVAL)

        # Get action hash from evidence
        action_hash = ""
        if mission_result.evidence_chain:
            records = mission_result.evidence_chain.get_all_records()
            for r in records:
                if r["type"] == "approval_requested" and "action_hash" in r["content"]:
                    action_hash = r["content"]["action_hash"]
                    break

        # Request approval through session manager
        approval = self.session_manager.request_approval(
            mission_id=mission_result.mission_id,
            action_hash=action_hash,
            action_description="Consequential action proposed"
        )

        # Speak the approval request
        request_text = f"I'm proposing an action that requires your approval. The action hash is {action_hash[:16]}. Do you approve?"
        self._speak(request_text)

        if self.on_approval_request:
            self.on_approval_request(approval.approval_id, action_hash)

    def _process_approval_response(self, transcript: VoiceTranscript):
        """Process Principal's approval response."""
        approval = self.session_manager.process_approval_response(transcript)

        if not approval:
            self._speak("I didn't detect a pending approval request.")
            self._set_state(VoicePipelineState.LISTENING)
            return

        binding = self.session_manager.get_approval_binding(approval)

        if approval.phrase_type == ApprovalPhraseType.EXPLICIT_APPROVAL:
            if self.session_manager.is_approval_valid(approval):
                self._speak(f"Approval received and bound to action hash {approval.action_hash[:16]}. However, external execution is disabled during this certification phase.")
            else:
                self._speak("Approval received but confidence is too low. Please repeat clearly.")
                self._set_state(VoicePipelineState.WAITING_APPROVAL)
        elif approval.phrase_type in (ApprovalPhraseType.EXPLICIT_REJECTION, ApprovalPhraseType.CANCELLATION):
            self._speak("Action rejected. No execution will occur.")
        else:
            self._speak("I couldn't understand your response clearly. Please say yes to approve or no to reject.")
            self._set_state(VoicePipelineState.WAITING_APPROVAL)

    def _speak(self, text: str):
        """Speak text using TTS."""
        if not text:
            return

        self._speaking = True
        self._interrupt_event.clear()
        self._set_state(VoicePipelineState.SPEAKING)

        # Synthesize and play
        def playback_callback(audio_data: bytes):
            # In real implementation, play audio
            # For mock, just simulate
            pass

        try:
            tts_result = self.tts_manager.synthesize(text)
            self.current_interaction.tts_result = tts_result
            self.current_interaction.response_text = text

            if self.on_response:
                self.on_response(text)

            # Simulate playback duration
            time.sleep(tts_result.duration_ms / 1000.0)

        except Exception as e:
            self._handle_error(str(e))
        finally:
            self._speaking = False
            if self.state == VoicePipelineState.SPEAKING:
                self._set_state(VoicePipelineState.LISTENING)

    def _handle_error(self, error: str):
        """Handle pipeline error."""
        self._set_state(VoicePipelineState.ERROR)
        if self.current_interaction:
            self.current_interaction.error = error
        if self.on_error:
            self.on_error(error)

    def start_session(self, principal_id: str = "principal-001") -> str:
        """Start a new Principal voice session."""
        session = self.session_manager.create_session(principal_id)
        self._set_state(VoicePipelineState.LISTENING)
        self.audio_capture.start_capture()
        return session.session_id

    def push_to_talk(self):
        """Start push-to-talk capture."""
        self.audio_capture.push_to_talk_start()

    def release_to_talk(self):
        """End push-to-talk and process."""
        segment = self.audio_capture.push_to_talk_end()
        if segment:
            self._process_audio_segment(segment)

    def stop_session(self):
        """Stop the current voice session."""
        self.audio_capture.stop_capture()
        self.session_manager.cleanup_expired_sessions()
        self._set_state(VoicePipelineState.IDLE)

    def get_interaction_history(self) -> List[VoiceInteraction]:
        """Get interaction history."""
        return self.interaction_history

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status for diagnostics."""
        return {
            "state": self.state.value,
            "session_active": self.session_manager.current_session_id is not None,
            "session_id": self.session_manager.current_session_id,
            "stt_info": self.stt_manager.get_model_info(),
            "tts_info": self.tts_manager.get_model_info(),
            "audio_devices": {
                "input": [d.device_id for d in self.audio_capture.device_manager.get_input_devices()],
                "output": [d.device_id for d in self.audio_capture.device_manager.get_output_devices()],
            },
            "side_effect_status": verify_i2_hard_disablement(),
            "interactions_count": len(self.interaction_history),
        }


def create_live_voice_pipeline(
    stt_config: STTConfig = None,
    tts_config: TTSConfig = None,
    capture_mode: CaptureMode = CaptureMode.PUSH_TO_TALK
) -> LiveVoicePipeline:
    """Factory function to create live voice pipeline."""
    return LiveVoicePipeline(stt_config, tts_config, capture_mode)