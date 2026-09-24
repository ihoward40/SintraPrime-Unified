"""Tests for the pure-Python audio normalization utilities."""

from __future__ import annotations

from voice_runtime.audio.formats import is_known_format, is_pcm
from voice_runtime.audio.normalization import analyze_pcm16, clip_normalize


def _pcm16_tone(amplitude: float, samples: int) -> bytes:
    import struct

    value = int(amplitude * 32767)
    return struct.pack(f"<{samples}h", *([value] * samples))


def test_analyze_pcm16_silence():
    result = analyze_pcm16(bytes(200))
    assert result.rms == 0.0
    assert result.peak == 0.0
    assert not result.is_speech_detected
    assert result.clipped_sample_count == 0


def test_analyze_pcm16_detects_speech_above_noise_floor():
    tone = _pcm16_tone(0.5, 100)
    result = analyze_pcm16(tone, noise_floor=0.02)
    assert result.is_speech_detected
    assert result.rms > 0.02


def test_analyze_pcm16_empty_bytes():
    result = analyze_pcm16(b"")
    assert result.rms == 0.0
    assert not result.is_speech_detected


def test_clip_normalize_preserves_length():
    tone = _pcm16_tone(0.8, 50)
    normalized = clip_normalize(tone)
    assert len(normalized) == len(tone)


def test_is_pcm_recognizes_wav():
    assert is_pcm("audio/wav")
    assert not is_pcm("audio/webm")


def test_is_known_format():
    assert is_known_format("audio/webm")
    assert not is_known_format("audio/does-not-exist")
