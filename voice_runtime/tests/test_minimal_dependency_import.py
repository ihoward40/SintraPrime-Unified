"""Regression test: importing voice_runtime never requires optional heavy deps.

This directly guards against the class of defect diagnosed earlier in this
session for the legacy ``voice/`` package (module-level ``numpy`` imports
absent from ``requirements.txt``, which broke PR #245's exact-head CI when
an unrelated test path eagerly triggered them).
"""

from __future__ import annotations

import importlib
import sys

_HEAVY_MODULE_PREFIXES = (
    "numpy",
    "torch",
    "transformers",
    "whisper",
    "elevenlabs",
    "boto3",
    "pyttsx3",
    "vibevoice",
)

_VOICE_RUNTIME_MODULES = (
    "voice_runtime",
    "voice_runtime.capabilities",
    "voice_runtime.errors",
    "voice_runtime.preflight",
    "voice_runtime.provenance",
    "voice_runtime.models",
    "voice_runtime.registry",
    "voice_runtime.router",
    "voice_runtime.providers",
    "voice_runtime.providers.base",
    "voice_runtime.providers.mock",
    "voice_runtime.providers.legacy",
    "voice_runtime.providers.browser",
    "voice_runtime.audio",
    "voice_runtime.audio.normalization",
    "voice_runtime.audio.formats",
)


def _purge_voice_runtime_from_sys_modules() -> None:
    for name in list(sys.modules):
        if name == "voice_runtime" or name.startswith("voice_runtime."):
            del sys.modules[name]


def test_core_modules_import_without_heavy_dependencies():
    """Freshly importing every always-available voice_runtime module must
    never cause a heavy/optional dependency to appear in sys.modules."""

    _purge_voice_runtime_from_sys_modules()
    before = {name for name in sys.modules if name.split(".")[0] in {p.split(".")[0] for p in _HEAVY_MODULE_PREFIXES}}

    for module_name in _VOICE_RUNTIME_MODULES:
        importlib.import_module(module_name)

    after = {name for name in sys.modules if name.split(".")[0] in {p.split(".")[0] for p in _HEAVY_MODULE_PREFIXES}}

    newly_imported = after - before
    assert not newly_imported, (
        f"importing voice_runtime modules unexpectedly pulled in heavy "
        f"dependencies: {sorted(newly_imported)}"
    )


def test_voice_runtime_package_has_version():
    import voice_runtime

    assert isinstance(voice_runtime.__version__, str)
    assert voice_runtime.__version__
