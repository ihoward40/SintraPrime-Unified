"""Tests for the preflight state model itself."""

from __future__ import annotations

from voice_runtime.preflight import PreflightResult, PreflightState


def test_available_is_usable():
    result = PreflightResult.available()
    assert result.usable


def test_dependency_missing_is_not_usable():
    result = PreflightResult.dependency_missing("torch")
    assert not result.usable
    assert result.state == PreflightState.DEPENDENCY_MISSING
    assert "torch" in result.detail


def test_model_missing_is_not_usable():
    result = PreflightResult.model_missing("vibevoice-1.5b")
    assert not result.usable
    assert result.state == PreflightState.MODEL_MISSING


def test_disabled_is_not_usable():
    result = PreflightResult.disabled()
    assert not result.usable
    assert result.state == PreflightState.DISABLED


def test_degraded_is_still_usable():
    result = PreflightResult(state=PreflightState.AVAILABLE_DEGRADED, detail="slow path")
    assert result.usable


def test_preflight_result_is_frozen():
    import dataclasses

    result = PreflightResult.available()
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        result.state = PreflightState.DISABLED  # type: ignore[misc]
