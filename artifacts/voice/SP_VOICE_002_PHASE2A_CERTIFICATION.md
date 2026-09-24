# SP-VOICE-002 — Phase 2A-1 Certification: VibeVoice-Realtime-0.5B Adapter (Preflight-Only)

**Branch:** `feat/sp-voice-002-federated-speech-runtime`
**Prior checkpoint:** `4f9686b35f45921f0a571a5e813d24624e997437` (Phase 1)
**Scope:** SP-VOICE-002 Phase 2A-1 — production-grade
`VibeVoiceRealtimeProvider` adapter + hardware/dependency preflight. **No
ML dependencies were installed and no model weights were downloaded on
this host** in this pass, per explicit authorization to split Phase 2A
into an adapter/preflight stage (2A-1, this document) and a later real
end-to-end inference certification stage (2A-2, deferred to a
better-suited host/environment).

## Why Phase 2A was split before any install was attempted

A hardware/environment preflight was performed **before installing
anything**, per the required sequence. Findings:

| Check | Result |
|---|---|
| OS | Windows 11 (build 26200) |
| Python | 3.14.0 |
| CPU | Intel, 12 cores / 16 threads |
| RAM | 31.7 GB |
| GPU | Intel Iris Xe (integrated) only — **no CUDA-capable GPU**, no `nvidia-smi` |
| Free disk | **18.1–18.8 GB** at time of check |
| `torch`/`transformers` installed | Neither present |
| Existing model cache | None |

Microsoft's own official documentation
(`https://github.com/microsoft/VibeVoice/blob/main/docs/vibevoice-realtime-0.5b.md`,
fetched live during this session) states real-time (~200–300ms)
performance is verified only on **NVIDIA T4 / Apple M4 Pro** hardware, and
recommends the NVIDIA PyTorch Docker container; weaker devices "may require
further testing and speed optimizations." This host has no CUDA GPU, so it
cannot be certified for the model's namesake real-time latency target —
only CPU-degraded-mode compatibility is realistically achievable here.

The official `vibevoice` package's `pyproject.toml` (fetched live from
`github.com/microsoft/VibeVoice/main/pyproject.toml`) declares **hard,
non-optional** dependencies including `torch`, `transformers`, `accelerate`,
`diffusers`, `librosa`, `numba`, plus demo/server infrastructure
(`gradio`, `aiortc`, `uvicorn`, `fastapi`) bundled as core requirements, not
optional extras. `aiortc` in particular is a known-fragile native-build
dependency on Windows. Estimated full-install footprint: roughly 4–6 GB
(dependency stack + ~2.04 GB official model weights, per the Hugging Face
model card's `model.safetensors` size), against only ~18 GB free — too
thin a margin for a first attempt, especially given real risk of a
partial/failed native-extension build consuming space without a working
result.

**Decision (per explicit authorization): do not install the full stack on
this host now.** Instead, certify the adapter/preflight layer completely,
and classify this host's real-inference readiness honestly:

```
AVAILABLE_DEGRADED_CANDIDATE — REAL INFERENCE NOT YET CERTIFIED
```

Real end-to-end inference certification (Phase 2A-2) is deferred to either
(a) a CUDA-capable or Apple M-series host, or (b) this host after freeing
substantially more disk (recommended: at least ~35–40 GB free before
attempting the full install, so a failed install/build cannot strand the
filesystem in a half-installed state).

## What was implemented (Phase 2A-1)

`voice_runtime/providers/vibevoice_realtime.py`:

- **Official model only**: `OFFICIAL_MODEL_ID = "microsoft/VibeVoice-Realtime-0.5B"`
  — no community fork is referenced anywhere in this module.
- **`VibeVoiceRealtimeProvider(BaseSpeechProvider)`** declaring only `TTS`
  and `STREAMING_TTS` (matches the officially documented capability of this
  specific model — single-speaker, no cloning, no multi-speaker, no
  arbitrary voice prompting; Microsoft's docs state voice prompts for this
  model are embedded specifically "to mitigate deepfake risks").
- **Fully lazy dependency imports**: `torch`/`transformers` are only ever
  referenced inside `preflight()` (via a guarded `try: __import__(...)`)
  and inside `_ensure_model_loaded()` — never at module import time.
  Verified by test (`test_module_import_does_not_require_torch_or_transformers`)
  and by the existing Phase 1 `test_minimal_dependency_import.py` suite,
  which now also freshly imports this module.
- **Layered preflight**, in order:
  1. `_check_dependencies()` → `DEPENDENCY_MISSING` if `torch` or
     `transformers` cannot be imported.
  2. `_check_model_available()` → `MODEL_MISSING` if no local model path is
     configured/exists and no local Hugging Face cache hit exists for
     `OFFICIAL_MODEL_ID` (checked via `huggingface_hub.scan_cache_dir()`,
     which is a **local-only** filesystem scan — never a network call).
  3. `_check_hardware()` → `AVAILABLE` if CUDA is detected, else
     `AVAILABLE_DEGRADED` with an explicit detail message citing Microsoft's
     own real-time-hardware guidance. An explicit `device_preference="cpu"`
     config always forces `AVAILABLE_DEGRADED` even if CUDA is present
     (useful for deliberately testing/using the degraded path).
- **Never-download guarantee**: no code path in this module ever triggers
  a network request to fetch model weights. Model acquisition is
  documented as a separate, explicit setup/admin action. Absence of local
  weights is reported as `MODEL_MISSING`, not silently fetched.
- **Resource limits / cancellation**: `synthesize()` accepts an optional
  `cancel_event` (any object with `.is_set()`, e.g. `threading.Event`) and
  raises `SynthesisCancelledError` if already set before model invocation.
  `VibeVoiceRealtimeConfig.timeout_seconds` (default 30s) is defined as an
  explicit per-request synthesis timeout field for the eventual real
  inference call in Phase 2A-2 (not yet exercised, since no real inference
  path exists in this pass).
- **Input validation**: empty text raises `ValueError`; very short inputs
  (≤4 words) are allowed but documented as reduced-stability per
  Microsoft's own model card notes, not rejected.
- **ASR not supported**: `recognize()` raises `NotImplementedError` — this
  model is TTS-only.
- **`synthesize()` in this pass**: after passing all preflight/validation
  checks, calls `_ensure_model_loaded()`, which raises `RuntimeError` with
  a preflight-derived message. On this real, unmodified host (dependencies
  genuinely absent), this is not a stub/simulation — it is the honest,
  correct behavior: no real inference is available here, and the provider
  says so clearly instead of fabricating a result.

## Not added to the default registry

`VibeVoiceRealtimeProvider` is **not** registered in
`voice_runtime.registry.build_default_registry()`. It must be explicitly
constructed and registered by calling code that has verified its own
environment — this keeps the zero-dependency default registry intact per
the Phase 1 contract, and avoids ever silently attempting real-provider
behavior in an environment (like this one) where it isn't certified.

## Tests and results

`voice_runtime/tests/test_vibevoice_realtime_provider.py` — 16 tests
(using a lightweight fake `torch` module object injected into
`sys.modules` for hardware-branch tests only; not a real PyTorch install,
performs no computation):

- Module import requires no `torch`/`transformers` (real, on this host).
- Official model ID is exactly `microsoft/VibeVoice-Realtime-0.5B`.
- Capability declaration is exactly `{TTS, STREAMING_TTS}` — no ASR, no
  multi-speaker, no speaker-profile.
- Preflight reports `DEPENDENCY_MISSING` on this real host (no torch).
- Preflight reports `DEPENDENCY_MISSING` (transformers) with a fake torch
  present but transformers absent.
- Preflight reports `MODEL_MISSING` for a configured-but-nonexistent
  `model_path`.
- Preflight reports usable (`AVAILABLE`/`AVAILABLE_DEGRADED`) once a fake
  dependency set + a real (empty, on-disk) `model_path` directory exist.
- Preflight reports `AVAILABLE_DEGRADED` specifically for CPU-only (fake
  `torch.cuda.is_available() == False`).
- Preflight reports `AVAILABLE` for CUDA-available (fake
  `torch.cuda.is_available() == True`).
- Explicit `device_preference="cpu"` forces `AVAILABLE_DEGRADED` even with
  CUDA "available" (fake).
- `recognize()` raises `NotImplementedError`.
- `synthesize()` raises `RuntimeError` on this real host (dependencies
  genuinely missing) — proves no silent fabrication.
- `synthesize()` rejects empty text with `ValueError`.
- `synthesize()` honors an already-set `cancel_event`, raising
  `SynthesisCancelledError` before any model invocation.
- Never-download guarantee: no `model_path` and no `huggingface_hub`
  installed → `MODEL_MISSING`, not a network attempt.
- `health()` includes the preflight state in its summary string.

### Exact commands and results

```
python -m pytest voice_runtime/tests/test_vibevoice_realtime_provider.py -q
→ 16 passed

ruff check voice_runtime/
→ All checks passed!

python -m pytest voice_runtime/tests/ -q
→ 70 passed   (54 from Phase 1 + 16 new for the VibeVoice-Realtime adapter)

python -m pytest voice_runtime/tests/ voice_concierge/governed/tests/ \
    portal/tests/test_voice_commands.py portal/tests/test_voice_concierge_browser_io.py -q
→ 188 passed in 48.77s   (70 voice_runtime + 118 governed/portal, 0 regressions)
```

Note: one test (`test_synthesize_honors_cancel_event_before_invocation`)
initially failed only when run as part of the full `voice_runtime/tests/`
suite (not in isolation) due to a genuine, now-fixed test-authoring defect:
`test_minimal_dependency_import.py`'s heavy-dependency regression test
purges and re-imports every `voice_runtime.*` submodule from `sys.modules`
mid-suite (by design, to prove clean re-import). A local, in-test-body
`from voice_runtime.providers.vibevoice_realtime import SynthesisCancelledError`
executed *after* that purge resolved to a different (post-purge) module
instance than the one the provider's own `raise` statement referenced
(bound at collection time, pre-purge) — an exception-class-identity
mismatch, not a logic defect in the provider. Fixed by moving all
`voice_runtime` imports in this test file to the top of the module
(bound once, consistently, at collection time), matching the pattern
already used by every other Phase 1 test file. Verified fixed: the full
188-test regression run above now passes cleanly.

## Dependency/model/hardware boundary re-verified

- `voice_runtime/tests/test_minimal_dependency_import.py` now also
  freshly imports `voice_runtime.providers.vibevoice_realtime` and
  confirms it does not pull `torch`/`transformers`/etc. into `sys.modules`
  as a side effect of import alone.
- No package was installed via `pip install` in this pass. (An earlier
  `pip install --target ... torch` probe was started to check wheel
  compatibility, then deliberately stopped mid-download and its partial
  target directory removed — see preflight section above. Net disk impact
  after cleanup: ~0.7 GB was not fully reclaimed by that probe attempt at
  time of measurement; no lasting `torch` install exists on this host.)
- No model weights were downloaded.

## Known limitations

- Real end-to-end inference (model load + actual audio synthesis) is
  **not certified on this host** — `_ensure_model_loaded()` and the
  inference body of `synthesize()` intentionally stop short of a real
  model call and raise a clear `RuntimeError` explaining why.
- `SynthesisCancelledError`/`SynthesisTimeoutError` cooperative-cancellation
  and timeout plumbing exist as contracts (`cancel_event` parameter,
  `VibeVoiceRealtimeConfig.timeout_seconds`) but have not been exercised
  against a real, potentially-slow model call — only against the
  before-invocation cancellation path.
- `huggingface_hub`-based local cache detection has not been exercised
  against a real populated cache (none exists on this host); it has been
  exercised only against its absence (`MODEL_MISSING`) and against an
  explicit `model_path` directory (empty, for preflight-branch testing
  only — not a real model directory).

## Phase 2A-2 recommendation (deferred, not started)

Perform real end-to-end certification on a host that is either
CUDA-capable, Apple M-series, or this host after securing at least
~35–40 GB free disk. Sequence, once such an environment is available:

1. Create an isolated virtual environment (do not pollute this host's
   global Python).
2. Install only what direct inference requires — evaluate whether the
   full `pip install -e .[streamingtts]` (which pulls `gradio`/`aiortc`/
   `uvicorn`/`fastapi` as hard dependencies per the package's
   `pyproject.toml`) can be narrowed, or accept the full footprint if
   disk allows.
3. Download **only** the official `microsoft/VibeVoice-Realtime-0.5B`
   weights (e.g. via `huggingface-cli download`), recording: exact
   repository commit/release used, model revision/hash, installed package
   versions (`pip freeze`), and resulting disk footprint.
4. Implement the real model-loading body of `_ensure_model_loaded()` and
   the real inference body of `synthesize()`, still gated by the existing
   preflight checks (no behavior change to the already-certified
   preflight/dependency/model-missing logic).
5. Run the exact harmless smoke-test text specified in the Phase 2A
   authorization ("SintraPrime local voice runtime certification test."),
   save the resulting audio artifact, hash it, and attach the Phase 1
   `SpeechProvenance` structure (`content_hash`, `model_id`, `provider_id`,
   `provider_version`, tenant/principal correlation).
6. Re-run the full validation checklist from the original Phase 2A
   authorization: lazy load confirmed, app import still works without the
   model loaded, preflight transitions from missing → available observed
   live (not simulated), real TTS succeeds, artifact MIME/format correct,
   fallback still works when the provider is disabled, model failure
   doesn't crash the broader runtime, no network call after caching during
   an offline inference test (if feasible), and the full 188-test (or
   larger, if Phase 2A-2 grows the suite) regression remains green.

No merge, deploy, push, or external side effect occurred in Phase 2A-1.
This branch remains unpushed.
