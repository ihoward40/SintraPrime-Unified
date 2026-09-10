"""
SintraPrime Federated Speech Runtime (SP-VOICE-002)
====================================================

Speech/data-plane package: automatic speech recognition (ASR), speech
synthesis (TTS), audio normalization, speaker-profile handling, and
provider capability discovery/routing.

Governing rule (unchanged from SP-VOICE-001, non-negotiable):

    Voice may request and coordinate. Existing SintraPrime policy decides,
    records, approves, executes, or refuses.

This package is a **speech/data plane only**. It recognizes speech,
synthesizes speech, normalizes audio, exposes provider capabilities, selects
available providers, and produces structured transcripts / speech artifacts
with provenance. It never decides whether a consequential action is
permitted, never executes filings/messages/payments/record changes, never
bypasses confirmation, and never bypasses tenant isolation. All command
authority remains exclusively in ``voice_concierge.governed``.

This package is intentionally kept free of eager imports so that importing
``voice_runtime`` (or any of its always-available submodules: capabilities,
models, registry, router, preflight, provenance, errors) never requires
optional heavy dependencies such as numpy, torch, transformers, CUDA
bindings, ffmpeg Python bindings, VibeVoice, Whisper, or any external
provider SDK. Optional/heavy dependencies are only imported inside a
specific provider's activation path, and only when that provider is
actually selected for use. See ``voice_runtime/providers/`` and
``voice_runtime/preflight.py``.
"""

from __future__ import annotations

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
