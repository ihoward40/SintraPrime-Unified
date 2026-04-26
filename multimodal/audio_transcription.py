"""
audio_transcription.py — Legal audio transcription with speaker diarization.

Transcribes legal recordings: depositions, hearings, client calls.
Provides speaker diarization, legal-context awareness, and action item extraction.

Supports:
- OpenAI Whisper API
- Local Whisper (faster-whisper or whisper.cpp)
- Structured transcript output: {speaker, timestamp, text, confidence}
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

try:
    from faster_whisper import WhisperModel as FasterWhisperModel  # type: ignore
    FASTER_WHISPER_AVAILABLE = True
    logger.info("faster-whisper available.")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    import whisper as local_whisper  # type: ignore
    LOCAL_WHISPER_AVAILABLE = True
    logger.info("openai-whisper (local) available.")
except ImportError:
    LOCAL_WHISPER_AVAILABLE = False

try:
    from openai import OpenAI as _OpenAI  # type: ignore
    OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    OPENAI_WHISPER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TranscriptionBackend(str, Enum):
    OPENAI_API = "openai_api"
    FASTER_WHISPER = "faster_whisper"
    LOCAL_WHISPER = "local_whisper"
    MOCK = "mock"


class LegalRecordingType(str, Enum):
    DEPOSITION = "deposition"
    HEARING = "hearing"
    CLIENT_CALL = "client_call"
    MEDIATION = "mediation"
    ARBITRATION = "arbitration"
    TELEPHONE_CONFERENCE = "telephone_conference"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TranscriptSegment:
    speaker: str
    timestamp_start: float  # seconds
    timestamp_end: float
    text: str
    confidence: float = 1.0
    is_question: bool = False
    is_objection: bool = False

    @property
    def timestamp_str(self) -> str:
        def fmt(s: float) -> str:
            m = int(s // 60)
            sec = s % 60
            return f"{m:02d}:{sec:05.2f}"
        return f"{fmt(self.timestamp_start)} --> {fmt(self.timestamp_end)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "timestamp_str": self.timestamp_str,
            "text": self.text,
            "confidence": self.confidence,
            "is_question": self.is_question,
            "is_objection": self.is_objection,
        }


@dataclass
class ActionItem:
    description: str
    assigned_to: Optional[str] = None
    deadline: Optional[str] = None
    timestamp_context: Optional[str] = None
    source_segment_idx: int = 0


@dataclass
class SpeakerProfile:
    label: str          # "Speaker 1", "ATTORNEY", etc.
    identified_name: Optional[str] = None
    role: Optional[str] = None  # attorney, witness, judge, client
    total_words: int = 0
    total_speaking_time: float = 0.0  # seconds
    segment_count: int = 0


@dataclass
class TranscriptionResult:
    file_path: Optional[str] = None
    recording_type: LegalRecordingType = LegalRecordingType.UNKNOWN
    duration_seconds: float = 0.0
    language: str = "en"
    segments: List[TranscriptSegment] = field(default_factory=list)
    speakers: List[SpeakerProfile] = field(default_factory=list)
    full_text: str = ""
    action_items: List[ActionItem] = field(default_factory=list)
    key_legal_terms: List[str] = field(default_factory=list)
    objections: List[Dict[str, Any]] = field(default_factory=list)
    backend_used: str = ""
    model_used: str = ""
    confidence_avg: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "recording_type": self.recording_type.value,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "segment_count": len(self.segments),
            "segments": [s.to_dict() for s in self.segments],
            "speakers": [
                {
                    "label": sp.label,
                    "name": sp.identified_name,
                    "role": sp.role,
                    "words": sp.total_words,
                    "speaking_time": sp.total_speaking_time,
                }
                for sp in self.speakers
            ],
            "full_text": self.full_text,
            "action_items": [
                {
                    "description": ai.description,
                    "assigned_to": ai.assigned_to,
                    "deadline": ai.deadline,
                }
                for ai in self.action_items
            ],
            "key_legal_terms": self.key_legal_terms,
            "objections": self.objections,
            "backend_used": self.backend_used,
            "model_used": self.model_used,
            "confidence_avg": self.confidence_avg,
            "warnings": self.warnings,
        }

    def to_srt(self) -> str:
        """Export transcript in SRT subtitle format."""
        lines = []
        for idx, seg in enumerate(self.segments, start=1):
            lines.append(str(idx))
            lines.append(seg.timestamp_str.replace("-->", "-->"))
            lines.append(f"[{seg.speaker}] {seg.text}")
            lines.append("")
        return "\n".join(lines)

    def to_plaintext(self) -> str:
        """Export transcript as plain text with speaker labels."""
        lines = []
        for seg in self.segments:
            ts = seg.timestamp_str.split(" -->")[0]
            lines.append(f"[{ts}] {seg.speaker}: {seg.text}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Legal terminology
# ---------------------------------------------------------------------------

LEGAL_TERMS = [
    "objection", "overruled", "sustained", "hearsay", "speculation",
    "leading", "foundation", "relevance", "privilege", "stipulate",
    "deponent", "exhibit", "subpoena", "sworn", "affidavit", "perjury",
    "counsel", "attorney", "court reporter", "transcript", "deposition",
    "cross-examination", "direct examination", "redirect", "recross",
    "motion in limine", "voir dire", "res judicata", "habeas corpus",
    "injunction", "contempt", "sanctions", "discovery", "interrogatory",
    "request for production", "request for admission", "expert witness",
    "lay witness", "fact witness", "damages", "liability", "negligence",
    "breach", "contract", "tort", "statute of limitations",
]

OBJECTION_PATTERNS = re.compile(
    r"\b(objection|object)\b.*?(?:\.|$)",
    re.IGNORECASE | re.MULTILINE,
)

ACTION_PATTERNS = re.compile(
    r"\b(?:will|shall|must|need to|going to|agree to|commit to)\s+([^.!?]{10,80})",
    re.IGNORECASE,
)

SPEAKER_ROLE_KEYWORDS = {
    "attorney": ["counsel", "attorney", "esquire", "esq", "mr.", "ms.", "mrs.", "judge"],
    "witness": ["witness", "deponent", "testify", "sworn"],
    "judge": ["judge", "justice", "your honor", "the court"],
    "clerk": ["clerk", "reporter", "court reporter"],
}

DEADLINE_PATTERNS = re.compile(
    r"\b(?:by|before|no later than|within|due|deadline)\s+([^\.,;]{5,40})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Transcription engine
# ---------------------------------------------------------------------------

class LegalAudioTranscriber:
    """
    Legal audio transcription engine with speaker diarization support.

    Priority order for backends:
    1. OpenAI Whisper API (cloud, best accuracy)
    2. faster-whisper (local, good accuracy)
    3. openai-whisper (local, original)
    """

    SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        preferred_backend: Optional[TranscriptionBackend] = None,
        model: str = "whisper-1",
        local_model_size: str = "base",
        language: Optional[str] = None,
    ):
        self.model = model
        self.local_model_size = local_model_size
        self.language = language
        self._openai_client = None
        self._local_model = None

        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if key and OPENAI_WHISPER_AVAILABLE:
            self._openai_client = _OpenAI(api_key=key)

        if preferred_backend:
            self.backend = preferred_backend
        else:
            self.backend = self._auto_select_backend()

    def _auto_select_backend(self) -> TranscriptionBackend:
        if self._openai_client:
            return TranscriptionBackend.OPENAI_API
        if FASTER_WHISPER_AVAILABLE:
            return TranscriptionBackend.FASTER_WHISPER
        if LOCAL_WHISPER_AVAILABLE:
            return TranscriptionBackend.LOCAL_WHISPER
        return TranscriptionBackend.MOCK

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def transcribe_file(self, file_path: str | Path) -> TranscriptionResult:
        """Transcribe an audio file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {path.suffix}. Supported: {self.SUPPORTED_FORMATS}")

        result = TranscriptionResult(
            file_path=str(path),
            backend_used=self.backend.value,
            model_used=self.model,
        )

        if self.backend == TranscriptionBackend.OPENAI_API:
            self._transcribe_openai(path, result)
        elif self.backend == TranscriptionBackend.FASTER_WHISPER:
            self._transcribe_faster_whisper(path, result)
        elif self.backend == TranscriptionBackend.LOCAL_WHISPER:
            self._transcribe_local_whisper(path, result)
        else:
            result.warnings.append("No transcription backend available. Returning empty result.")

        # Post-processing
        self._build_full_text(result)
        self._detect_recording_type(result)
        self._extract_legal_terms(result)
        self._extract_objections(result)
        self._extract_action_items(result)
        self._build_speaker_profiles(result)
        self._compute_avg_confidence(result)

        return result

    def transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.mp3") -> TranscriptionResult:
        """Transcribe audio from bytes."""
        suffix = Path(filename).suffix or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)
        try:
            return self.transcribe_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # OpenAI Whisper API backend
    # ------------------------------------------------------------------

    def _transcribe_openai(self, path: Path, result: TranscriptionResult) -> None:
        try:
            with open(path, "rb") as audio_file:
                kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "file": audio_file,
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["segment", "word"],
                }
                if self.language:
                    kwargs["language"] = self.language

                response = self._openai_client.audio.transcriptions.create(**kwargs)

            result.language = getattr(response, "language", "en")
            result.duration_seconds = getattr(response, "duration", 0.0)

            raw_segments = getattr(response, "segments", [])
            if raw_segments:
                result.segments = self._parse_openai_segments(raw_segments)
            else:
                # No segment data — wrap full text in one segment
                full = getattr(response, "text", "")
                result.segments = [
                    TranscriptSegment(
                        speaker="Speaker 1",
                        timestamp_start=0.0,
                        timestamp_end=result.duration_seconds,
                        text=full,
                        confidence=1.0,
                    )
                ]
        except Exception as e:
            logger.error("OpenAI transcription failed: %s", e)
            result.warnings.append(f"OpenAI transcription error: {e}")

    def _parse_openai_segments(self, raw_segments: List[Any]) -> List[TranscriptSegment]:
        segments = []
        current_speaker = "Speaker 1"
        speaker_counter = 1

        for seg in raw_segments:
            text = seg.get("text", "").strip() if isinstance(seg, dict) else getattr(seg, "text", "").strip()
            start = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
            end = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
            avg_logprob = seg.get("avg_logprob", 0.0) if isinstance(seg, dict) else getattr(seg, "avg_logprob", 0.0)
            confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))

            # Heuristic speaker change on silence >2s
            if segments and start - segments[-1].timestamp_end > 2.0:
                speaker_counter += 1
                current_speaker = f"Speaker {speaker_counter}"

            is_obj = bool(re.search(r"\bobjection\b", text, re.IGNORECASE))
            is_q = text.strip().endswith("?")

            segments.append(
                TranscriptSegment(
                    speaker=current_speaker,
                    timestamp_start=float(start),
                    timestamp_end=float(end),
                    text=text,
                    confidence=float(confidence),
                    is_question=is_q,
                    is_objection=is_obj,
                )
            )
        return segments

    # ------------------------------------------------------------------
    # faster-whisper backend
    # ------------------------------------------------------------------

    def _transcribe_faster_whisper(self, path: Path, result: TranscriptionResult) -> None:
        try:
            if not self._local_model:
                self._local_model = FasterWhisperModel(self.local_model_size)
            segments, info = self._local_model.transcribe(
                str(path),
                language=self.language,
                word_timestamps=True,
                vad_filter=True,
            )
            result.language = info.language
            result.duration_seconds = info.duration

            parsed: List[TranscriptSegment] = []
            speaker_counter = 1
            current_speaker = "Speaker 1"
            last_end = 0.0

            for seg in segments:
                if parsed and seg.start - last_end > 2.0:
                    speaker_counter += 1
                    current_speaker = f"Speaker {speaker_counter}"
                text = seg.text.strip()
                parsed.append(
                    TranscriptSegment(
                        speaker=current_speaker,
                        timestamp_start=seg.start,
                        timestamp_end=seg.end,
                        text=text,
                        confidence=getattr(seg, "avg_logprob", 0.0) + 1.0,
                        is_question=text.endswith("?"),
                        is_objection=bool(re.search(r"\bobjection\b", text, re.IGNORECASE)),
                    )
                )
                last_end = seg.end

            result.segments = parsed
        except Exception as e:
            logger.error("faster-whisper transcription failed: %s", e)
            result.warnings.append(f"faster-whisper error: {e}")

    # ------------------------------------------------------------------
    # Local whisper backend
    # ------------------------------------------------------------------

    def _transcribe_local_whisper(self, path: Path, result: TranscriptionResult) -> None:
        try:
            if not self._local_model:
                self._local_model = local_whisper.load_model(self.local_model_size)
            output = self._local_model.transcribe(str(path), verbose=False)
            result.language = output.get("language", "en")

            segments = output.get("segments", [])
            parsed: List[TranscriptSegment] = []
            speaker_counter = 1
            current_speaker = "Speaker 1"

            for seg in segments:
                text = seg.get("text", "").strip()
                start = seg.get("start", 0.0)
                end = seg.get("end", 0.0)

                if parsed and start - parsed[-1].timestamp_end > 2.0:
                    speaker_counter += 1
                    current_speaker = f"Speaker {speaker_counter}"

                parsed.append(
                    TranscriptSegment(
                        speaker=current_speaker,
                        timestamp_start=start,
                        timestamp_end=end,
                        text=text,
                        confidence=min(1.0, max(0.0, seg.get("avg_logprob", 0.0) + 1.0)),
                        is_question=text.endswith("?"),
                        is_objection=bool(re.search(r"\bobjection\b", text, re.IGNORECASE)),
                    )
                )

            result.segments = parsed
            if segments:
                result.duration_seconds = segments[-1].get("end", 0.0)
        except Exception as e:
            logger.error("Local whisper transcription failed: %s", e)
            result.warnings.append(f"Local whisper error: {e}")

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _build_full_text(self, result: TranscriptionResult) -> None:
        result.full_text = " ".join(seg.text for seg in result.segments).strip()

    def _detect_recording_type(self, result: TranscriptionResult) -> None:
        text = result.full_text.lower()
        type_map = [
            (LegalRecordingType.DEPOSITION, ["deponent", "deposition", "you are under oath", "court reporter"]),
            (LegalRecordingType.HEARING, ["your honor", "the court", "motion", "hearing"]),
            (LegalRecordingType.MEDIATION, ["mediator", "mediation", "settle", "settlement"]),
            (LegalRecordingType.ARBITRATION, ["arbitrator", "arbitration", "award"]),
            (LegalRecordingType.CLIENT_CALL, ["attorney-client", "privileged", "my client"]),
            (LegalRecordingType.TELEPHONE_CONFERENCE, ["conference call", "dial in", "line one"]),
        ]
        for rec_type, keywords in type_map:
            if any(kw in text for kw in keywords):
                result.recording_type = rec_type
                return
        result.recording_type = LegalRecordingType.UNKNOWN

    def _extract_legal_terms(self, result: TranscriptionResult) -> None:
        text_lower = result.full_text.lower()
        result.key_legal_terms = [t for t in LEGAL_TERMS if t in text_lower]

    def _extract_objections(self, result: TranscriptionResult) -> None:
        for seg in result.segments:
            for match in OBJECTION_PATTERNS.finditer(seg.text):
                result.objections.append({
                    "speaker": seg.speaker,
                    "timestamp": seg.timestamp_str,
                    "text": match.group(0).strip(),
                })

    def _extract_action_items(self, result: TranscriptionResult) -> None:
        for idx, seg in enumerate(result.segments):
            for match in ACTION_PATTERNS.finditer(seg.text):
                desc = match.group(0).strip()
                if len(desc) < 15:
                    continue
                deadline_match = DEADLINE_PATTERNS.search(desc)
                deadline = deadline_match.group(1).strip() if deadline_match else None
                result.action_items.append(
                    ActionItem(
                        description=desc,
                        assigned_to=seg.speaker,
                        deadline=deadline,
                        timestamp_context=seg.timestamp_str,
                        source_segment_idx=idx,
                    )
                )

    def _build_speaker_profiles(self, result: TranscriptionResult) -> None:
        profiles: Dict[str, SpeakerProfile] = {}
        for seg in result.segments:
            if seg.speaker not in profiles:
                profiles[seg.speaker] = SpeakerProfile(label=seg.speaker)
            p = profiles[seg.speaker]
            p.total_words += len(seg.text.split())
            p.total_speaking_time += seg.timestamp_end - seg.timestamp_start
            p.segment_count += 1

            # Attempt role identification
            text_lower = seg.text.lower()
            for role, kws in SPEAKER_ROLE_KEYWORDS.items():
                if any(kw in text_lower for kw in kws) and not p.role:
                    p.role = role

        result.speakers = list(profiles.values())

    def _compute_avg_confidence(self, result: TranscriptionResult) -> None:
        if result.segments:
            result.confidence_avg = sum(s.confidence for s in result.segments) / len(result.segments)
        else:
            result.confidence_avg = 0.0


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def transcribe_legal_audio(
    file_path: str | Path,
    api_key: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe a legal audio recording. Convenience function."""
    transcriber = LegalAudioTranscriber(api_key=api_key)
    return transcriber.transcribe_file(file_path)
