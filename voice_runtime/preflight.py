"""Provider/runtime preflight state model.

Preflight answers "can this provider actually run right now, and if not,
why?" without ever crashing application startup. A provider that requires a
missing optional dependency, a missing model file, or insufficient hardware
must report a typed, inspectable state instead of raising on import or on
registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PreflightState(str, Enum):
    """Coarse-grained availability state for a speech provider."""

    AVAILABLE = "available"
    """Provider is fully available and ready to use."""

    AVAILABLE_DEGRADED = "available_degraded"
    """Provider is usable but running in a reduced-capability/slower mode."""

    DISABLED = "disabled"
    """Provider is administratively disabled (feature-flagged off)."""

    DEPENDENCY_MISSING = "dependency_missing"
    """A required optional dependency (package) is not installed."""

    MODEL_MISSING = "model_missing"
    """A required model artifact/weights file is not present locally."""

    HARDWARE_INSUFFICIENT = "hardware_insufficient"
    """Available hardware (CPU/GPU/RAM/VRAM/disk) does not meet requirements."""

    CONFIGURATION_ERROR = "configuration_error"
    """Provider configuration is present but invalid/incomplete."""

    UNSUPPORTED = "unsupported"
    """Provider does not support the current platform/environment at all."""


#: States in which a provider may actually be selected for routing.
USABLE_STATES: frozenset[PreflightState] = frozenset(
    {PreflightState.AVAILABLE, PreflightState.AVAILABLE_DEGRADED}
)


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of checking whether a provider can currently be used.

    ``detail`` should be a short, human-readable explanation — especially
    important for non-``AVAILABLE`` states so operators/tests can see *why*
    a provider was skipped without reading provider source code.
    """

    state: PreflightState
    detail: str = ""
    checked_fields: dict[str, str] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        """Whether a provider in this state may be selected for routing."""
        return self.state in USABLE_STATES

    @classmethod
    def available(cls, detail: str = "", **checked_fields: str) -> PreflightResult:
        return cls(PreflightState.AVAILABLE, detail=detail, checked_fields=checked_fields)

    @classmethod
    def dependency_missing(cls, dependency: str, detail: str = "") -> PreflightResult:
        return cls(
            PreflightState.DEPENDENCY_MISSING,
            detail=detail or f"required dependency {dependency!r} is not installed",
            checked_fields={"dependency": dependency},
        )

    @classmethod
    def model_missing(cls, model_id: str, detail: str = "") -> PreflightResult:
        return cls(
            PreflightState.MODEL_MISSING,
            detail=detail or f"required model {model_id!r} is not present locally",
            checked_fields={"model_id": model_id},
        )

    @classmethod
    def disabled(cls, detail: str = "provider is disabled by configuration") -> PreflightResult:
        return cls(PreflightState.DISABLED, detail=detail)
