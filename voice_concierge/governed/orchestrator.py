"""Orchestrator for SP-VOICE-001 — Increment Two.

Wires the Increment One foundation (classifier, policy, session, confirmation,
receipts) to Increment Two's provider layer. This is the FIRST place in the
package that performs any "execution" — and execution here always means
invoking a mock/sandboxed provider (``mock_providers.py``). Nothing in this
module ever contacts a real telephony, calendar, messaging, filing, or payment
backend.

Governing rule, unchanged from Increment One:

    Voice may request and coordinate. Existing SintraPrime policy decides,
    records, approves, executes, or refuses.

Increment Two adds: policy-approved reads and drafts execute immediately
against mock providers; writes and sensitive writes execute against mock
providers ONLY after an explicit, exact-target confirmation; prohibited and
flag-disabled requests never reach a provider at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .command_envelope import ConfirmationState, RiskClass, VoiceCommandEnvelope
from .confirmation import ConfirmationOutcome, PendingConfirmation
from .flags import TranscriptRetention, VoiceFeatureFlags
from .policy import PolicyDecision, PolicyResult, evaluate
from .providers import (
    ProviderExecutionError,
    ProviderResult,
    VoiceActionProvider,
    VoiceCapability,
    resolve_capability,
)
from .receipts import VoiceReceipt, build_receipt
from .session import InvalidTransitionError, SessionState, VoiceSession

# Results a receipt records; these are outcome labels, not provider actions.
RESULT_ALLOWED = "completed"
RESULT_DRAFTED = "drafted"
RESULT_AWAITING_CONFIRMATION = "awaiting_confirmation"
RESULT_REFUSED = "refused"
RESULT_FAILED = "failed"
RESULT_CANCELLED = "cancelled"


@dataclass(frozen=True)
class OrchestrationOutcome:
    """Immutable result of driving one voice command envelope to a decision point."""

    envelope: VoiceCommandEnvelope
    policy: PolicyResult
    capability: VoiceCapability
    provider_result: ProviderResult | None
    receipt: VoiceReceipt
    session_state: SessionState
    pending_confirmation: PendingConfirmation | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _run_mechanical_transitions(session: VoiceSession) -> None:
    """Advance a fresh session through the fixed pre-decision states.

    Transcription and classification have already happened by the time an
    envelope exists (its ``risk_class`` is already populated), so these
    transitions are mechanical bookkeeping, not new work.
    """
    if session.state == SessionState.IDLE:
        session.transition(SessionState.LISTENING, "voice command received")
    if session.state == SessionState.LISTENING:
        session.transition(SessionState.TRANSCRIBING, "transcription available")
    if session.state == SessionState.TRANSCRIBING:
        session.transition(SessionState.CLASSIFYING, "classification available")
    if session.state == SessionState.CLASSIFYING:
        session.transition(SessionState.PLANNING, "policy evaluation")


def _execute_provider(
    envelope: VoiceCommandEnvelope,
    *,
    risk_class: RiskClass,
    capability: VoiceCapability,
    providers: dict[VoiceCapability, VoiceActionProvider],
) -> ProviderResult:
    provider = providers.get(capability) or providers.get(VoiceCapability.GENERIC)
    if provider is None:
        raise ProviderExecutionError(f"no mock provider registered for capability {capability}")
    return provider.execute(envelope, risk_class=risk_class)


def handle_voice_command(
    *,
    envelope: VoiceCommandEnvelope,
    flags: VoiceFeatureFlags,
    session: VoiceSession,
    providers: dict[VoiceCapability, VoiceActionProvider],
    retention: TranscriptRetention | None = None,
) -> OrchestrationOutcome:
    """Drive one classified voice command envelope through policy and (if
    allowed or draft-only) mock execution.

    ``session`` must be a fresh or IDLE/LISTENING/TRANSCRIBING/CLASSIFYING
    ``VoiceSession`` for this command; the orchestrator advances it. The
    caller is responsible for creating a new ``VoiceSession`` per command
    (a voice session's envelope-level ``session_id`` may still group many
    commands together at the persistence layer).
    """
    retention = retention if retention is not None else flags.transcript_retention
    _run_mechanical_transitions(session)

    policy = evaluate(envelope.risk_class, flags)
    capability = resolve_capability(envelope.normalized_intent, envelope.requested_capability)

    if policy.decision == PolicyDecision.REFUSED:
        session.refuse(policy.reason)
        receipt = build_receipt(
            envelope.with_confirmation_state(policy.confirmation_state),
            policy_decision=str(policy.decision),
            result=RESULT_REFUSED,
            retention=retention,
            completed_at=_now_iso(),
        )
        return OrchestrationOutcome(
            envelope=envelope,
            policy=policy,
            capability=capability,
            provider_result=None,
            receipt=receipt,
            session_state=session.state,
        )

    if policy.decision in (PolicyDecision.ALLOWED, PolicyDecision.ALLOWED_DRAFT_ONLY):
        session.transition(SessionState.EXECUTING, "policy allowed")
        try:
            provider_result = _execute_provider(
                envelope, risk_class=envelope.risk_class, capability=capability, providers=providers
            )
        except ProviderExecutionError as exc:
            session.fail(str(exc))
            receipt = build_receipt(
                envelope,
                policy_decision=str(policy.decision),
                result=RESULT_FAILED,
                retention=retention,
                completed_at=_now_iso(),
            )
            return OrchestrationOutcome(
                envelope=envelope,
                policy=policy,
                capability=capability,
                provider_result=None,
                receipt=receipt,
                session_state=session.state,
            )
        session.transition(SessionState.COMPLETED, "mock execution completed")
        result_label = (
            RESULT_DRAFTED
            if policy.decision == PolicyDecision.ALLOWED_DRAFT_ONLY
            else RESULT_ALLOWED
        )
        receipt = build_receipt(
            envelope,
            policy_decision=str(policy.decision),
            result=result_label,
            retention=retention,
            artifacts=list(provider_result.artifacts),
            completed_at=_now_iso(),
        )
        return OrchestrationOutcome(
            envelope=envelope,
            policy=policy,
            capability=capability,
            provider_result=provider_result,
            receipt=receipt,
            session_state=session.state,
        )

    # CONFIRMATION_REQUIRED — no provider is invoked until confirmed.
    session.transition(SessionState.AWAITING_CONFIRMATION, policy.reason)
    pending = PendingConfirmation(
        command_id=envelope.command_id,
        action_description=envelope.normalized_intent,
        target=envelope.target_resource or envelope.normalized_intent,
    )
    envelope_awaiting = envelope.with_confirmation_state(ConfirmationState.REQUIRED)
    receipt = build_receipt(
        envelope_awaiting,
        policy_decision=str(policy.decision),
        result=RESULT_AWAITING_CONFIRMATION,
        retention=retention,
    )
    return OrchestrationOutcome(
        envelope=envelope_awaiting,
        policy=policy,
        capability=capability,
        provider_result=None,
        receipt=receipt,
        session_state=session.state,
        pending_confirmation=pending,
    )


def confirm_voice_command(
    *,
    envelope: VoiceCommandEnvelope,
    session: VoiceSession,
    pending: PendingConfirmation,
    utterance: str,
    current_target: str,
    pending_count: int,
    providers: dict[VoiceCapability, VoiceActionProvider],
    retention: TranscriptRetention = TranscriptRetention.HASH_ONLY,
) -> OrchestrationOutcome:
    """Evaluate a confirmation utterance and, if confirmed, execute the
    previously deferred mock provider action.

    Session must be in ``AWAITING_CONFIRMATION``.
    """
    if session.state != SessionState.AWAITING_CONFIRMATION:
        raise InvalidTransitionError(
            f"cannot confirm a command in state {session.state}; expected AWAITING_CONFIRMATION"
        )

    outcome: ConfirmationOutcome = pending.evaluate(
        utterance, current_target=current_target, pending_count=pending_count
    )
    capability = resolve_capability(envelope.normalized_intent, envelope.requested_capability)

    if not outcome.confirmed:
        session.refuse(outcome.reason)
        envelope_denied = envelope.with_confirmation_state(ConfirmationState.DENIED)
        receipt = build_receipt(
            envelope_denied,
            policy_decision=str(PolicyDecision.REFUSED),
            result=RESULT_REFUSED,
            retention=retention,
            completed_at=_now_iso(),
        )
        return OrchestrationOutcome(
            envelope=envelope_denied,
            policy=PolicyResult(PolicyDecision.REFUSED, ConfirmationState.DENIED, outcome.reason),
            capability=capability,
            provider_result=None,
            receipt=receipt,
            session_state=session.state,
        )

    envelope_confirmed = envelope.with_confirmation_state(ConfirmationState.CONFIRMED)
    session.transition(SessionState.EXECUTING, "confirmed by principal")
    try:
        provider_result = _execute_provider(
            envelope_confirmed,
            risk_class=envelope_confirmed.risk_class,
            capability=capability,
            providers=providers,
        )
    except ProviderExecutionError as exc:
        session.fail(str(exc))
        receipt = build_receipt(
            envelope_confirmed,
            policy_decision=str(PolicyDecision.CONFIRMATION_REQUIRED),
            result=RESULT_FAILED,
            retention=retention,
            completed_at=_now_iso(),
        )
        return OrchestrationOutcome(
            envelope=envelope_confirmed,
            policy=PolicyResult(
                PolicyDecision.CONFIRMATION_REQUIRED, ConfirmationState.CONFIRMED, "confirmed"
            ),
            capability=capability,
            provider_result=None,
            receipt=receipt,
            session_state=session.state,
        )

    session.transition(SessionState.COMPLETED, "confirmed mock execution completed")
    receipt = build_receipt(
        envelope_confirmed,
        policy_decision=str(PolicyDecision.CONFIRMATION_REQUIRED),
        result=RESULT_ALLOWED,
        retention=retention,
        artifacts=list(provider_result.artifacts),
        completed_at=_now_iso(),
    )
    return OrchestrationOutcome(
        envelope=envelope_confirmed,
        policy=PolicyResult(
            PolicyDecision.CONFIRMATION_REQUIRED, ConfirmationState.CONFIRMED, "confirmed"
        ),
        capability=capability,
        provider_result=provider_result,
        receipt=receipt,
        session_state=session.state,
    )


def cancel_voice_command(
    *,
    envelope: VoiceCommandEnvelope,
    session: VoiceSession,
    reason: str = "cancelled by principal",
    retention: TranscriptRetention = TranscriptRetention.HASH_ONLY,
) -> OrchestrationOutcome:
    """Cancel an in-flight (non-terminal) voice command session."""
    session.cancel(reason)
    envelope_cancelled = envelope.with_confirmation_state(ConfirmationState.DENIED)
    receipt = build_receipt(
        envelope_cancelled,
        policy_decision=str(PolicyDecision.REFUSED),
        result=RESULT_CANCELLED,
        retention=retention,
        completed_at=_now_iso(),
    )
    capability = resolve_capability(envelope.normalized_intent, envelope.requested_capability)
    return OrchestrationOutcome(
        envelope=envelope_cancelled,
        policy=PolicyResult(PolicyDecision.REFUSED, ConfirmationState.DENIED, reason),
        capability=capability,
        provider_result=None,
        receipt=receipt,
        session_state=session.state,
    )
