# SP-VOICE-002 — Architecture Baseline (Phase 0)

**Baseline: `origin/main` @ `e2ada66e22f7992fec83c884fd6f7aa9329ccb25`.**
**Branch: `feat/sp-voice-002-federated-speech-runtime`.**

This document defines the control-plane/data-plane split that all future
SP-VOICE-002 implementation phases must preserve. It does not authorize any
implementation yet — Phase 0 stops after this artifact and the component
matrix are produced.

## Governing rule (unchanged, non-negotiable)

> Voice may request and coordinate. Existing SintraPrime policy decides,
> records, approves, executes, or refuses.

Speech recognition and speech synthesis are **computation capabilities
only**. They do not gain independent filing, sending, publishing,
purchasing, payment, account-modification, or other consequential authority
— regardless of how realistic, fast, or convenient a given speech engine is.

## Control Plane — `voice_concierge/governed/` (SP-VOICE-001, authoritative, unchanged)

Owns and remains the *only* place that:
- classifies risk (`classifier.py`);
- decides policy (`policy.py`);
- manages session/cancellation state (`session.py`);
- enforces exact-target confirmation (`confirmation.py`);
- resolves and invokes **command capability** providers
  (`providers.py`/`mock_providers.py`/`orchestrator.py`);
- produces hash-chained events, receipts, and audit integration
  (`receipts.py`, `portal/models/voice_command.py`,
  `portal/services/voice_command_service.py`);
- exposes the RBAC-gated, tenant-scoped REST API
  (`portal/routers/voice_commands.py`).

SP-VOICE-002 introduces **no new execution path**. Nothing in the new speech
runtime may call a mock or real command provider directly, mint a
`VoiceCommand`, or otherwise bypass `voice_concierge/governed/orchestrator.py`.
Speech/audio output is always upstream (turning audio into a transcript that
becomes a command request) or downstream (turning an already-governed
response into audio) of this layer — never a parallel authority.

## Speech/Data Plane — `voice_runtime/` (SP-VOICE-002, new)

Owns speech **computation**, not decisions:
- ASR / speech-to-text;
- TTS / text-to-speech (streaming and long-form);
- multi-speaker synthesis;
- speaker diarization;
- audio normalization/preprocessing;
- speaker-profile handling (with consent governance, see Phase 4 of the
  implementation plan already authorized for later phases);
- provider capability declaration, discovery, routing, and lazy model
  lifecycle/preflight.

Proposed package shape (not yet created — Phase 1 work):

```
voice_runtime/
├── __init__.py       # import-free facade, mirrors voice_concierge/__init__.py
├── providers/         # one module per provider (browser, legacy adapter, VibeVoice-*, ...)
├── registry.py        # capability-based provider discovery & fallback routing
├── capabilities.py    # ASR / TTS / streaming-TTS / long-form / diarization / ... enum + protocol
├── models.py          # structured transcript / synthesis-request / provenance schemas
├── preflight.py        # dependency/hardware capability probing (no crash-on-missing-model)
├── audio.py            # audio preprocessing utilities (harvested from legacy voice/)
├── provenance.py       # media-provenance record construction, integrated with existing audit()
└── policy.py           # speaker-profile consent gating, disclosure-state enforcement
```

Hard requirement carried from this session's diagnosis of the original
PR #245 CI failure: **no module in `voice_runtime/__init__.py`'s import chain
may eagerly import a heavy dependency** (numpy, torch, transformers, or any
VibeVoice package). Application/test-suite startup must succeed with none of
these installed; heavyweight providers load lazily only when selected and
available (mirrors `voice_concierge/__init__.py`'s already-correct pattern,
and directly fixes the class of defect found in legacy `voice/__init__.py`
and still latent in `voice/wake_word.py` / `voice/voice_engine.py`, per the
component matrix).

## Existing building blocks available to `voice_runtime/` (from the component matrix)

| Reusable source | What to take | What NOT to take |
|---|---|---|
| `voice/voice_engine.py` | `AudioBuffer` noise-floor/silence-detection logic | Session/event-bus orchestration (superseded by `voice_concierge/governed/session.py`); module-level `logging.basicConfig()` |
| `voice/speech_processor.py` | Primary→fallback→offline provider-chain *pattern*; `LegalTermsDictionary`; `AudioPreprocessor`/`LanguageDetector` interfaces | Raw API-key dataclass fields; concrete mock-stub provider implementations |
| `voice/legal_nlp.py` | Entire module, as a domain/language-layer adapter feeding transcripts into (not replacing) risk classification | — |
| `voice/persona.py` | Entire module, as default synthetic-voice persona/profile metadata | — |
| `voice/wake_word.py` | Phonetic-matching local wake-word detector | Direct numpy dependency without lazy-loading it |
| `web/src/pages/VoiceConcierge.tsx` (PR #247) | Browser `SpeechRecognition`/`speechSynthesis` as the Tier-3 (zero-install) fallback provider | — |
| `voice/voice_api.py`, `voice/README.md` | Nothing — retire | Mock-authenticated router; misleading docs |

## Provider routing posture (for later Phase 7, informational only here)

Any future routing table must never silently downgrade governance
requirements, and must always keep the browser Web Speech API as a
zero-install fallback tier, consistent with what PR #247 already ships.

## What Phase 0 explicitly does NOT do

- No `voice_runtime/` code has been written.
- No VibeVoice (official or community-fork) package has been installed,
  downloaded, or referenced as a dependency.
- No model weights have been downloaded.
- No real ASR/TTS execution has occurred.
- No voice cloning or speaker enrollment has occurred.
- No deletion or refactor of `voice/` has occurred — legacy code is
  inventoried, not yet touched.
