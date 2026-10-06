"""Job specifications for the ``media_render`` package.

This module defines the data model for render jobs:

- :class:`LyricVideoJob` -- timed lyric overlays over a styled background,
  synced to an audio track (Lawful Roots Recordings music/lyric videos).
- :class:`ExplainerJob` -- kinetic-typography scenes generated from a script
  (visual educational content).
- :class:`RenderResult` -- the outcome returned by the render pipeline.

All validation lives here so it can run without Node.js, FFmpeg, or the
hyperframes CLI installed.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence


class JobValidationError(ValueError):
    """Raised when a media render job specification fails validation."""


def _require_existing_file(path: str | Path, *, label: str) -> Path:
    """Return the resolved path, raising :class:`JobValidationError` if missing."""
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise JobValidationError(f"{label} does not exist or is not a file: {candidate}")
    return candidate.resolve()


def _require_output_path(path: str | Path, *, label: str = "output_path") -> Path:
    candidate = Path(path).expanduser()
    if not str(candidate).strip():
        raise JobValidationError(f"{label} must be a non-empty path.")
    if candidate.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise JobValidationError(
            f"{label} must end in .mp4, .mov, or .webm (got {candidate.suffix!r})."
        )
    return candidate


# ---------------------------------------------------------------------------
# Small building blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LyricLine:
    """One timed lyric line. Times are seconds from the start of the audio."""

    text: str
    start: float
    end: float

    def validate(self) -> None:
        if not self.text or not self.text.strip():
            raise JobValidationError("LyricLine.text must be a non-empty string.")
        if self.start < 0:
            raise JobValidationError(f"LyricLine.start must be >= 0 (got {self.start}).")
        if self.end <= self.start:
            raise JobValidationError(
                f"LyricLine.end must be > start "
                f"(got start={self.start}, end={self.end})."
            )


@dataclass(frozen=True)
class Theme:
    """Visual theme applied to a composition (background, type, accents)."""

    name: str = "lawful-roots"
    background: str = "#0d0d12"
    background_gradient: str = "linear-gradient(135deg, #0d0d12 0%, #1a1428 60%, #0d0d12 100%)"
    foreground: str = "#f5f0e6"
    accent: str = "#d4a53f"
    muted: str = "#8a8a93"
    font_family: str = "'Inter', 'Helvetica Neue', Arial, sans-serif"

    def validate(self) -> None:
        if not self.name.strip():
            raise JobValidationError("Theme.name must be a non-empty string.")


PRESET_THEMES: dict[str, Theme] = {
    "lawful-roots": Theme(),
    "neon-night": Theme(
        name="neon-night",
        background="#050510",
        background_gradient="linear-gradient(135deg, #050510 0%, #101038 55%, #2a0a4a 100%)",
        foreground="#eef2ff",
        accent="#38e1ff",
        muted="#6b7280",
    ),
    "paper": Theme(
        name="paper",
        background="#faf7f0",
        background_gradient="linear-gradient(135deg, #faf7f0 0%, #efe8d8 100%)",
        foreground="#1c1a17",
        accent="#b3541e",
        muted="#8a8171",
    ),
}


@dataclass(frozen=True)
class NarrationOptions:
    """Narration/voice configuration for an explainer job.

    The media_render pipeline does not generate speech itself: narration audio
    is either supplied as a file (``engine="external-file"``) or produced by an
    external TTS step and attached afterwards (``engine="tts"`` records which
    voice profile was intended). ``engine="none"`` renders typography only.
    """

    engine: str = "none"
    narration_audio_path: Optional[str | Path] = None
    voice_id: Optional[str] = None
    rate: float = 1.0
    language: str = "en-US"

    def validate(self) -> None:
        if self.engine not in {"none", "external-file", "tts"}:
            raise JobValidationError(
                f"NarrationOptions.engine must be one of "
                f"'none', 'external-file', 'tts' (got {self.engine!r})."
            )
        if self.engine == "external-file":
            if not self.narration_audio_path:
                raise JobValidationError(
                    "NarrationOptions.narration_audio_path is required "
                    "when engine='external-file'."
                )
            _require_existing_file(self.narration_audio_path, label="narration_audio_path")
        if not 0.5 <= self.rate <= 2.0:
            raise JobValidationError(
                f"NarrationOptions.rate must be between 0.5 and 2.0 (got {self.rate})."
            )
        if not re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", self.language or ""):
            raise JobValidationError(
                f"NarrationOptions.language must look like 'en' or 'en-US' "
                f"(got {self.language!r})."
            )


@dataclass
class RenderResult:
    """Outcome of a render pipeline run."""

    job_id: str
    success: bool
    output_path: Optional[Path]
    elapsed_seconds: float
    command: Sequence[str]
    stdout_tail: str = ""
    stderr_tail: str = ""
    message: str = ""


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@dataclass
class LyricVideoJob:
    """Render a karaoke-style lyric video from an audio track + timed lyrics.

    Attributes:
        audio_path: Path to the audio file (mp3/wav/m4a, ...).
        lyrics: Timed lyric lines; must be non-overlapping and ordered in time.
        output_path: Destination video file (.mp4/.mov/.webm).
        theme: Visual theme for the composition.
        title / artist: Optional overlay metadata.
        width / height / fps: Output video dimensions and frame rate.
        audio_offset: Seconds to shift lyric timing relative to the audio
            (positive delays the lyrics).
    """

    audio_path: str | Path
    lyrics: Sequence[LyricLine]
    output_path: str | Path
    theme: Theme = field(default_factory=Theme)
    title: str = ""
    artist: str = ""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    audio_offset: float = 0.0
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def validate(self) -> None:
        _require_existing_file(self.audio_path, label="audio_path")
        _require_output_path(self.output_path)
        if not self.lyrics:
            raise JobValidationError("LyricVideoJob.lyrics must contain at least one line.")
        for line in self.lyrics:
            line.validate()
        ordered = sorted(self.lyrics, key=lambda line: line.start)
        for previous, current in zip(ordered, ordered[1:]):
            if current.start < previous.end:
                raise JobValidationError(
                    "LyricVideoJob.lyrics must not overlap: "
                    f"{previous.text!r} (ends {previous.end}) overlaps "
                    f"{current.text!r} (starts {current.start})."
                )
        self.theme.validate()
        for label, value in (("width", self.width), ("height", self.height)):
            if value <= 0:
                raise JobValidationError(f"LyricVideoJob.{label} must be > 0 (got {value}).")
        if self.fps <= 0:
            raise JobValidationError(f"LyricVideoJob.fps must be > 0 (got {self.fps}).")

    @property
    def duration_seconds(self) -> float:
        """End time of the last lyric line (informational)."""
        return max((line.end for line in self.lyrics), default=0.0)


@dataclass
class ExplainerJob:
    """Render a kinetic-typography explainer video from a script.

    Exactly one of ``script_text`` / ``script_path`` must be provided. The
    script is split into scenes (roughly one sentence per scene) and each
    scene is rendered as a timed typographic clip.
    """

    script_text: Optional[str] = None
    script_path: Optional[str | Path] = None
    output_path: str | Path = "explainer.mp4"
    narration: NarrationOptions = field(default_factory=NarrationOptions)
    theme: Theme = field(default_factory=Theme)
    title: str = ""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    max_scene_words: int = 18
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def validate(self) -> None:
        if bool(self.script_text) == bool(self.script_path):
            raise JobValidationError(
                "ExplainerJob requires exactly one of script_text / script_path."
            )
        if self.script_path is not None:
            _require_existing_file(self.script_path, label="script_path")
        if self.script_text is not None and not self.script_text.strip():
            raise JobValidationError("ExplainerJob.script_text must be non-empty.")
        _require_output_path(self.output_path)
        self.narration.validate()
        self.theme.validate()
        for label, value in (("width", self.width), ("height", self.height)):
            if value <= 0:
                raise JobValidationError(f"ExplainerJob.{label} must be > 0 (got {value}).")
        if self.fps <= 0:
            raise JobValidationError(f"ExplainerJob.fps must be > 0 (got {self.fps}).")
        if self.max_scene_words <= 0:
            raise JobValidationError(
                f"ExplainerJob.max_scene_words must be > 0 (got {self.max_scene_words})."
            )

    @property
    def script(self) -> str:
        """Resolved script text, from ``script_text`` or the ``script_path`` file."""
        if self.script_text is not None:
            return self.script_text
        assert self.script_path is not None  # validated above
        return Path(self.script_path).expanduser().read_text(encoding="utf-8")
