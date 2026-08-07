"""SP-VOICE-001 Increment Two — governed voice command service.

Bridges the pure ``voice_concierge.governed`` orchestrator to tenant-scoped
persistence, audit, and realtime status. Every execution this service can
produce is a mock/sandboxed provider outcome (see
``voice_concierge.governed.mock_providers``) — this module never contacts a
real telephony, calendar, messaging, filing, or payment backend, and it
enforces mock-only execution defensively even if a caller supplies a custom
provider registry.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_concierge.governed import (
    ConfirmationState,
    VoiceCommandEnvelope,
    VoiceFeatureFlags,
    VoiceSession,
    classify,
    create_envelope,
)
from voice_concierge.governed.command_envelope import RiskClass, VoiceSource
from voice_concierge.governed.confirmation import PendingConfirmation, target_fingerprint
from voice_concierge.governed.mock_providers import default_mock_registry
from voice_concierge.governed.orchestrator import (
    OrchestrationOutcome,
)
from voice_concierge.governed.orchestrator import (
    cancel_voice_command as _cancel_voice_command,
)
from voice_concierge.governed.orchestrator import (
    confirm_voice_command as _confirm_voice_command,
)
from voice_concierge.governed.orchestrator import (
    handle_voice_command as _handle_voice_command,
)
from voice_concierge.governed.providers import ProviderResult, VoiceActionProvider, VoiceCapability
from voice_concierge.governed.session import SessionState

from ..auth.rbac import CurrentUser
from ..models.voice_command import VoiceCommand, VoiceCommandEvent, VoiceCommandReceipt
from ..services.audit_service import audit
from ..websocket.connection_manager import ws_manager

log = structlog.get_logger(__name__)
_CONFIRMATION_LOCKS_GUARD = asyncio.Lock()
_CONFIRMATION_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}


class VoiceCommandNotFoundError(Exception):
    """Raised when a voice command id cannot be found for the caller's tenant."""


class VoiceCommandStateError(Exception):
    """Raised when an action is attempted against an invalid command state."""

    def __init__(self, message: str, *, command_id: str):
        self.command_id = command_id
        super().__init__(message)


class MockOnlyExecutionError(Exception):
    """Raised defensively if a provider ever returns a non-mock result.

    This should never trigger with the shipped mock providers; it exists to
    fail loudly rather than silently persist a non-sandboxed outcome.
    """


@dataclass(frozen=True)
class VoiceCommandSubmission:
    raw_transcript: str
    source: VoiceSource
    voice_session_id: str | None = None
    requested_capability: str | None = None
    target_resource: str | None = None


@dataclass(frozen=True)
class VoiceCommandResult:
    command: VoiceCommand
    outcome: OrchestrationOutcome
    pending_confirmation: PendingConfirmation | None = None


def _sha256_json(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _compute_event_hash(
    *,
    command_id: str,
    sequence: int,
    event_type: str,
    state: str,
    payload: dict[str, Any],
    previous_hash: str | None,
) -> str:
    return _sha256_json(
        {
            "command_id": command_id,
            "sequence": sequence,
            "event_type": event_type,
            "state": state,
            "payload": payload,
            "previous_hash": previous_hash,
        }
    )


def _compute_receipt_hash(
    *,
    command_id: str,
    result: str,
    audit_log_id: str | None,
    terminal_event_hash: str | None,
) -> str:
    return _sha256_json(
        {
            "command_id": command_id,
            "result": result,
            "audit_log_id": audit_log_id,
            "terminal_event_hash": terminal_event_hash,
        }
    )


def _assert_mock_only(provider_result: ProviderResult | None) -> None:
    if provider_result is not None and not provider_result.mock:
        raise MockOnlyExecutionError(
            "SP-VOICE-001 Increment Two only ever persists mock/sandboxed provider outcomes"
        )


def _providers_for(
    override: dict[VoiceCapability, VoiceActionProvider] | None,
) -> dict[VoiceCapability, VoiceActionProvider]:
    return override if override is not None else default_mock_registry()


async def _confirmation_lock(tenant_id: str, command_id: str) -> asyncio.Lock:
    key = (tenant_id, command_id)
    async with _CONFIRMATION_LOCKS_GUARD:
        lock = _CONFIRMATION_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _CONFIRMATION_LOCKS[key] = lock
        return lock


async def _append_events(
    db: AsyncSession,
    command_row: VoiceCommand,
    session: VoiceSession,
    *,
    start_sequence: int,
    previous_hash: str | None,
) -> list[VoiceCommandEvent]:
    events: list[VoiceCommandEvent] = []
    sequence = start_sequence
    for record in session.history:
        payload = {"from_state": str(record.from_state), "reason": record.reason}
        event_hash = _compute_event_hash(
            command_id=command_row.id,
            sequence=sequence,
            event_type="SESSION_TRANSITION",
            state=str(record.to_state),
            payload=payload,
            previous_hash=previous_hash,
        )
        event = VoiceCommandEvent(
            id=str(uuid.uuid4()),
            command_id=command_row.id,
            sequence=sequence,
            event_type="SESSION_TRANSITION",
            state=str(record.to_state),
            payload=payload,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        db.add(event)
        events.append(event)
        previous_hash = event_hash
        sequence += 1
    await db.flush()
    return events


_TERMINAL_STATES = frozenset({"completed", "refused", "cancelled", "failed"})


async def _finalize(
    db: AsyncSession,
    current_user: CurrentUser,
    command_row: VoiceCommand,
    outcome: OrchestrationOutcome,
    events: list[VoiceCommandEvent],
    *,
    audit_action: str,
) -> None:
    """Apply an orchestration outcome to the persisted projection row,
    write the audit entry, and — if terminal — write the immutable receipt.
    """
    _assert_mock_only(outcome.provider_result)

    command_row.policy_decision = str(outcome.policy.decision)
    command_row.confirmation_state = str(outcome.envelope.confirmation_state)
    command_row.session_state = str(outcome.session_state)
    command_row.result = outcome.receipt.result
    command_row.reason = outcome.policy.reason
    command_row.resolved_capability = str(outcome.capability)
    command_row.updated_at = datetime.now(UTC)
    if outcome.provider_result is not None:
        command_row.provider_capability = str(outcome.provider_result.capability)
        command_row.provider_resource_id = outcome.provider_result.resource_id
        command_row.provider_mock = outcome.provider_result.mock
        command_row.artifacts = list(outcome.provider_result.artifacts)

    is_terminal = str(outcome.session_state).lower() in _TERMINAL_STATES
    if is_terminal:
        command_row.completed_at = datetime.now(UTC)

    audit_entry = await audit(
        db,
        action=audit_action,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="voice_command",
        resource_id=command_row.id,
        resource_name=command_row.command_id,
        status="refused" if outcome.receipt.result == "refused" else "success",
        details={
            "command_id": command_row.command_id,
            "risk_class": str(outcome.envelope.risk_class),
            "policy_decision": str(outcome.policy.decision),
            "result": outcome.receipt.result,
            "capability": str(outcome.capability),
            "mock": outcome.provider_result.mock if outcome.provider_result else None,
        },
    )
    await db.flush()
    command_row.audit_log_id = str(audit_entry.id)

    if is_terminal:
        terminal_hash = events[-1].event_hash if events else None
        receipt_hash = _compute_receipt_hash(
            command_id=command_row.id,
            result=outcome.receipt.result,
            audit_log_id=str(audit_entry.id),
            terminal_event_hash=terminal_hash,
        )
        receipt = VoiceCommandReceipt(
            id=str(uuid.uuid4()),
            command_id=command_row.id,
            receipt_type="TERMINAL",
            receipt_hash=receipt_hash,
            result=outcome.receipt.result,
            audit_log_id=str(audit_entry.id),
            evidence_refs=list(outcome.receipt.artifacts),
        )
        db.add(receipt)

    await db.flush()
    await _publish_status(current_user, command_row)


async def _publish_status(current_user: CurrentUser, command_row: VoiceCommand) -> None:
    event = {
        "type": "voice.command_status",
        "command_id": command_row.command_id,
        "state": command_row.session_state,
        "result": command_row.result,
        "risk_class": command_row.risk_class,
        "policy_decision": command_row.policy_decision,
    }
    try:
        await ws_manager.send_to_user(str(current_user.user_id), event)
    except Exception as exc:  # pragma: no cover - realtime delivery is best-effort
        log.warning(
            "voice.command_realtime_delivery_failed",
            command_id=command_row.command_id,
            user_id=str(current_user.user_id),
            error=str(exc),
        )


async def submit_voice_command(
    db: AsyncSession,
    submission: VoiceCommandSubmission,
    current_user: CurrentUser,
    *,
    flags: VoiceFeatureFlags | None = None,
    providers: dict[VoiceCapability, VoiceActionProvider] | None = None,
) -> VoiceCommandResult:
    """Classify, evaluate policy for, and (if allowed) mock-execute a new
    voice command. Persists the full lifecycle as an append-only event chain
    plus a mutable projection row, and a terminal receipt when applicable.
    """
    flags = flags if flags is not None else VoiceFeatureFlags.from_env()
    providers = _providers_for(providers)

    normalized_intent = submission.raw_transcript
    risk_class = classify(submission.raw_transcript)
    envelope: VoiceCommandEnvelope = create_envelope(
        session_id=submission.voice_session_id or f"vsess-{uuid.uuid4().hex[:12]}",
        principal_id=current_user.user_id,
        source=submission.source,
        raw_transcript=submission.raw_transcript,
        normalized_intent=normalized_intent,
        risk_class=risk_class,
        confirmation_state=ConfirmationState.NOT_REQUIRED,
        requested_capability=submission.requested_capability,
        target_resource=submission.target_resource,
    )

    session = VoiceSession(envelope.session_id, current_user.user_id)
    outcome = _handle_voice_command(
        envelope=envelope, flags=flags, session=session, providers=providers
    )

    command_row = VoiceCommand(
        id=str(uuid.uuid4()),
        tenant_id=str(current_user.tenant_id),
        principal_id=str(current_user.user_id),
        command_id=envelope.command_id,
        voice_session_id=envelope.session_id,
        correlation_id=envelope.correlation_id,
        source=str(envelope.source),
        raw_transcript_hash=outcome.receipt.raw_transcript_hash,
        raw_transcript=outcome.receipt.raw_transcript,
        normalized_intent=envelope.normalized_intent,
        requested_capability=envelope.requested_capability,
        resolved_capability=str(outcome.capability),
        target_resource=envelope.target_resource,
        risk_class=str(envelope.risk_class),
        policy_decision=str(outcome.policy.decision),
        confirmation_state=str(outcome.envelope.confirmation_state),
        session_state=str(outcome.session_state),
        result=outcome.receipt.result,
        reason=outcome.policy.reason,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    if outcome.pending_confirmation is not None:
        restated_target = envelope.target_resource or envelope.normalized_intent
        command_row.confirmation_target_restated_at = datetime.now(UTC)
        command_row.confirmation_target_fingerprint = target_fingerprint(restated_target)

    db.add(command_row)
    await db.flush()

    events = await _append_events(db, command_row, session, start_sequence=1, previous_hash=None)
    await _finalize(
        db, current_user, command_row, outcome, events, audit_action="voice_command_submitted"
    )

    return VoiceCommandResult(
        command=command_row,
        outcome=outcome,
        pending_confirmation=outcome.pending_confirmation,
    )


async def _load_command(
    db: AsyncSession,
    current_user: CurrentUser,
    command_id: str,
    *,
    for_update: bool = False,
) -> VoiceCommand:
    stmt = select(VoiceCommand).where(
        VoiceCommand.tenant_id == str(current_user.tenant_id),
        VoiceCommand.command_id == command_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    command_row = result.scalar_one_or_none()
    if command_row is None:
        raise VoiceCommandNotFoundError(command_id)
    return command_row


def _rehydrate_envelope(
    command_row: VoiceCommand, *, confirmation_state: ConfirmationState
) -> VoiceCommandEnvelope:
    return create_envelope(
        session_id=command_row.voice_session_id,
        principal_id=command_row.principal_id,
        source=VoiceSource(command_row.source),
        raw_transcript=command_row.raw_transcript or "[hash-only retention]",
        normalized_intent=command_row.normalized_intent,
        risk_class=RiskClass(command_row.risk_class),
        confirmation_state=confirmation_state,
        requested_capability=command_row.requested_capability,
        target_resource=command_row.target_resource,
        correlation_id=command_row.correlation_id,
        command_id=command_row.command_id,
    )


def _rehydrate_session(command_row: VoiceCommand, current_user: CurrentUser) -> VoiceSession:
    """Reconstruct a transient session driver positioned at the command's
    last persisted state. The durable audit trail lives in
    ``voice_command_events``, not in this in-memory object's history.
    """
    session = VoiceSession(command_row.voice_session_id, str(current_user.user_id))
    session.state = SessionState(command_row.session_state)
    return session


async def _last_event_hash(db: AsyncSession, command_row: VoiceCommand) -> tuple[str | None, int]:
    result = await db.execute(
        select(VoiceCommandEvent.event_hash, VoiceCommandEvent.sequence)
        .where(VoiceCommandEvent.command_id == command_row.id)
        .order_by(VoiceCommandEvent.sequence.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None, 1
    return row[0], row[1] + 1


async def confirm_voice_command(
    db: AsyncSession,
    command_id: str,
    utterance: str,
    current_user: CurrentUser,
    *,
    current_target: str | None = None,
    providers: dict[VoiceCapability, VoiceActionProvider] | None = None,
) -> VoiceCommandResult:
    """Evaluate a confirmation utterance for a pending voice command and, if
    confirmed, mock-execute it.
    """
    providers = _providers_for(providers)
    lock = await _confirmation_lock(str(current_user.tenant_id), command_id)
    async with lock:
        command_row = await _load_command(db, current_user, command_id, for_update=True)
        if command_row.session_state != str(SessionState.AWAITING_CONFIRMATION):
            raise VoiceCommandStateError(
                f"command {command_id} is not awaiting confirmation (state={command_row.session_state})",
                command_id=command_id,
            )

        pending_count_result = await db.execute(
            select(func.count(VoiceCommand.id)).where(
                VoiceCommand.tenant_id == str(current_user.tenant_id),
                VoiceCommand.voice_session_id == command_row.voice_session_id,
                VoiceCommand.session_state == str(SessionState.AWAITING_CONFIRMATION),
            )
        )
        pending_count = pending_count_result.scalar_one()

        pending = PendingConfirmation(
            command_id=command_row.command_id,
            action_description=command_row.normalized_intent,
            target=command_row.target_resource or command_row.normalized_intent,
            created_at=command_row.created_at.replace(tzinfo=UTC)
            if command_row.created_at.tzinfo is None
            else command_row.created_at,
        )
        pending.apply_restated_evidence(
            restated_at=command_row.confirmation_target_restated_at.replace(tzinfo=UTC)
            if command_row.confirmation_target_restated_at
            and command_row.confirmation_target_restated_at.tzinfo is None
            else command_row.confirmation_target_restated_at,
            target_fingerprint=command_row.confirmation_target_fingerprint,
            command_id=command_row.command_id,
        )

        effective_target = (
            current_target or command_row.target_resource or command_row.normalized_intent
        )
        confirmation_check = pending.evaluate(
            utterance,
            current_target=effective_target,
            pending_count=pending_count,
        )

        envelope = _rehydrate_envelope(command_row, confirmation_state=ConfirmationState.REQUIRED)
        session = _rehydrate_session(command_row, current_user)

        if confirmation_check.confirmed:
            command_row.session_state = str(SessionState.EXECUTING)
            command_row.confirmation_state = str(ConfirmationState.CONFIRMED)
            command_row.result = "execution_claimed"
            command_row.updated_at = datetime.now(UTC)
            await db.flush()

        outcome = _confirm_voice_command(
            envelope=envelope,
            session=session,
            pending=pending,
            utterance=utterance,
            current_target=effective_target,
            pending_count=pending_count,
            providers=providers,
        )

        previous_hash, start_sequence = await _last_event_hash(db, command_row)
        events = await _append_events(
            db, command_row, session, start_sequence=start_sequence, previous_hash=previous_hash
        )
        await _finalize(
            db,
            current_user,
            command_row,
            outcome,
            events,
            audit_action="voice_command_confirmation",
        )

        return VoiceCommandResult(command=command_row, outcome=outcome)


async def cancel_voice_command(
    db: AsyncSession,
    command_id: str,
    current_user: CurrentUser,
    *,
    reason: str = "cancelled by principal",
) -> VoiceCommandResult:
    """Cancel an in-flight (non-terminal) voice command."""
    command_row = await _load_command(db, current_user, command_id)
    if command_row.session_state in _TERMINAL_STATES:
        raise VoiceCommandStateError(
            f"command {command_id} is already terminal (state={command_row.session_state})",
            command_id=command_id,
        )

    envelope = _rehydrate_envelope(
        command_row, confirmation_state=ConfirmationState(command_row.confirmation_state)
    )
    session = _rehydrate_session(command_row, current_user)

    outcome = _cancel_voice_command(envelope=envelope, session=session, reason=reason)

    previous_hash, start_sequence = await _last_event_hash(db, command_row)
    events = await _append_events(
        db, command_row, session, start_sequence=start_sequence, previous_hash=previous_hash
    )
    await _finalize(
        db, current_user, command_row, outcome, events, audit_action="voice_command_cancelled"
    )

    return VoiceCommandResult(command=command_row, outcome=outcome)


async def get_voice_command(
    db: AsyncSession, command_id: str, current_user: CurrentUser
) -> VoiceCommand:
    return await _load_command(db, current_user, command_id)


async def list_voice_commands(
    db: AsyncSession,
    current_user: CurrentUser,
    *,
    voice_session_id: str | None = None,
    limit: int = 50,
) -> list[VoiceCommand]:
    stmt = select(VoiceCommand).where(VoiceCommand.tenant_id == str(current_user.tenant_id))
    if voice_session_id:
        stmt = stmt.where(VoiceCommand.voice_session_id == voice_session_id)
    stmt = stmt.order_by(VoiceCommand.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
