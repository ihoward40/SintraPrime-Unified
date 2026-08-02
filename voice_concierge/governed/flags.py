"""Feature flags for SP-VOICE-001 — disabled by default.

All capability flags default to ``false`` (directive §Feature Flags). The only
flag with a non-false default is the transcript retention mode, which defaults
to ``hash_only`` so raw transcripts are never persisted unless a deployment
explicitly opts in.

Env-parsing mirrors ``governed_inference/contracts.py::_env_bool`` so behaviour
is identical across the codebase. Flags gate *capability*, never authority: a
flag being true never grants an action; policy still decides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

FLAG_ENABLED = "SP_VOICE_001_ENABLED"
FLAG_REMOTE_ENABLED = "SP_VOICE_001_REMOTE_ENABLED"
FLAG_SCREEN_CONTEXT_ENABLED = "SP_VOICE_001_SCREEN_CONTEXT_ENABLED"
FLAG_WRITE_ACTIONS_ENABLED = "SP_VOICE_001_WRITE_ACTIONS_ENABLED"
FLAG_TRANSCRIPT_RETENTION = "SP_VOICE_001_TRANSCRIPT_RETENTION"


class TranscriptRetention(StrEnum):
    HASH_ONLY = "hash_only"
    FULL = "full"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_retention(name: str, default: TranscriptRetention) -> TranscriptRetention:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized == TranscriptRetention.FULL.value:
        return TranscriptRetention.FULL
    # Any unrecognized value fails safe to hash-only.
    return TranscriptRetention.HASH_ONLY


@dataclass(frozen=True)
class VoiceFeatureFlags:
    """Immutable snapshot of SP-VOICE-001 feature flags."""

    enabled: bool = False
    remote_enabled: bool = False
    screen_context_enabled: bool = False
    write_actions_enabled: bool = False
    transcript_retention: TranscriptRetention = TranscriptRetention.HASH_ONLY

    @classmethod
    def from_env(cls) -> VoiceFeatureFlags:
        """Load flags from the process environment, failing safe to defaults."""
        return cls(
            enabled=_env_bool(FLAG_ENABLED, False),
            remote_enabled=_env_bool(FLAG_REMOTE_ENABLED, False),
            screen_context_enabled=_env_bool(FLAG_SCREEN_CONTEXT_ENABLED, False),
            write_actions_enabled=_env_bool(FLAG_WRITE_ACTIONS_ENABLED, False),
            transcript_retention=_env_retention(
                FLAG_TRANSCRIPT_RETENTION, TranscriptRetention.HASH_ONLY
            ),
        )
