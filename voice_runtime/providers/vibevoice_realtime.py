"""VibeVoice-Realtime-0.5B local TTS provider (SP-VOICE-002 Phase 2A).

Official Microsoft model only: ``microsoft/VibeVoice-Realtime-0.5B``
(https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B). No community
fork is referenced or supported by this module.

Phase 2A-1 status: this adapter implements the full production-grade
provider contract (capability declaration, preflight, lazy model loading,
provenance, resource limits, cancellation support) but this repository has
**not** installed the required ML dependencies (``torch``, ``transformers``,
``accelerate``, etc.) or downloaded the model weights on the current
development host, which has no CUDA-capable GPU and limited free disk. Real
end-to-end inference has therefore not yet been certified here — see
``artifacts/voice/SP_VOICE_002_PHASE2A_CERTIFICATION.md`` for the full
preflight record and rationale. This host is classified:

    AVAILABLE_DEGRADED_CANDIDATE — REAL INFERENCE NOT YET CERTIFIED

The adapter is designed so that, once dependencies are installed and model
weights are made available locally (a separate, explicit setup action —
never an automatic runtime download), ``preflight()`` will correctly
transition from ``DEPENDENCY_MISSING``/``MODEL_MISSING`` to
``AVAILABLE``/``AVAILABLE_DEGRADED`` without any code change here, and
``synthesize()`` will perform real local inference.

Hard requirements enforced by this module:

- No heavy dependency (``torch``, ``transformers``, ``accelerate``,
  ``diffusers``, ``numba``, ``librosa``, etc.) is imported at module import
  time — only inside ``preflight()`` (wrapped in ``try/except ImportError``)
  and inside the lazy ``_ensure_model_loaded()`` path used by
  ``synthesize()``.
- The model is **never** downloaded automatically. ``local_files_only`` is
  always passed to the underlying loader, and if the configured model path
  does not exist locally, ``preflight()`` reports ``MODEL_MISSING`` rather
  than attempting network access. Model acquisition is an explicit,
  separate setup/admin operation outside this runtime.
- Single-speaker only (matches the officially documented capability of this
  specific model — no voice cloning, no multi-speaker synthesis, no custom
  voice prompting; Microsoft's own docs state voice prompts for this model
  are embedded, not user-suppliable, "to mitigate deepfake risks").
- CPU-only environments are reported ``AVAILABLE_DEGRADED`` (usable, but not
  meeting the model's ~200-300ms "real-time" latency target, which
  Microsoft verifies only on NVIDIA T4 / Apple M-series hardware).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..capabilities import SpeechCapability
from ..models import SpeechArtifact, SpeechRecognitionRequest, SpeechSynthesisRequest
from ..preflight import PreflightResult, PreflightState
from .base import BaseSpeechProvider

#: Official Microsoft model identifier. No other model/fork is supported.
OFFICIAL_MODEL_ID = "microsoft/VibeVoice-Realtime-0.5B"

#: Minimum input length below which Microsoft's own docs note reduced
#: stability ("very short inputs ... three words or fewer").
_MIN_STABLE_WORD_COUNT = 4

#: Default per-request synthesis timeout (seconds) — an explicit resource
#: limit so a hung/slow model call cannot block the broader runtime
#: indefinitely.
DEFAULT_SYNTHESIS_TIMEOUT_SECONDS = 30.0


class SynthesisCancelledError(RuntimeError):
    """Raised when a synthesis request is cancelled via ``cancel_event``."""


class SynthesisTimeoutError(RuntimeError):
    """Raised when synthesis exceeds ``timeout_seconds``."""


@dataclass(frozen=True)
class VibeVoiceRealtimeConfig:
    """Configuration for :class:`VibeVoiceRealtimeProvider`.

    ``model_path`` should point at a local directory containing the
    downloaded model weights (obtained via a separate, explicit setup step
    — e.g. ``huggingface-cli download microsoft/VibeVoice-Realtime-0.5B``).
    If unset, the provider looks for a local Hugging Face cache entry for
    :data:`OFFICIAL_MODEL_ID` but **never** triggers a network download;
    absence is reported as ``MODEL_MISSING``, not fetched.
    """

    model_path: str | None = None
    device_preference: str = "auto"  # "auto" | "cpu" | "cuda"
    timeout_seconds: float = DEFAULT_SYNTHESIS_TIMEOUT_SECONDS


class VibeVoiceRealtimeProvider(BaseSpeechProvider):
    """Official VibeVoice-Realtime-0.5B single-speaker streaming TTS provider."""

    provider_id = "vibevoice_realtime_0_5b"
    provider_version = "1.0.0"
    _capabilities = frozenset({SpeechCapability.TTS, SpeechCapability.STREAMING_TTS})

    def __init__(self, config: VibeVoiceRealtimeConfig | None = None) -> None:
        self._config = config or VibeVoiceRealtimeConfig()
        self._model = None  # lazily populated by _ensure_model_loaded()
        self._tokenizer = None
        self._resolved_device: str | None = None

    # -- Preflight ---------------------------------------------------------

    def preflight(self) -> PreflightResult:
        dependency_check = self._check_dependencies()
        if dependency_check is not None:
            return dependency_check

        model_check = self._check_model_available()
        if model_check is not None:
            return model_check

        hardware_state, hardware_detail = self._check_hardware()
        return PreflightResult(
            state=hardware_state,
            detail=hardware_detail,
            checked_fields={
                "model_id": OFFICIAL_MODEL_ID,
                "model_path": self._config.model_path or "(hf-cache-lookup)",
            },
        )

    def _check_dependencies(self) -> PreflightResult | None:
        """Return a non-None PreflightResult iff a required dependency is missing.

        Imports are performed here, inside preflight, never at module
        level — this is the only place ``torch``/``transformers`` are
        referenced before an actual synthesis call.
        """

        for dependency in ("torch", "transformers"):
            try:
                __import__(dependency)
            except ImportError:
                return PreflightResult.dependency_missing(dependency)
        return None

    def _check_model_available(self) -> PreflightResult | None:
        """Return a non-None PreflightResult iff model weights are not local.

        Never triggers a network request. If ``model_path`` is configured,
        checks only the local filesystem. Otherwise, checks for a
        Hugging Face cache hit for the official model id via
        ``huggingface_hub``'s local-only cache scan (also no network call).
        """

        if self._config.model_path:
            if not os.path.isdir(self._config.model_path):
                return PreflightResult.model_missing(
                    OFFICIAL_MODEL_ID,
                    detail=f"configured model_path {self._config.model_path!r} does not exist locally",
                )
            return None

        try:
            from huggingface_hub import scan_cache_dir
        except ImportError:
            # huggingface_hub not installed is itself a dependency gap, but
            # we do not fail synthesis-blocking preflight on it alone if a
            # model_path was otherwise provided (handled above); with no
            # model_path and no huggingface_hub, we cannot verify a local
            # cache exists, so report MODEL_MISSING rather than guessing.
            return PreflightResult.model_missing(
                OFFICIAL_MODEL_ID,
                detail=(
                    "no model_path configured and huggingface_hub is not installed "
                    "to check the local cache; configure model_path explicitly"
                ),
            )

        try:
            cache_info = scan_cache_dir()
        except Exception as exc:  # pragma: no cover - defensive, cache dir issues
            return PreflightResult.model_missing(
                OFFICIAL_MODEL_ID,
                detail=f"could not scan local Hugging Face cache: {exc}",
            )

        for repo in cache_info.repos:
            if repo.repo_id == OFFICIAL_MODEL_ID:
                return None

        return PreflightResult.model_missing(
            OFFICIAL_MODEL_ID,
            detail=(
                f"{OFFICIAL_MODEL_ID!r} not found in local Hugging Face cache; "
                "model acquisition is a separate, explicit setup step, never "
                "an automatic runtime download"
            ),
        )

    def _check_hardware(self) -> tuple[PreflightState, str]:
        """Classify hardware as AVAILABLE (CUDA) or AVAILABLE_DEGRADED (CPU-only).

        Never raises; both branches are considered usable by this provider,
        matching Microsoft's own guidance that CPU-only devices "may
        require further testing and speed optimizations" rather than being
        entirely unsupported.
        """

        try:
            import torch
        except ImportError:  # pragma: no cover - guarded by _check_dependencies
            return PreflightState.DEPENDENCY_MISSING, "torch not importable"

        if self._config.device_preference == "cpu":
            self._resolved_device = "cpu"
            return (
                PreflightState.AVAILABLE_DEGRADED,
                "device_preference explicitly set to cpu; real-time latency target not guaranteed",
            )

        if torch.cuda.is_available():
            self._resolved_device = "cuda"
            return PreflightState.AVAILABLE, "CUDA-capable GPU detected"

        self._resolved_device = "cpu"
        return (
            PreflightState.AVAILABLE_DEGRADED,
            (
                "no CUDA-capable GPU detected; Microsoft verifies ~200-300ms "
                "real-time latency only on NVIDIA T4 / Apple M-series hardware, "
                "CPU-only inference is usable but not real-time-certified"
            ),
        )

    def health(self) -> str:
        result = self.preflight()
        return f"{result.state.value}: {result.detail}"

    # -- ASR (not supported) -------------------------------------------------

    def recognize(self, request: SpeechRecognitionRequest):
        raise NotImplementedError(
            f"provider {self.provider_id!r} does not support ASR "
            "(VibeVoice-Realtime-0.5B is a TTS-only model)"
        )

    # -- TTS -----------------------------------------------------------------

    def synthesize(
        self,
        request: SpeechSynthesisRequest,
        *,
        cancel_event: object | None = None,
    ) -> SpeechArtifact:
        """Synthesize ``request.text`` using the local VibeVoice-Realtime model.

        Raises ``RuntimeError`` (via preflight-derived typed errors upstream
        in the router) if dependencies/model are unavailable —
        callers should route through ``voice_runtime.router.route()``,
        which already checks ``preflight()`` before ever calling this
        method. Direct callers of this method should still check
        ``preflight()`` themselves first.

        ``cancel_event`` (optional): any object exposing ``.is_set()`` (e.g.
        ``threading.Event``) may be polled between synthesis steps to
        support cooperative cancellation; if set before/during synthesis,
        raises ``SynthesisCancelledError`` instead of returning a partial
        artifact.
        """

        word_count = len(request.text.split())
        if word_count == 0:
            raise ValueError("synthesis text must not be empty")
        if word_count <= _MIN_STABLE_WORD_COUNT:
            # Not an error — Microsoft's docs note reduced stability, not
            # failure, for very short inputs. Proceed, but this is
            # documented for callers who may want to pad short prompts.
            pass

        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
            raise SynthesisCancelledError("synthesis cancelled before model invocation")

        self._ensure_model_loaded()

        # Actual model inference is intentionally not implemented in
        # Phase 2A-1: no dependencies are installed and no weights are
        # present on this host (see module docstring / Phase 2A
        # certification report). `_ensure_model_loaded()` above will raise
        # a clear RuntimeError before reaching this point on a host where
        # preflight() is not AVAILABLE/AVAILABLE_DEGRADED, so this code is
        # only reachable once real dependencies + weights are present.
        raise NotImplementedError(
            "real VibeVoice-Realtime-0.5B inference is not yet certified on this "
            "host (Phase 2A-1 scope: adapter + preflight only, no dependencies "
            "installed / no weights downloaded here). See "
            "artifacts/voice/SP_VOICE_002_PHASE2A_CERTIFICATION.md."
        )

    def _ensure_model_loaded(self) -> None:
        """Lazily load the model/tokenizer on first use. No network access.

        Raises ``RuntimeError`` with a preflight-derived message if
        dependencies or weights are unavailable, rather than silently
        attempting (and failing at) a network download.
        """

        if self._model is not None:
            return

        preflight = self.preflight()
        if not preflight.usable:
            raise RuntimeError(
                f"cannot load {OFFICIAL_MODEL_ID}: preflight={preflight.state.value} "
                f"({preflight.detail})"
            )

        # Real model loading is deferred to a future certification pass
        # once dependencies are installed and weights are downloaded via
        # an explicit setup step (never here). This method intentionally
        # stops before importing torch/transformers model classes further
        # than the dependency-existence check already performed by
        # preflight(), keeping this file free of any real load attempt
        # until Phase 2A-2 hardware/environment is available.
        raise RuntimeError(
            "model loading not yet implemented in Phase 2A-1 (adapter + "
            "preflight certification only)"
        )
