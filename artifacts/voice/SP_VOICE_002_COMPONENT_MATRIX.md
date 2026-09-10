# SP-VOICE-002 — Component Matrix (Phase 0: Repository Archaeology)

**Baseline: `origin/main` @ `e2ada66e22f7992fec83c884fd6f7aa9329ccb25`, worktree
branch `feat/sp-voice-002-federated-speech-runtime`.**

This inventory was produced entirely from the finalized, certified post-#245
`main` baseline (see `SP_VOICE_001_PR245_TERMINAL_STATE.md`). No pre-rebase or
mixed state was inspected for classification purposes.

## Historical commits inspected

| Commit | Date | Summary |
|---|---|---|
| `08e7c7f0` | 2026-04-25 | batch 18 — sintraprime speech, tools/security, connectors/platforms, watch |
| `6746f677` | 2026-04-25 | batch 19 — sintraprime tools/security, connectors/platforms, watch, speech remaining |
| `2fa9c1f7` | 2026-04-25 | "Phase 4 Complete: Voice, SaaS, Docket, DocuSign, Agencies, ML (29K lines)" |
| `d57927c7` | 2026-04-25 | "Squad Omega — all 65 test failures resolved (case_law API, docket urllib3, federal/voice/esign logic, banking/saas imports)" |
| `f9e5eeb0` | 2026-08-02 | SP-VOICE-001: Add governed voice operations foundation (#240, squash merge) |
| `e32c07c6` | 2026-08-02 | SP-VOICE-001 Increment Two: governed voice orchestrator, mock providers, ledger API, and concierge panel (#245, squash merge) |
| `6e3d2740` | 2026-08-02 | Browser Voice I/O for Voice Concierge (#247) |

The April 2026 commits (`08e7c7f0`/`6746f677`/`2fa9c1f7`/`d57927c7`) are the
origin of the legacy `voice/` package (Senior Partner persona, legal NLP,
speech processor, wake word, voice engine, voice API) — roughly 3,219 lines
across 8 non-test modules today (line count taken from the current tree, not
the original commit, since the package has been touched since). PR #240/#245
introduced the modern governed control plane at `voice_concierge/governed/`
(~1,174 lines across 10 modules). PR #247 added browser mic/speech-synthesis
I/O directly into the `voice_concierge/governed`-backed frontend
(`web/src/pages/VoiceConcierge.tsx`, `web/src/api/voice.ts`) and a
corresponding portal test (`portal/tests/test_voice_concierge_browser_io.py`).

## Component classifications

### Legacy `voice/` package (April 2026 origin)

| Component | Origin | Status | Responsibility | Dependencies | Governance relevance | Overlap | Known debt | Disposition | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| `voice/__init__.py` | 08e7c7f0 era | present, lazy `__getattr__` exports | Package facade | none eager | none — pure exports | superseded facade | Previously caused CI failures for PR #245 because eager submodule imports pulled `numpy` transitively into unrelated test collection paths (root-caused and fixed by relocating governed code out of `voice/` in PR #245's `f8661f12` commit). The lazy `__getattr__` pattern here *is* the correct fix shape and should be the template for `voice_runtime/`. | **KEEP (as template)** | Already lazy; safe to import `voice` itself. Any `voice.<X>` attribute access still requires `numpy` (undeclared dependency — see below). |
| `voice/voice_engine.py` (`VoiceEngine`, `SessionManager`, `AudioBuffer`) | 08e7c7f0/2fa9c1f7 | present, all mock/no-op internals (`# Mock implementation` comments throughout: `_transcribe_audio`, `_synthesize_text`) | Async session/audio-buffer orchestration, event bus | `numpy` (module-level import, **undeclared** in `requirements.txt`) | No governance hooks at all — no RBAC, no tenant scoping, no policy/confirmation gate; a raw `speak()`/`process_audio()` call would execute unconditionally if ever wired to a real backend | Functionally duplicates the *session/event* concerns already handled far more rigorously by `voice_concierge/governed/session.py` and `orchestrator.py` | `numpy` import at module top-level; `logging.basicConfig()` called at import time (global side effect); no tenant/session isolation; mock TTS/STT baked in as literal stubs, not swappable providers | **ADAPT** — the `AudioBuffer`/noise-floor/silence-detection logic is reusable audio-preprocessing utility; the session/event-bus/orchestration layer should be retired in favor of `voice_concierge/governed/session.py`, which already has confirmation/cancellation/child-task semantics this module lacks entirely | Provides real audio-buffering logic worth harvesting, but it must never gain command/session authority — that already exists, governed, elsewhere |
| `voice/speech_processor.py` (`SpeechProcessor`, `AudioPreprocessor`, `LanguageDetector`, `LegalTermsDictionary`) | 08e7c7f0/2fa9c1f7 | present, all provider calls are literal mock stubs returning canned text/zeroed audio arrays | STT/TTS provider fan-out with fallback chain (Whisper→Google; ElevenLabs→Polly→pyttsx3) | `numpy` (in mock synth helpers), designed for `openai`, `google-cloud-speech`, `elevenlabs`, `boto3`, `pyttsx3` (none installed/declared) | No provider ever contacts anything real today (good), but the module's design assumes **real, unguarded** provider credentials (`openai_api_key`, `elevenlabs_api_key`, `aws_access_key`/`aws_secret_key` fields directly on a dataclass) with **no consent, provenance, or governance layer** if ever activated | Directly overlaps the intended `voice_runtime/providers/` capability classes (ASR/TTS/streaming/long-form) that SP-VOICE-002 must build | Raw credential fields on a plain dataclass (no secrets-manager integration); provider fallback logic has no capability-declaration/preflight model; `LegalTermsDictionary`/`AudioPreprocessor`/`LanguageDetector` are reusable, provider-agnostic utilities | **ADAPT** — the fallback-chain *pattern* (primary→fallback→offline) and the legal-pronunciation dictionary are worth carrying into `voice_runtime/providers/registry.py` and a domain-specific normalization adapter; the concrete provider stubs and raw-credential dataclass should be **RETIRE**d in favor of governed provider classes with capability declarations and provenance metadata | Salvage the fallback-chain shape and legal-terms utility; do not carry over the ungoverned credential model |
| `voice/legal_nlp.py` (`Intent` enum, `LegalNLPProcessor`) | 08e7c7f0/2fa9c1f7 | present, regex/keyword-based intent classification, 25+ legal intents | Domain-specific intent classification and entity extraction for legal queries | none heavy (`re`, stdlib) | Not governance — purely a language-understanding layer; does not decide or execute anything | Complements rather than duplicates `voice_concierge/governed/classifier.py` (which classifies **risk**, not legal domain/intent) — these are different axes of classification and could compose | none significant; well-contained, pure-Python, already lightweight | **KEEP** (as a language/domain layer, not a control-plane component) | Directly reusable as a "legal domain intent" adapter feeding into (but never replacing) the governed risk classifier; matches the plan's Phase 2 guidance to move legal NLP to "the language layer" |
| `voice/persona.py` (`SeniorPartnerPersona`, `PersonaConfig`, `LegalDomain`, `ToneLevel`) | 08e7c7f0/2fa9c1f7 | present, template-based response generation with escalation-detection heuristics | Persona/tone selection and human-readable response templating | none heavy | No governance impact — persona selection is presentation, not authority | No overlap with existing control plane; complements future TTS voice-profile selection | Escalation heuristics are advisory text only, not tied to any real escalation/paging system | **KEEP** (as a persona/profile) | Matches the plan's explicit guidance ("Senior Partner persona KEEP as persona/profile"); can become the default synthetic-voice persona metadata for `voice_runtime` once speaker-profile governance (Phase 4 of SP-VOICE-002) exists |
| `voice/response_formatter.py` | 08e7c7f0/2fa9c1f7 | present, not yet read in depth this pass | Converts text responses to voice-friendly formatting/SSML | none heavy expected | none | Complements TTS output stage | not yet assessed for defects | **KEEP** (pending closer read in Phase 1) | Formatting concern, independent of control plane |
| `voice/wake_word.py` (`WakeWordDetector`, `PhoneticMatcher`) | 08e7c7f0/2fa9c1f7 | present, local-only, no network calls, phonetic distance matching | Local wake-word detection | `numpy` (module-level import, **undeclared** dependency) | None — purely a local audio-trigger utility, no execution authority | No current equivalent elsewhere in the repo | Same undeclared-`numpy`-dependency hazard as `voice_engine.py` | **KEEP** (adapt to lazy-load numpy) | Explicitly local/offline by design (a genuine strength — "no network calls" is already the right governance posture for this piece); just needs the dependency hazard fixed |
| `voice/voice_api.py` | 08e7c7f0/2fa9c1f7 | present, FastAPI router with **mock JWT verification** (`# Mock JWT verification - in production use real verification`) hardcoded in `verify_token` | Legacy standalone REST/WebSocket voice API | `fastapi`, `jwt` (PyJWT) | **Significant governance hazard if ever mounted**: `verify_token` unconditionally returns a fake payload for any bearer token, i.e. **authentication is fully bypassed** in this module. This is exactly the kind of consequential-action risk the plan's Phase 3+ governance work must prevent from ever reaching a real deployment. | Directly duplicated/superseded by `portal/routers/voice_commands.py`, which uses the real portal auth/RBAC/tenant-scoping stack (`CurrentUser`, permission-gated dependencies) | Not mounted into the FastAPI app today (verified: no reference to `voice.voice_api` found in `portal/` router registration) — currently dead code, but its presence is a landmine for anyone who imports/mounts it without noticing the mock-auth comment | **RETIRE** | This router must not be adapted or reused; it should not exist alongside the governed `portal/routers/voice_commands.py` API surface. Any future real-time streaming API belongs behind the same RBAC/tenant middleware as the rest of `portal/routers/`, never a standalone unauthenticated router. |
| `voice/tests/test_voice.py` | 08e7c7f0/2fa9c1f7/d57927c7 | present, ~24KB, imports `numpy` directly and depends on every legacy module above | Legacy package's own test suite (persona, NLP, formatting, wake word, speech processor, integration/edge cases per README: "50+ unit tests") | `numpy` (undeclared) | none | Tests exercise retired/adapted code; will need reshaping alongside each module's disposition | Test suite currently only "works" because `numpy` happens to be present transitively in this environment (confirmed: `numpy 2.3.5` importable, but **not listed** in `requirements.txt`) — this is the same unmanaged-dependency class of defect diagnosed for PR #245's CI failures, just not yet triggered because nothing eagerly imports `voice.*` from a path CI collects by default | **ADAPT** — split into per-disposition test files as modules are KEPT/ADAPTED/RETIRED; declare `numpy` explicitly wherever it remains needed, or remove the dependency by rewriting audio-buffer/wake-word math without it | Confirms the plan's stated lesson: undeclared heavy dependencies in `voice/` are a repeat hazard, not a one-off; SP-VOICE-002 must not repeat this pattern in `voice_runtime/` |
| `voice/README.md` | 08e7c7f0 era | present, extensive (functional spec + API examples for a **fully real** ElevenLabs/Whisper/AWS Polly/Google STT system that was never actually implemented — every provider call in the code is a mock stub) | Documentation | n/a | Documentation risk: describes production behavior (real API keys, real transcription latency figures, a `/voice/transcribe` REST surface) that does not exist in the code — misleading if read at face value | n/a | Aspirational/stale relative to actual (mock-only) implementation | **RETIRE / rewrite** | Must not be used as a spec for SP-VOICE-002; any new README must accurately reflect governed, mock-first, capability-declared reality per this repo's conventions |

### Modern governed control plane (PR #240/#245/#247 origin — `voice_concierge/`)

| Component | Status | Disposition | Rationale |
|---|---|---|---|
| `voice_concierge/__init__.py` | present, deliberately import-free (docstring explicitly states the lazy-import design goal) | **KEEP — authoritative, untouched** | This is the fix for the exact "eager heavy import" class of defect found in legacy `voice/__init__.py`; it is the correct pattern to replicate for `voice_runtime/__init__.py`. |
| `voice_concierge/governed/command_envelope.py` | present, immutable envelope + ID generation | **KEEP — authoritative, untouched** | Core control-plane data type. |
| `voice_concierge/governed/classifier.py` | present, deterministic risk classifier | **KEEP — authoritative, untouched** | Risk classification is the governance backbone; SP-VOICE-002 must never bypass or duplicate it. |
| `voice_concierge/governed/policy.py` | present, pure risk-class → decision matrix | **KEEP — authoritative, untouched** | |
| `voice_concierge/governed/confirmation.py` | present, exact-target confirmation (defect fixed this session, commit `b9941096`/merged as part of `#240`) | **KEEP — authoritative, untouched** | Recently hardened; do not touch except for independently demonstrated defects. |
| `voice_concierge/governed/session.py` | present, session state machine, cancellation/interruption | **KEEP — authoritative, untouched** | |
| `voice_concierge/governed/receipts.py` | present, correlated machine-readable receipts, hash-only transcript retention | **KEEP — authoritative, untouched** | Template for SP-VOICE-002's Phase 5 media-provenance record — same hash-chained/audit-integrated pattern should be reused, not reinvented. |
| `voice_concierge/governed/flags.py` | present, disabled-by-default feature flags | **KEEP — authoritative, untouched** | |
| `voice_concierge/governed/providers.py` | present, `VoiceActionProvider` protocol + capability resolution (no I/O) | **KEEP — authoritative, untouched** | Distinct from and a good structural model for the *new* `voice_runtime` provider-capability protocol (ASR/TTS/etc.), but must remain a separate registry — this one resolves **command capabilities** (email/calendar/messaging/...), not **speech capabilities** (ASR/TTS/diarization/...). |
| `voice_concierge/governed/mock_providers.py` | present, mock-only command-capability providers | **KEEP — authoritative, untouched** | |
| `voice_concierge/governed/orchestrator.py` | present, ties classification+policy+session+confirmation+providers+receipts together | **KEEP — authoritative, untouched** | The single place command execution happens; SP-VOICE-002's speech runtime must never gain a parallel execution path that bypasses this. |
| `voice_concierge/governed/AGENTS.md` | present, DOX child doc | **KEEP, extend narrowly if SP-VOICE-002 adds a sibling `voice_runtime/AGENTS.md`** | Already declares the governing rule this whole effort must preserve. |
| `portal/models/voice_command.py` | present, tenant-scoped hash-chained ledger models | **KEEP — authoritative, untouched** | |
| `portal/services/voice_command_service.py` | present, RBAC-gated service layer, `MockOnlyExecutionError` guard | **KEEP — authoritative, untouched** | |
| `portal/routers/voice_commands.py` | present, RBAC-gated REST API (submit/get/list/confirm/cancel), real JWT-backed `CurrentUser` | **KEEP — authoritative, untouched** | The correct authenticated API pattern — the opposite of legacy `voice/voice_api.py`'s mock auth. |
| `web/src/api/voice.ts` | present, typed API client, docstring explicitly disclaims real-world side effects | **KEEP — authoritative, untouched** | |
| `web/src/pages/VoiceConcierge.tsx` (PR #247) | present, browser `SpeechRecognition`/`speechSynthesis` (Web Speech API) capture + playback, feeding the governed command API only | **KEEP — fallback tier** | This *is* the "browser speech input/output fallback" the plan calls for. It already exists and already only feeds the governed ledger — SP-VOICE-002 should treat it as Tier-3 fallback in the provider routing table (Phase 7), not replace it. |
| `portal/tests/test_voice_commands.py`, `portal/tests/test_voice_concierge_browser_io.py`, `voice_concierge/governed/tests/*.py` | present, 153+ tests | **KEEP — authoritative, untouched** | |

### Unrelated speech-adjacent code (false positive, out of scope)

| Component | Status | Disposition | Rationale |
|---|---|---|---|
| `apps/SintraPrime/src/speech/*.ts` (`speak.ts`, `speechTiers.ts`, `decideSpeech.ts`, `emitSpeechBundle.ts`, `renderConfidenceSpeech.ts`, etc.) | present, TypeScript | **OUT OF SCOPE — not voice/audio at all** | This is a different, unrelated "speech" concept: rendering natural-language *status/confidence commentary* for a separate orchestration/gradient system (based on file names: `getRequalificationStatus`, `s3Deltas`, `s5Status`, `s6Feedback`, `writeSpeechArtifact`). It has nothing to do with audio, ASR, or TTS. Excluded from the SP-VOICE-002 inventory; flagged here only so a future reader doesn't conflate the two "speech" namespaces. |

## Summary disposition counts

- **KEEP (as-is / authoritative, no changes):** 20 components (all of `voice_concierge/governed/*`, `portal/*voice*`, `web/*voice*`, `voice/legal_nlp.py`, `voice/persona.py`, `voice/response_formatter.py`, `voice/wake_word.py` pending numpy fix)
- **ADAPT (harvest logic, rebuild interface):** 3 components (`voice/voice_engine.py`'s `AudioBuffer`, `voice/speech_processor.py`'s fallback pattern + legal-terms/preprocessing utilities, `voice/tests/test_voice.py` restructuring)
- **RETIRE:** 2 components (`voice/voice_api.py` — mock-auth hazard; `voice/README.md` — misleading aspirational spec)
- **OUT OF SCOPE:** 1 false-positive namespace collision (`apps/SintraPrime/src/speech/`)

## Phase 1 disposition updates (executed)

Phase 1 ("SP-VOICE-002 — Federated Provider Architecture") has been
implemented on branch `feat/sp-voice-002-federated-speech-runtime`. The
following dispositions from the table above have now been **acted on**,
not merely proposed:

| Component | Phase-0 disposition | Phase-1 outcome |
|---|---|---|
| `voice/voice_engine.py`'s `AudioBuffer` (RMS/noise-floor/silence-detection, clip-normalize) | ADAPT | **Harvested** as a pure-Python (no `numpy`) reimplementation in `voice_runtime/audio/normalization.py` (`analyze_pcm16`, `clip_normalize`), exposed via `voice_runtime/providers/legacy.py::LegacyAudioAdapterProvider`. Declares only `AUDIO_NORMALIZATION`; cannot be routed to for ASR/TTS. See provenance comments in both files documenting the exact extraction source and rationale. |
| `voice/speech_processor.py`'s primary→fallback→offline provider-chain *shape* | ADAPT | **Pattern reused** in `voice_runtime/router.py::route()` (explicit-preference → priority-ordered fallback → typed unavailable error), generalized to any capability rather than hard-coded to STT/TTS provider names. Concrete mock stubs and raw-credential dataclass fields were **not** carried over, per the Phase-0 finding. |
| `voice/legal_nlp.py`, `voice/persona.py` | KEEP (as language/persona layer) | **Untouched.** Not imported by `voice_runtime` in Phase 1 (no ASR/TTS-adjacent use yet); remains available for a future language/persona adapter layer, per the architecture baseline. |
| `voice/voice_api.py` | RETIRE | **Formally reclassified `RETIRED_UNSAFE_LEGACY_API`** (not deleted — deletion was not required for safety since it is already unreachable/unmounted, and the plan directs against deletion unless clearly isolated and necessary). A regression test (`voice_runtime/tests/test_legacy_and_browser_providers.py::test_no_import_of_legacy_voice_api_module`) enforces, via AST inspection of the legacy-adapter module's actual `import`/`from...import` statements (not a docstring substring match), that `voice_runtime` never imports `voice.voice_api` or any `voice.*` submodule. |
| Undeclared `numpy` module-level imports (`voice/voice_engine.py`, `voice/wake_word.py`, `voice/tests/test_voice.py`) | Key finding — hazard persists | **Not reproduced.** `voice_runtime/tests/test_minimal_dependency_import.py::test_core_modules_import_without_heavy_dependencies` freshly imports every always-available `voice_runtime` submodule and asserts none of `numpy`/`torch`/`transformers`/`whisper`/`elevenlabs`/`boto3`/`pyttsx3`/`vibevoice` newly appear in `sys.modules` as a result. Passing. The legacy hazard itself remains unresolved in `voice/` (out of scope for Phase 1 — `voice/` was not modified). |
| `web/src/pages/VoiceConcierge.tsx` (PR #247 browser Web Speech API) | KEEP — fallback tier | **Represented, not modified.** `voice_runtime/providers/browser.py::BrowserSpeechProvider` is a server-side capability *descriptor* only (declares ASR+TTS, reports `AVAILABLE_DEGRADED`/client-side-dependent via preflight); it never calls browser APIs from Python. A regression test asserts the frontend file still contains `SpeechRecognition`/`speechSynthesis` markers, unchanged. |

See `SP_VOICE_002_PHASE1_CERTIFICATION.md` for the full architecture,
test, and validation record.

## Key finding: undeclared `numpy` dependency hazard persists

`numpy` is imported at module level in `voice/voice_engine.py`, `voice/wake_word.py`,
and `voice/tests/test_voice.py`, but is **not present in `requirements.txt`**.
This is the same defect class that broke PR #245's exact-head CI before the
`voice_concierge/` relocation (diagnosed and fixed earlier in this session).
It has not resurfaced only because nothing in current CI paths eagerly imports
`voice.<submodule>` attributes today, and because `numpy` happens to be
installed transitively in this environment. **Any SP-VOICE-002 work that
touches or re-exports `voice/` must either declare the dependency explicitly
or remove the eager import**, per the plan's Phase 0 lazy-loading requirement.

## Answer to the "key question": what should the legacy April implementation become?

Per the evidence above, the correct answer is **(2) a compatibility/utility
source behind new provider interfaces — not (1) the foundation, and not (4)
wholesale retirement.** Specifically:
- `persona.py` and `legal_nlp.py` are self-contained, low-risk, and genuinely
  reusable **as-is** (option "KEEP", not even needing adaptation).
- `voice_engine.py` and `speech_processor.py` contain real, useful
  algorithmic content (audio buffering/noise-floor detection, provider
  fallback-chain shape, legal pronunciation dictionary) but their *authority
  model* (raw credentials on dataclasses, no capability declarations, no
  governance hooks, global `logging.basicConfig()` side effects) is
  incompatible with SP-VOICE-002's required architecture and must not be
  reused verbatim — only specific functions/algorithms should be lifted into
  the new `voice_runtime/` structure.
- `voice_api.py` and `README.md` are net-negative artifacts (unauthenticated
  router; misleading docs) and should be retired outright.
