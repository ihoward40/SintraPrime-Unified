from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOICE_PAGE = ROOT / "web" / "src" / "pages" / "VoiceConcierge.tsx"
VOICE_API = ROOT / "web" / "src" / "api" / "voice.ts"


def _voice_page_source() -> str:
    return VOICE_PAGE.read_text(encoding="utf-8")


def test_browser_voice_io_is_transcript_only_and_uses_governed_submit() -> None:
    source = _voice_page_source()

    assert "navigator.mediaDevices.getUserMedia({ audio: true })" in source
    assert "SpeechRecognition" in source
    assert "SpeechSynthesisUtterance" in source
    assert "speechSynthesis.speak" in source
    assert "voiceApi.submit({ raw_transcript: rawTranscript, source: captureMode as VoiceSource })" in source
    assert "FormData" not in source
    assert "MediaRecorder" not in source
    assert "fetch(" not in source
    assert "mock_providers" not in source
    assert "executeProvider" not in source


def test_voice_ui_requires_explicit_submit_or_cancel_after_capture() -> None:
    source = _voice_page_source()

    assert "Nothing is classified or recorded until Submit is pressed" in source
    assert "cancelTranscript" in source
    assert "onClick={submit}" in source
    assert "setTranscript((current) => `${current} ${finalText}`.trim())" in source


def test_voice_source_type_matches_backend_enum() -> None:
    source = VOICE_API.read_text(encoding="utf-8")

    assert "export type VoiceSource = 'desktop_voice' | 'remote_voice' | 'transcript_import';" in source
    assert "mobile_voice" not in source
    assert "telephony" not in source
    assert "text_fallback" not in source
