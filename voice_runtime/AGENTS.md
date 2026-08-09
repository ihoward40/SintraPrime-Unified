# voice_runtime — SP-VOICE-002 Federated Speech Runtime (Phase 1)

## Purpose

Speech/data-plane package: automatic speech recognition (ASR), speech
synthesis (TTS), audio normalization, and provider capability
discovery/routing for SintraPrime voice features. Converts audio to
structured transcripts and text to speech artifacts — nothing more.

Governing rule (shared with `voice_concierge/governed`, non-negotiable):

> Voice may request and coordinate. Existing SintraPrime policy decides,
> records, approves, executes, or refuses.

This package is a **speech/data plane only**. It has no authority to decide
whether a consequential action is permitted, execute filings, send
messages, make payments, modify records, bypass confirmation, or bypass
tenant isolation — all of that remains exclusively in
`voice_concierge/governed`. See
`artifacts/voice/SP_VOICE_002_ARCHITECTURE_BASELINE.md` for the full
control-plane/data-plane split, and
`artifacts/voice/SP_VOICE_002_PHASE1_CERTIFICATION.md` for what Phase 1
implemented.

## Ownership

- `capabilities.py` — `SpeechCapability` enum (ASR, TTS, STREAMING_TTS,
  LONG_FORM_TTS, MULTI_SPEAKER_TTS, SPEAKER_DIARIZATION,
  AUDIO_NORMALIZATION, SPEAKER_PROFILE)
- `errors.py` — typed error hierarchy (`VoiceRuntimeError` and subclasses)
- `models.py` — provider-neutral request/response schemas
  (`SpeechRecognitionRequest`, `StructuredTranscript`,
  `SpeechSynthesisRequest`, `SpeechArtifact`, `AudioSource`, `TenantContext`)
- `preflight.py` — `PreflightState`/`PreflightResult` (availability without
  crashing on missing dependency/model/hardware)
- `provenance.py` — `SpeechProvenance` record + `content_hash()`; designed
  to feed the existing audit/receipt subsystem, not to compete with it
- `registry.py` — `ProviderRegistry` (registration, duplicate rejection,
  capability/preflight maps, priority-ordered capability lookup) +
  `build_default_registry()`
- `router.py` — deterministic `route()` with full routing evidence
  (considered/rejected providers and reasons)
- `providers/base.py` — `SpeechProvider` Protocol + `BaseSpeechProvider`
- `providers/mock.py` — deterministic mock ASR/TTS provider (no real
  inference)
- `providers/legacy.py` — bounded adapter harvesting only the legacy
  `voice/voice_engine.py::AudioBuffer` normalization math (pure Python, no
  `voice` package import); declares `AUDIO_NORMALIZATION` only
- `providers/browser.py` — server-side descriptor for the PR #247 browser
  Web Speech API fallback tier; never executes browser APIs from Python
- `audio/normalization.py`, `audio/formats.py` — pure-Python audio
  preprocessing utilities (no `numpy`)
- `tests/` — 54 tests covering import-dependency boundary, registry,
  routing/fallback, mock provider, models/provenance, legacy/browser
  provider boundaries, and no-side-effect guarantees

## Local Contracts

- `voice_runtime/__init__.py` and every always-available submodule
  (everything except inside a specific provider's real-model activation
  path) must remain importable with **no** optional heavy dependency
  installed: no `numpy`, `torch`, `transformers`, `whisper`, `elevenlabs`,
  `boto3`, `pyttsx3`, or `vibevoice`. Enforced by
  `tests/test_minimal_dependency_import.py`.
- Providers declare capabilities explicitly (`SpeechCapability` frozenset);
  the registry/router never branch on provider identity or name.
- `preflight()` must never raise or crash application startup — it always
  returns a `PreflightResult`.
- Unsupported capabilities and unavailable providers fail with typed errors
  (`UnsupportedCapabilityError`, `ProviderUnavailableError`), never a silent
  fallback to something unexpected.
- This package must never import `voice.voice_api` (legacy, unauthenticated
  mock-JWT router — classified `RETIRED_UNSAFE_LEGACY_API`) or reproduce
  its mock bearer-token verification. Enforced by AST-based import
  inspection in `tests/test_legacy_and_browser_providers.py`.
- No provider in this package may perform a real network call, write a
  file, or download a model as a side effect of registration or routing
  (mock/legacy/browser providers are all local/deterministic). Any future
  real provider (e.g. VibeVoice) must gate all such behavior behind an
  explicit, separately-authorized activation path — never merely by being
  registered.
- This package routes NO consequential actions and never bypasses
  `voice_concierge/governed`.

## Work Guidance

- Add new capabilities to `capabilities.py` conservatively; a capability
  should represent a genuine, distinct computation class, not a
  provider-specific feature flag.
- New providers should subclass `BaseSpeechProvider` (or independently
  satisfy the `SpeechProvider` Protocol) and declare only the capabilities
  they actually implement; unimplemented `recognize()`/`synthesize()` must
  raise `NotImplementedError`, never fabricate output.
- Real/heavy providers (e.g. a future VibeVoice adapter) must import their
  heavy dependencies lazily, inside methods gated by `preflight()` —
  never at module import time. See `providers/legacy.py`'s docstring for
  the pattern of harvesting an *algorithm* rather than importing an unsafe
  module wholesale when adapting legacy code.
- Do not add real provider credentials as plain dataclass fields; follow
  the existing repository secrets-management pattern instead.

## Verification

- `python -m pytest voice_runtime/tests/ -q`
- `ruff check voice_runtime/`
- Regression: `python -m pytest voice_concierge/governed/tests/ portal/tests/test_voice_commands.py portal/tests/test_voice_concierge_browser_io.py -q`

## Child DOX Index

*(None — leaf modules.)*
