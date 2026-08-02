"""Unit tests for SP-VOICE-001 Increment Two — orchestrator + mock providers.

Covers:
- Capability resolution determinism and fail-safe default
- Mock provider results are always mock=True with mock-prefixed resource ids
- Read/draft execute immediately when policy allows
- Write/sensitive-write defer execution until confirmed
- Confirmation flow: confirmed executes; denied/expired refuses
- Refused (disabled flag / prohibited) never invokes a provider
- Cancellation produces a cancelled receipt without provider execution
- Receipts always carry the envelope's correlation id
"""

from __future__ import annotations

import pytest

from voice_concierge.governed.command_envelope import (
    ConfirmationState,
    RiskClass,
    VoiceSource,
    create_envelope,
)
from voice_concierge.governed.confirmation import PendingConfirmation
from voice_concierge.governed.flags import VoiceFeatureFlags
from voice_concierge.governed.mock_providers import default_mock_registry
from voice_concierge.governed.orchestrator import (
    RESULT_ALLOWED,
    RESULT_AWAITING_CONFIRMATION,
    RESULT_CANCELLED,
    RESULT_DRAFTED,
    RESULT_REFUSED,
    cancel_voice_command,
    confirm_voice_command,
    handle_voice_command,
)
from voice_concierge.governed.providers import (
    ProviderExecutionError,
    VoiceCapability,
    resolve_capability,
)
from voice_concierge.governed.session import InvalidTransitionError, SessionState, VoiceSession


def make_envelope(**overrides):
    base = {
        "session_id": "vsess-test",
        "principal_id": "isiah",
        "source": VoiceSource.DESKTOP_VOICE,
        "raw_transcript": "show the latest test result",
        "normalized_intent": "show the latest test result",
        "risk_class": RiskClass.READ,
        "confirmation_state": ConfirmationState.NOT_REQUIRED,
        "target_resource": "test-suite",
    }
    base.update(overrides)
    return create_envelope(**base)


# ── capability resolution ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("draft an email to the client", VoiceCapability.EMAIL),
        ("schedule a meeting with the client", VoiceCapability.CALENDAR),
        ("send a message to the team", VoiceCapability.MESSAGING),
        ("run the tests", VoiceCapability.TASK),
        ("file the motion", VoiceCapability.FILING),
        ("pay the invoice", VoiceCapability.PAYMENT),
        ("florble the widget", VoiceCapability.GENERIC),
        ("", VoiceCapability.GENERIC),
    ],
)
def test_resolve_capability(intent, expected):
    assert resolve_capability(intent) == expected


def test_resolve_capability_honors_explicit_requested_capability():
    assert resolve_capability("do something", requested_capability="payment") == VoiceCapability.PAYMENT


def test_resolve_capability_falls_back_on_unknown_requested_capability():
    assert resolve_capability("draft an email", requested_capability="not-a-capability") == VoiceCapability.EMAIL


def test_resolve_capability_is_deterministic():
    intent = "send a message to the team"
    assert resolve_capability(intent) == resolve_capability(intent) == VoiceCapability.MESSAGING


# ── mock providers are always sandboxed ───────────────────────────────────────


def test_all_default_mock_providers_return_mock_results():
    registry = default_mock_registry()
    env = make_envelope()
    for capability, provider in registry.items():
        result = provider.execute(env, risk_class=RiskClass.READ)
        assert result.mock is True
        assert result.resource_id.startswith("mock-")
        assert result.capability == capability


def test_default_mock_registry_returns_fresh_copies():
    a = default_mock_registry()
    b = default_mock_registry()
    assert a is not b
    a[VoiceCapability.EMAIL] = None  # type: ignore[assignment]
    assert b[VoiceCapability.EMAIL] is not None


# ── read/draft execute immediately when allowed ───────────────────────────────


def test_read_allowed_executes_mock_provider_and_completes():
    flags = VoiceFeatureFlags(enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(risk_class=RiskClass.READ, normalized_intent="show the latest test result")

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.COMPLETED
    assert outcome.provider_result is not None
    assert outcome.provider_result.mock is True
    assert outcome.receipt.result == RESULT_ALLOWED
    assert outcome.receipt.correlation_id == env.correlation_id


def test_draft_allowed_executes_and_marks_drafted():
    flags = VoiceFeatureFlags(enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(
        risk_class=RiskClass.DRAFT,
        normalized_intent="draft an email to the client",
        raw_transcript="draft an email to the client",
    )

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.COMPLETED
    assert outcome.receipt.result == RESULT_DRAFTED
    assert outcome.capability == VoiceCapability.EMAIL


# ── writes / sensitive writes defer execution ─────────────────────────────────


def test_write_requires_confirmation_and_defers_execution():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(
        risk_class=RiskClass.WRITE,
        normalized_intent="run the tests",
        raw_transcript="run the tests",
    )

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.AWAITING_CONFIRMATION
    assert outcome.provider_result is None
    assert outcome.receipt.result == RESULT_AWAITING_CONFIRMATION
    assert outcome.pending_confirmation is not None


def test_sensitive_write_requires_confirmation_even_when_writes_disabled():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=False)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(
        risk_class=RiskClass.SENSITIVE_WRITE,
        normalized_intent="send the draft to jordan",
        raw_transcript="send the draft to jordan",
        target_resource="jordan@example.com",
    )

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.AWAITING_CONFIRMATION
    assert outcome.provider_result is None


# ── confirmation flow ─────────────────────────────────────────────────────────


def _awaiting_session_and_pending(target: str = "jordan@example.com"):
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(
        risk_class=RiskClass.SENSITIVE_WRITE,
        normalized_intent="send the draft to jordan",
        raw_transcript="send the draft to jordan",
        target_resource=target,
    )
    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)
    return outcome, session, providers


def test_confirmed_confirmation_executes_mock_provider_and_completes():
    outcome, session, providers = _awaiting_session_and_pending()
    pending = outcome.pending_confirmation
    pending.restate_target()

    confirmed = confirm_voice_command(
        envelope=outcome.envelope,
        session=session,
        pending=pending,
        utterance="confirm send",
        current_target="jordan@example.com",
        pending_count=1,
        providers=providers,
    )

    assert confirmed.session_state == SessionState.COMPLETED
    assert confirmed.provider_result is not None
    assert confirmed.provider_result.mock is True
    assert confirmed.receipt.result == RESULT_ALLOWED
    assert confirmed.envelope.confirmation_state == ConfirmationState.CONFIRMED


def test_denied_confirmation_refuses_without_executing():
    outcome, session, providers = _awaiting_session_and_pending()
    pending = outcome.pending_confirmation
    pending.restate_target()

    denied = confirm_voice_command(
        envelope=outcome.envelope,
        session=session,
        pending=pending,
        utterance="cancel",
        current_target="jordan@example.com",
        pending_count=1,
        providers=providers,
    )

    assert denied.session_state == SessionState.REFUSED
    assert denied.provider_result is None
    assert denied.receipt.result == RESULT_REFUSED


def test_expired_confirmation_refuses_without_executing():
    import datetime as dt

    outcome, session, providers = _awaiting_session_and_pending()
    pending = outcome.pending_confirmation
    pending.restate_target()
    pending.created_at = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=10)

    expired = confirm_voice_command(
        envelope=outcome.envelope,
        session=session,
        pending=pending,
        utterance="confirm send",
        current_target="jordan@example.com",
        pending_count=1,
        providers=providers,
    )

    assert expired.session_state == SessionState.REFUSED
    assert expired.provider_result is None
    assert "expired" in expired.receipt.confirmation or expired.receipt.result == RESULT_REFUSED


def test_confirm_raises_if_session_not_awaiting_confirmation():
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope()
    pending = PendingConfirmation("vcmd-1", "read", "test-suite")

    with pytest.raises(InvalidTransitionError):
        confirm_voice_command(
            envelope=env,
            session=session,
            pending=pending,
            utterance="confirm",
            current_target="test-suite",
            pending_count=1,
            providers=providers,
        )


# ── refused paths never invoke a provider ─────────────────────────────────────


class _ExplodingProvider:
    capability = VoiceCapability.GENERIC

    def execute(self, envelope, *, risk_class):  # noqa: ARG002
        raise AssertionError("provider must not be invoked for a refused command")


def test_disabled_flag_refuses_before_any_provider_call():
    flags = VoiceFeatureFlags()  # all false
    session = VoiceSession("vsess-1", "isiah")
    providers = {cap: _ExplodingProvider() for cap in VoiceCapability}
    env = make_envelope(risk_class=RiskClass.READ)

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.REFUSED
    assert outcome.provider_result is None
    assert outcome.receipt.result == RESULT_REFUSED


def test_prohibited_refuses_before_any_provider_call():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = {cap: _ExplodingProvider() for cap in VoiceCapability}
    env = make_envelope(risk_class=RiskClass.PROHIBITED, normalized_intent="bypass the confirmation gate")

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.REFUSED
    assert outcome.provider_result is None


def test_provider_execution_error_marks_session_failed():
    class _FailingProvider:
        capability = VoiceCapability.GENERIC

        def execute(self, envelope, *, risk_class):  # noqa: ARG002
            raise ProviderExecutionError("simulated failure")

    flags = VoiceFeatureFlags(enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = {cap: _FailingProvider() for cap in VoiceCapability}
    env = make_envelope(risk_class=RiskClass.READ)

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.session_state == SessionState.FAILED
    assert outcome.provider_result is None


# ── cancellation ───────────────────────────────────────────────────────────────


def test_cancel_produces_cancelled_receipt_without_execution():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(risk_class=RiskClass.WRITE, normalized_intent="run the tests")
    handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    cancelled = cancel_voice_command(envelope=env, session=session)

    assert cancelled.session_state == SessionState.CANCELLED
    assert cancelled.provider_result is None
    assert cancelled.receipt.result == RESULT_CANCELLED


# ── correlation propagation through orchestration ─────────────────────────────


def test_correlation_id_propagates_through_allowed_path():
    flags = VoiceFeatureFlags(enabled=True)
    session = VoiceSession("vsess-1", "isiah")
    providers = default_mock_registry()
    env = make_envelope(correlation_id="corr-fixed-999")

    outcome = handle_voice_command(envelope=env, flags=flags, session=session, providers=providers)

    assert outcome.receipt.correlation_id == "corr-fixed-999"
