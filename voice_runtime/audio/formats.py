"""Audio format/MIME helpers.

Small, dependency-free helpers for reasoning about audio container/format
strings. Real format *conversion* (e.g. via ffmpeg) is out of scope for
Phase 1 and belongs in a lazily-loaded provider-specific path if ever
implemented — this module only classifies/validates format identifiers.
"""

from __future__ import annotations

#: MIME types the runtime recognizes as raw/uncompressed PCM containers.
PCM_MIME_TYPES: frozenset[str] = frozenset({"audio/wav", "audio/x-wav", "audio/pcm"})

#: MIME types the runtime recognizes as compressed audio containers.
COMPRESSED_MIME_TYPES: frozenset[str] = frozenset(
    {"audio/webm", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/aac"}
)

#: All MIME types this module can classify.
KNOWN_MIME_TYPES: frozenset[str] = PCM_MIME_TYPES | COMPRESSED_MIME_TYPES


def is_pcm(mime_type: str) -> bool:
    """Whether ``mime_type`` denotes a raw/uncompressed PCM container."""

    return mime_type.lower() in PCM_MIME_TYPES


def is_known_format(mime_type: str) -> bool:
    """Whether ``mime_type`` is one this runtime recognizes at all."""

    return mime_type.lower() in KNOWN_MIME_TYPES
