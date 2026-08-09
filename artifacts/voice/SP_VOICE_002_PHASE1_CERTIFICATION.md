# SP-VOICE-002 — Phase 1 Certification: Federated Provider Architecture

**Branch:** `feat/sp-voice-002-federated-speech-runtime`
**Base:** `origin/main` @ `e2ada66e22f7992fec83c884fd6f7aa9329ccb25`
**Phase:** 1 of the SP-VOICE-002 implementation plan (provider-neutral speech
runtime skeleton only — no VibeVoice, no model downloads, no real
provider calls, no voice cloning, no speaker enrollment, no GPU setup).

## Governing rule (preserved, unchanged)

> Voice may request and coordinate. Existing SintraPrime policy decides,
> records, approves, executes, or refuses.

`voice_runtime` is a speech/data plane only. It recognizes speech,
synthesizes speech, normalizes audio, exposes provider capabilities,
selects available providers, and produces structured transcripts/artifacts
with provenance. It contains **zero** consequential-action authority: no
code path decides whether an action is permitted, executes a filing, sends
a message, moves money, modifies a record, bypasses confirmation, or
bypasses tenant isolation. `voice_concierge/governed` was not modified and
remains the sole authority for all of that.

## Architecture implemented

```
voice_runtime/
├── __init__.py         # import-free facade (mirrors voice_concierge/__init__.py's pattern)
├── capabilities.py      # SpeechCapability enum (8 capabilities)
├── errors.py            # typed error hierarchy
├── models.py             # provider-neutral request/response schemas
├── preflight.py           # PreflightState enum + PreflightResult
├── provenance.py          # SpeechProvenance record + content_hash()
├── registry.py            # ProviderRegistry + build_default_registry()
├── router.py              # deterministic route() with fallback + evidence
├── providers/
│   ├── __init__.py        # import-free
│   ├── base.py             # SpeechProvider Protocol + BaseSpeechProvider
│   ├── mock.py              # MockSpeechProvider (deterministic, no real inference)
│   ├── legacy.py             # LegacyAudioAdapterProvider (harvested AudioBuffer logic)
│   └── browser.py             # BrowserSpeechProvider (PR #247 descriptor, no execution)
├── audio/
│   ├── __init__.py
│   ├── normalization.py       # pure-Python RMS/silence/clip-normalize (no numpy)
│   └── formats.py               # MIME/format classification helpers
└── tests/                        # 54 tests (see below)
```

This matches the structure proposed in the Phase-1 authorization, with no
material deviation.

## Changed files

**New files (30):**
- `voice_runtime/__init__.py`
- `voice_runtime/capabilities.py`
- `voice_runtime/errors.py`
- `voice_runtime/models.py`
- `voice_runtime/preflight.py`
- `voice_runtime/provenance.py`
- `voice_runtime/registry.py`
- `voice_runtime/router.py`
- `voice_runtime/providers/__init__.py`
- `voice_runtime/providers/base.py`
- `voice_runtime/providers/mock.py`
- `voice_runtime/providers/legacy.py`
- `voice_runtime/providers/browser.py`
- `voice_runtime/audio/__init__.py`
- `voice_runtime/audio/normalization.py`
- `voice_runtime/audio/formats.py`
- `voice_runtime/tests/__init__.py`
- `voice_runtime/tests/test_minimal_dependency_import.py`
- `voice_runtime/tests/test_registry.py`
- `voice_runtime/tests/test_router.py`
- `voice_runtime/tests/test_mock_provider.py`
- `voice_runtime/tests/test_legacy_and_browser_providers.py`
- `voice_runtime/tests/test_models_and_provenance.py`
- `voice_runtime/tests/test_no_side_effects.py`
- `voice_runtime/tests/test_audio_normalization.py`
- `voice_runtime/tests/test_preflight.py`
- `artifacts/voice/SP_VOICE_001_PR245_TERMINAL_STATE.md` (Phase 0 carry-forward)
- `artifacts/voice/SP_VOICE_002_COMPONENT_MATRIX.md` (Phase 0, updated this phase)
- `artifacts/voice/SP_VOICE_002_ARCHITECTURE_BASELINE.md` (Phase 0 carry-forward)
- `artifacts/voice/SP_VOICE_002_PHASE1_CERTIFICATION.md` (this file)

**Modified files (2):**
- `pytest.ini` — added `voice_runtime/tests` to `testpaths`
- `pyproject.toml` — added `voice_runtime/tests` to `[tool.pytest.ini_options].testpaths`; added `voice_runtime` to `[tool.ruff.lint.isort].known-first-party`

**Not modified:** nothing under `voice/`, `voice_concierge/`, `portal/`, or
`web/` was touched in Phase 1. `voice_concierge/governed` remains
byte-for-byte as merged in PR #245/#240.

## Capability model

`voice_runtime.capabilities.SpeechCapability`: `ASR`, `TTS`,
`STREAMING_TTS`, `LONG_FORM_TTS`, `MULTI_SPEAKER_TTS`,
`SPEAKER_DIARIZATION`, `AUDIO_NORMALIZATION`, `SPEAKER_PROFILE`.

Providers declare a `frozenset[SpeechCapability]`; the registry/router
never reason about provider identity, only declared capabilities — adding a
future VibeVoice adapter requires no changes to `registry.py`/`router.py`.

## Provider registry

`ProviderRegistry` (in `voice_runtime/registry.py`):
- `register(provider, priority=100, enabled=True)` — raises
  `DuplicateProviderError` on ID collision.
- `unregister`, `set_enabled`, `get`, `is_enabled`, `provider_ids()`.
- `capability_map()` — provider ID → declared capabilities.
- `preflight_map()` — provider ID → current `PreflightResult` (disabled
  providers always report `DISABLED` regardless of their own `preflight()`).
- `providers_for_capability(capability)` — all registered providers
  declaring a capability, in deterministic `(priority, registration_order)`
  order.
- `build_default_registry()` — assembles the Phase-1 default set:
  `legacy_audio_adapter` (priority 50), `browser_native` (priority 90),
  `mock` (priority 100). No autonomous discovery; no plugin auto-install.

## Routing rules

`voice_runtime.router.route(registry, capability, preferred_provider_id=None)`:
1. If a `preferred_provider_id` is given and usable, select it regardless
   of configured priority (explicit caller preference wins).
2. Otherwise, walk `providers_for_capability()` in priority order and
   select the first provider whose current `preflight()` is `usable`.
3. If no provider declares the capability at all →
   `UnsupportedCapabilityError`.
4. If one or more providers declare it but none are usable →
   `ProviderUnavailableError` with per-provider rejection reasons.

Every call returns full `RoutingDecision` evidence: requested capability,
selected provider ID, all considered provider IDs, and a `rejected` tuple
of `(provider_id, reason)` pairs — never a silent selection.

Default routing tiers implemented, per the authorization's example (no
VibeVoice hard-coded):
1. legacy local audio-normalization adapter (priority 50)
2. browser/native fallback descriptor (priority 90)
3. mock (priority 100, dev/test default, always last)

A real local ASR/TTS provider (e.g. a future VibeVoice adapter) would slot
in at a lower priority number (e.g. 10) ahead of the legacy/browser tiers —
no routing-logic changes required, only a new registration call.

## Preflight

`PreflightState`: `AVAILABLE`, `AVAILABLE_DEGRADED`, `DISABLED`,
`DEPENDENCY_MISSING`, `MODEL_MISSING`, `HARDWARE_INSUFFICIENT`,
`CONFIGURATION_ERROR`, `UNSUPPORTED` — exactly the 8 states specified.
`PreflightResult` is a frozen dataclass with `.usable` (true only for
`AVAILABLE`/`AVAILABLE_DEGRADED`), `.detail`, and `.checked_fields`.
Convenience constructors (`available`, `dependency_missing`,
`model_missing`, `disabled`) keep provider code concise. All Phase-1
providers use static preflight (no real model integration exists yet);
none can crash application startup — preflight is a pure function call.

## Legacy adapter

`voice_runtime/providers/legacy.py::LegacyAudioAdapterProvider`:
- Declares **only** `AUDIO_NORMALIZATION` — cannot be routed to for ASR/TTS
  (its inherited `recognize()`/`synthesize()` raise `NotImplementedError`
  if ever called in error).
- Wraps `analyze_pcm16()`/`clip_normalize()` in
  `voice_runtime/audio/normalization.py`, which are **pure-Python
  reimplementations** (documented via provenance comments) of the RMS/
  noise-floor/silence-detection/clip-normalize logic from legacy
  `voice/voice_engine.py::AudioBuffer` — not an import of that module.
- Does **not** import the `voice` package at all (verified by AST
  inspection in tests, not just a substring check on source text).
- Exposes no legacy credentials, no legacy mock authentication
  (`voice.voice_api.verify_token` is never referenced by import), and no
  legacy direct-execution behavior.

## Legacy code reused

- `voice/voice_engine.py::AudioBuffer` RMS/noise-floor/silence-detection and
  clip/normalize math → reimplemented pure-Python in
  `voice_runtime/audio/normalization.py`.
- `voice/speech_processor.py`'s primary→fallback→offline provider-chain
  *shape* → generalized into `voice_runtime/router.py`'s
  preferred→priority-ordered→typed-error routing algorithm.

## Legacy code intentionally excluded

- `voice/voice_api.py` — reclassified `RETIRED_UNSAFE_LEGACY_API` (hardcoded
  mock bearer-token verification hazard, documented in the component
  matrix). Not deleted (not required for safety since it is already
  unreachable/unmounted); not imported or referenced by any `voice_runtime`
  import statement (enforced by test).
- `voice/speech_processor.py`'s raw API-key dataclass fields and concrete
  provider stubs — not reproduced; a real provider's credentials belong in
  the existing secrets-management pattern, not on a plain dataclass.
- `voice/voice_engine.py`'s session/event-bus orchestration — superseded by
  `voice_concierge/governed/session.py`, not duplicated.
- `voice/legal_nlp.py`, `voice/persona.py` — left untouched per Phase-0 KEEP
  disposition; not yet wired into `voice_runtime` (no ASR/TTS-adjacent use
  in Phase 1).
- `voice/README.md` — not used as a spec; this certification and the
  architecture baseline are the authoritative Phase-1 documentation.

## Dependency boundary (hard requirement, verified)

Importing `voice_runtime` and all of its always-available submodules
(`capabilities`, `errors`, `preflight`, `provenance`, `models`, `registry`,
`router`, `providers`, `providers.base`, `providers.mock`,
`providers.legacy`, `providers.browser`, `audio`, `audio.normalization`,
`audio.formats`) does **not** require `numpy`, `torch`, `transformers`,
`whisper`, `elevenlabs`, `boto3`, `pyttsx3`, or `vibevoice`. Verified by
`voice_runtime/tests/test_minimal_dependency_import.py`, which purges any
prior `voice_runtime.*` entries from `sys.modules`, freshly imports every
listed submodule, and asserts none of the heavy-dependency module
namespaces newly appear in `sys.modules` as a side effect.

## Test commands and exact results

```
python -m pytest voice_runtime/tests/ -q
→ 54 passed in 2.31s

ruff check voice_runtime/
→ All checks passed!

python -m pytest voice_runtime/tests/ voice_concierge/governed/tests/ \
    portal/tests/test_voice_commands.py portal/tests/test_voice_concierge_browser_io.py -q
→ 172 passed in 55.47s
    (54 voice_runtime + 88 voice_concierge/governed + 30 portal voice-related)

python -m pytest --collect-only -q
→ collects cleanly across the full default testpaths (tests/, portal/tests/,
  voice_concierge/governed/tests/, voice_runtime/tests/) with zero collection
  errors; only pre-existing, unrelated PytestCollectionWarning entries for
  agents/sigma and agents/zero dataclasses (present before this change).
```

No test in `voice_concierge/governed/tests/`, `portal/tests/test_voice_commands.py`,
or `portal/tests/test_voice_concierge_browser_io.py` was modified — all 118
of those pre-existing tests pass unchanged, confirming zero regression to
the merged SP-VOICE-001 foundation.

## Test coverage against the Phase-1 checklist

| Required test | Test file | Status |
|---|---|---|
| Core import without optional ML deps | `test_minimal_dependency_import.py` | ✅ |
| Provider registration | `test_registry.py::test_register_and_get` | ✅ |
| Duplicate provider rejection | `test_registry.py::test_duplicate_registration_rejected` | ✅ |
| Capability discovery | `test_registry.py::test_capability_map_reports_all_providers` | ✅ |
| Provider unavailable state | `test_router.py::test_route_all_providers_unavailable_raises_typed_error` | ✅ |
| Deterministic routing | `test_router.py::test_route_selects_only_candidate`, `test_providers_for_capability_deterministic_priority_order` | ✅ |
| Fallback routing | `test_router.py::test_route_falls_back_past_unavailable_provider`, `test_route_preferred_provider_unusable_falls_back` | ✅ |
| All providers unavailable | `test_router.py::test_route_all_providers_unavailable_raises_typed_error` | ✅ |
| Unsupported capability | `test_router.py::test_route_unsupported_capability_raises_typed_error` | ✅ |
| Disabled provider | `test_registry.py::test_disabled_provider_reported_in_preflight_map`, `test_router.py::test_route_disabled_provider_is_skipped` | ✅ |
| Preflight failure does not crash | `test_preflight.py` (all), `test_router.py` fallback tests | ✅ |
| Mock ASR output | `test_mock_provider.py::test_mock_recognize_produces_structured_transcript` | ✅ |
| Mock TTS output | `test_mock_provider.py::test_mock_synthesize_produces_speech_artifact` | ✅ |
| Structured transcript model | `test_models_and_provenance.py::test_structured_transcript_roundtrip_fields` | ✅ |
| Speech artifact model | `test_models_and_provenance.py::test_speech_artifact_provenance_serializes_to_dict` | ✅ |
| Provenance generation | `test_mock_provider.py`, `test_models_and_provenance.py` (multiple) | ✅ |
| Content hashing | `test_models_and_provenance.py::test_content_hash_deterministic_for_same_input`, `test_content_hash_differs_for_different_input` | ✅ |
| Legacy adapter cannot expose command authority | `test_legacy_and_browser_providers.py::test_legacy_adapter_declares_only_audio_normalization`, `test_legacy_adapter_recognize_and_synthesize_not_implemented` | ✅ |
| No import of `voice.voice_api` | `test_legacy_and_browser_providers.py::test_no_import_of_legacy_voice_api_module` (AST-based) | ✅ |
| No external network side effects | `test_no_side_effects.py::test_mock_asr_flow_makes_no_network_calls`, `test_default_registry_routing_makes_no_network_calls` | ✅ |
| No filesystem/model downloads | `test_no_side_effects.py::test_no_filesystem_model_downloads` | ✅ |
| No browser API regression | `test_no_side_effects.py::test_voice_concierge_frontend_browser_speech_api_present` | ✅ |
| SP-VOICE-001 governed tests remain green | Full regression run above (88 tests unchanged) | ✅ |

## Known limitations

- `voice/legal_nlp.py` and `voice/persona.py` are not yet wired into
  `voice_runtime` — they remain standalone, per their Phase-0 KEEP
  disposition, until a language/persona adapter is designed in a later
  phase.
- The undeclared-`numpy` hazard in `voice/voice_engine.py` and
  `voice/wake_word.py` still exists in the legacy package itself (Phase 1
  did not modify `voice/`, per scope). It is fully avoided within
  `voice_runtime`, but anyone still importing `voice.voice_engine` or
  `voice.wake_word` directly (outside this runtime) remains exposed to it.
- `BrowserSpeechProvider.recognize()`/`.synthesize()` deliberately raise
  `NotImplementedError` — there is no code path today that would route a
  server-side capability request to the browser tier and expect a real
  result; the descriptor exists for capability-reporting/routing-evidence
  purposes only. Real browser-mediated flows continue to go through the
  existing `portal/routers/voice_commands.py` API and
  `web/src/pages/VoiceConcierge.tsx`, unchanged.
- No real ASR/TTS provider exists yet (by design — Phase 1 scope excludes
  VibeVoice/any real model integration).
- `SPEAKER_PROFILE` capability is defined in the enum but no provider
  declares or implements it yet; speaker-profile consent governance is
  explicitly deferred to a later phase per the original increment plan.

## Phase 2 recommendation

Proceed to **SP-VOICE-002 Phase 2: official-provider certification**,
evaluating VibeVoice-ASR and VibeVoice-Realtime-0.5B **one at a time**
against this now-stable interface:
1. Add a new `voice_runtime/providers/vibevoice_asr.py` (or similar)
   implementing `SpeechProvider` with lazy-imported dependencies gated
   behind `preflight()` — never imported at module load time.
2. Register it at a low priority number (e.g. 10) ahead of the legacy/
   browser tiers in a non-default registry assembly (not
   `build_default_registry()`, to keep the zero-dependency default intact).
3. Add explicit dependency/model-file/hardware preflight checks returning
   `DEPENDENCY_MISSING`/`MODEL_MISSING`/`HARDWARE_INSUFFICIENT` as
   appropriate — no installation, no download, no execution authorized yet
   without a separate, explicit go-ahead per provider.
4. Extend the mock-first test pattern established here: typed-error and
   fallback tests must pass with the new provider intentionally left
   unavailable (dependency/model absent) before any real integration is
   attempted.

No merge, deploy, push, or external side effect occurred in Phase 1. This
branch has not been pushed to any remote.
