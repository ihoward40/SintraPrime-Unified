"""Browser/native speech provider descriptor.

Represents the existing PR #247 client-side speech capability
(``web/src/pages/VoiceConcierge.tsx``'s use of the browser
``SpeechRecognition``/``speechSynthesis`` Web Speech APIs) as an entry in
the server-side provider/capability model, **without** attempting to
execute browser APIs from Python. There is no way (and no need) for this
process to actually invoke a user's browser speech engine — this class
exists purely so the registry/router can:

- advertise browser/native ASR+TTS as a routing fallback tier;
- correctly report that its real availability is client-side dependent
  (i.e. this server-side descriptor can never promise ``AVAILABLE``, only
  that the *capability exists in the frontend* — actual availability is
  determined by the user's browser at runtime, which this process cannot
  observe).

Calling ``recognize()``/``synthesize()`` on this provider is a programming
error server-side (the browser performs these operations directly and
submits the resulting transcript, or plays the resulting speech, without
ever round-tripping through this Python provider) — both raise
``NotImplementedError`` with a clear explanation, inherited from
``BaseSpeechProvider``.

This module intentionally does not modify or interact with
``web/src/pages/VoiceConcierge.tsx`` or ``web/src/api/voice.ts`` in any way.
"""

from __future__ import annotations

from ..capabilities import SpeechCapability
from ..preflight import PreflightResult, PreflightState
from .base import BaseSpeechProvider


class BrowserSpeechProvider(BaseSpeechProvider):
    """Descriptor for the existing browser Web Speech API fallback tier.

    Declares ASR + TTS capabilities (matching what PR #247 already ships:
    ``SpeechRecognition``/``webkitSpeechRecognition`` for input,
    ``window.speechSynthesis`` for output) purely for routing/reporting
    purposes. This is always the last-resort fallback tier in routing
    priority — see ``voice_runtime/router.py``.
    """

    provider_id = "browser_native"
    provider_version = "1.0.0"
    _capabilities = frozenset({SpeechCapability.ASR, SpeechCapability.TTS})

    def preflight(self) -> PreflightResult:
        # Server-side, this provider can never be positively confirmed
        # "available" — actual availability depends on the requesting
        # user's browser/client, which this process cannot observe. It is
        # reported as AVAILABLE_DEGRADED to signal "usable as a fallback,
        # but not verifiable/guaranteed from the server."
        return PreflightResult(
            state=PreflightState.AVAILABLE_DEGRADED,
            detail="client-side dependent; actual availability determined by requesting browser",
            checked_fields={"execution_location": "client"},
        )

    def health(self) -> str:
        return "descriptor only — real execution happens client-side in the browser (PR #247)"
