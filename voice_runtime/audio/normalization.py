"""Audio normalization utilities.

Algorithms in this module are adapted from the legacy
``voice/voice_engine.py::AudioBuffer`` and ``voice/speech_processor.py``
modules (see ``artifacts/voice/SP_VOICE_002_COMPONENT_MATRIX.md`` for the
full Phase-0 disposition). They are reimplemented here in pure Python
(no ``numpy``) so that importing ``voice_runtime.audio`` never requires an
undeclared/optional heavy dependency — this directly fixes the class of
defect identified in the legacy modules, where ``numpy`` was imported at
module level without being declared in ``requirements.txt``.

If a caller wants numpy-accelerated versions of these same operations, that
belongs in a provider-specific, lazily-imported code path — never here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of a normalization/silence-detection pass."""

    rms: float
    peak: float
    is_speech_detected: bool
    clipped_sample_count: int


def _iter_pcm16_samples(pcm16_bytes: bytes) -> list[float]:
    """Decode little-endian 16-bit PCM bytes into floats in [-1.0, 1.0].

    Pure-Python replacement for the numpy-based buffer handling in the
    legacy ``AudioBuffer``. Not performance-optimized; adequate for tests
    and small/streamed chunks. A future real-time provider may choose a
    faster, lazily-imported implementation internally.
    """

    sample_count = len(pcm16_bytes) // 2
    samples = []
    for i in range(sample_count):
        lo = pcm16_bytes[2 * i]
        hi = pcm16_bytes[2 * i + 1]
        value = (hi << 8) | lo
        if value >= 32768:
            value -= 65536
        samples.append(value / 32768.0)
    return samples


def analyze_pcm16(pcm16_bytes: bytes, *, noise_floor: float = 0.02) -> NormalizationResult:
    """Compute RMS/peak/speech-detection for a chunk of 16-bit PCM audio.

    Mirrors ``voice.voice_engine.AudioBuffer.is_speech_detected`` /
    ``get_audio_level`` behavior (RMS energy vs. a noise-floor threshold),
    without any numpy dependency.
    """

    samples = _iter_pcm16_samples(pcm16_bytes)
    if not samples:
        return NormalizationResult(rms=0.0, peak=0.0, is_speech_detected=False, clipped_sample_count=0)

    sum_sq = sum(s * s for s in samples)
    rms = math.sqrt(sum_sq / len(samples))
    peak = max(abs(s) for s in samples)
    clipped = sum(1 for s in samples if abs(s) >= 1.0)

    return NormalizationResult(
        rms=rms,
        peak=peak,
        is_speech_detected=rms > noise_floor * 2,
        clipped_sample_count=clipped,
    )


def clip_normalize(pcm16_bytes: bytes) -> bytes:
    """Clip decoded samples to [-1.0, 1.0] and re-encode as 16-bit PCM.

    Pure-Python equivalent of ``AudioBuffer.add_chunk``'s
    ``np.clip(audio_chunk, -1.0, 1.0)`` normalization step.
    """

    samples = _iter_pcm16_samples(pcm16_bytes)
    out = bytearray()
    for s in samples:
        clipped = max(-1.0, min(1.0, s))
        value = round(clipped * 32767.0)
        if value < 0:
            value += 65536
        out.append(value & 0xFF)
        out.append((value >> 8) & 0xFF)
    return bytes(out)
