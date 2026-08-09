"""Speech-runtime provider implementations.

This subpackage is intentionally free of eager heavy imports at the package
level — importing ``voice_runtime.providers`` must not require numpy,
torch, transformers, or any external provider SDK. Individual provider
modules (e.g. a future VibeVoice adapter) may depend on heavy packages
internally, but only import them lazily, inside methods that run after
``preflight()`` has confirmed availability.
"""

from __future__ import annotations

__all__: list[str] = []
