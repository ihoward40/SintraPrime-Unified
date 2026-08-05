"""Read-only projection service for Mission Control Foundation.

Provides tenant-scoped query functions for:
1. Intent ledger (commands) — list and detail views with events and receipts.
2. Execution-state (run-controls) — list and detail views with transition events.
3. Correlation/causation chains — assembled from command events, run-control
   events, and receipts.

All functions are read-only. They accept an AsyncSession and return projection
data. No mutations are performed. Tenant isolation is enforced by filtering
on tenant_id in every query — no cross-tenant access is possible.

Review corrections applied:
- Cross-tenant causation-chain query now joins MissionControlRunControl and
  filters on tenant_id so a run-control event referencing another tenant's
  command cannot leak into the chain.
- Detail projections redact payloads, metadata, evidence refs, and sensitive
  run-control fields (last_error, confirmation_ref, recovery_ref).
- List responses return lightweight summaries (CommandSummary / RunControlSummary)
  with event/receipt counts instead of full payloads, events, and receipts.
- Freshness metadata (FreshnessMeta) is computed on every response.
- Causation graph safety: duplicate hash detection, missing-parent detection,
  truncation above MAX_CAUSATION_LINKS, and deterministic ordering.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from ..models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
)
from ..schemas.mission_control_projection import (
    EXPOSED_PAYLOAD_FIELDS,
    MAX_CAUSATION_LINKS,
    CausationChain,
    CausationLink,
    CommandEventProjection,
    CommandListResponse,
    CommandProjection,
    CommandReceiptProjection,
    CommandSummary,
    RunControlEventProjection,
    RunControlListResponse,
    RunControlProjection,
    RunControlSummary,
    classify_freshness,
    redact_dict,
    redact_error,
    redact_evidence_refs,
    redact_ref,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _min_dt() -> datetime:
    """Return a timezone-aware minimum datetime for stable sort keys."""
    return datetime.min.replace(tzinfo=UTC)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """Normalize a timezone-naive datetime to UTC, preserving None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _latest_source_updated(*candidates: datetime | None) -> datetime | None:
    """Return the latest non-None candidate, or None if all are None."""
    latest: datetime | None = None
    for candidate in candidates:
        if candidate is None:
            continue
        aware = _ensure_aware(candidate)
        if latest is None or aware > latest:
            latest = aware
    return latest


# ── Intent projection ─────────────────────────────────────────────────────────


async def list_commands(
    db: AsyncSession,
    *,
    tenant_id: str,
    state: str | None = None,
    command_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> CommandListResponse:
    """List commands for a tenant, filtered by optional state and command_type.

    Returns a paginated read-only projection of summaries. Events and receipts
    are not loaded; only ``event_count`` and ``receipt_count`` are surfaced.
    """
    query = (
        select(MissionControlCommand)
        .where(MissionControlCommand.tenant_id == tenant_id)
        .order_by(MissionControlCommand.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if state is not None:
        query = query.where(MissionControlCommand.state == state)
    if command_type is not None:
        query = query.where(MissionControlCommand.command_type == command_type)

    result = await db.execute(query)
    commands = list(result.scalars().all())

    count_query = (
        select(func.count())
        .select_from(MissionControlCommand)
        .where(MissionControlCommand.tenant_id == tenant_id)
    )
    if state is not None:
        count_query = count_query.where(MissionControlCommand.state == state)
    if command_type is not None:
        count_query = count_query.where(MissionControlCommand.command_type == command_type)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    generated_at = datetime.now(UTC)
    source_updated_at = _latest_source_updated(
        *(cmd.updated_at if hasattr(cmd, "updated_at") else cmd.created_at for cmd in commands),
        *(cmd.completed_at for cmd in commands),
        *(cmd.created_at for cmd in commands),
    )
    freshness = classify_freshness(generated_at, source_updated_at)

    return CommandListResponse(
        items=[_to_command_summary(cmd) for cmd in commands],
        total=total,
        limit=limit,
        offset=offset,
        freshness=freshness,
    )


async def get_command(
    db: AsyncSession,
    *,
    tenant_id: str,
    command_id: str,
) -> CommandProjection | None:
    """Return a single command projection by ID, scoped to tenant.

    Returns None if the command does not exist or belongs to a different
    tenant. Payloads, metadata, and evidence refs are redacted.
    """
    query = select(MissionControlCommand).where(
        MissionControlCommand.id == command_id,
        MissionControlCommand.tenant_id == tenant_id,
    )
    result = await db.execute(query)
    cmd = result.scalars().first()
    if cmd is None:
        return None
    return _to_command_projection(cmd)


def _to_command_summary(cmd: MissionControlCommand) -> CommandSummary:
    """Convert a MissionControlCommand ORM model to a lightweight summary."""
    events = cmd.events or []
    receipts = cmd.receipts or []
    return CommandSummary(
        id=cmd.id,
        tenant_id=cmd.tenant_id,
        requested_by=cmd.requested_by,
        command_type=cmd.command_type,
        target_type=cmd.target_type,
        target_id=cmd.target_id,
        idempotency_key=cmd.idempotency_key,
        request_hash=cmd.request_hash,
        state=cmd.state,
        reason_code=cmd.reason_code,
        reason=cmd.reason,
        audit_log_id=cmd.audit_log_id,
        created_at=cmd.created_at,
        completed_at=cmd.completed_at,
        event_count=len(events),
        receipt_count=len(receipts),
    )


def _to_command_projection(cmd: MissionControlCommand) -> CommandProjection:
    """Convert a MissionControlCommand ORM model to a redacted detail projection."""
    events = sorted((cmd.events or []), key=lambda e: e.sequence)
    receipts = list(cmd.receipts or [])
    generated_at = datetime.now(UTC)
    source_updated_at = _latest_source_updated(
        cmd.created_at,
        cmd.completed_at,
        *(e.created_at for e in events),
        *(r.created_at for r in receipts),
    )
    return CommandProjection(
        id=cmd.id,
        tenant_id=cmd.tenant_id,
        requested_by=cmd.requested_by,
        command_type=cmd.command_type,
        target_type=cmd.target_type,
        target_id=cmd.target_id,
        idempotency_key=cmd.idempotency_key,
        request_hash=cmd.request_hash,
        state=cmd.state,
        reason_code=cmd.reason_code,
        reason=cmd.reason,
        payload=redact_dict(cmd.payload or {}, EXPOSED_PAYLOAD_FIELDS),
        metadata=redact_dict(cmd.metadata_json or {}, EXPOSED_PAYLOAD_FIELDS),
        audit_log_id=cmd.audit_log_id,
        created_at=cmd.created_at,
        completed_at=cmd.completed_at,
        events=[
            CommandEventProjection(
                id=e.id,
                sequence=e.sequence,
                event_type=e.event_type,
                state=e.state,
                payload=redact_dict(e.payload or {}, EXPOSED_PAYLOAD_FIELDS),
                previous_hash=e.previous_hash,
                event_hash=e.event_hash,
                created_at=e.created_at,
            )
            for e in events
        ],
        receipts=[
            CommandReceiptProjection(
                id=r.id,
                receipt_type=r.receipt_type,
                receipt_hash=r.receipt_hash,
                audit_log_id=r.audit_log_id,
                evidence_refs=redact_evidence_refs(r.evidence_refs or []),
                created_at=r.created_at,
            )
            for r in receipts
        ],
        freshness=classify_freshness(generated_at, source_updated_at),
    )


# ── Execution-state projection ────────────────────────────────────────────────


async def list_run_controls(
    db: AsyncSession,
    *,
    tenant_id: str,
    state: str | None = None,
    workflow_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> RunControlListResponse:
    """List run-control summaries for a tenant.

    Returns a paginated read-only projection. Events and ``last_error`` are
    not surfaced; only ``event_count`` is included.
    """
    query = (
        select(MissionControlRunControl)
        .where(MissionControlRunControl.tenant_id == tenant_id)
        .order_by(MissionControlRunControl.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if state is not None:
        query = query.where(MissionControlRunControl.state == state)
    if workflow_id is not None:
        query = query.where(MissionControlRunControl.workflow_id == workflow_id)

    result = await db.execute(query)
    controls = list(result.scalars().all())

    count_query = (
        select(func.count())
        .select_from(MissionControlRunControl)
        .where(MissionControlRunControl.tenant_id == tenant_id)
    )
    if state is not None:
        count_query = count_query.where(MissionControlRunControl.state == state)
    if workflow_id is not None:
        count_query = count_query.where(MissionControlRunControl.workflow_id == workflow_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    generated_at = datetime.now(UTC)
    source_updated_at = _latest_source_updated(
        *(rc.updated_at for rc in controls),
        *(rc.created_at for rc in controls),
    )
    freshness = classify_freshness(generated_at, source_updated_at)

    return RunControlListResponse(
        items=[_to_run_control_summary(rc) for rc in controls],
        total=total,
        limit=limit,
        offset=offset,
        freshness=freshness,
    )


async def get_run_control(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_control_id: str,
) -> RunControlProjection | None:
    """Return a single run-control projection by ID, scoped to tenant.

    Sensitive fields (last_error, confirmation_ref, recovery_ref) are redacted.
    Event payloads are redacted via redact_dict.
    """
    query = select(MissionControlRunControl).where(
        MissionControlRunControl.id == run_control_id,
        MissionControlRunControl.tenant_id == tenant_id,
    )
    result = await db.execute(query)
    rc = result.scalars().first()
    if rc is None:
        return None
    return _to_run_control_projection(rc)


def _to_run_control_summary(rc: MissionControlRunControl) -> RunControlSummary:
    """Convert a MissionControlRunControl ORM model to a lightweight summary."""
    events = rc.events or []
    return RunControlSummary(
        id=rc.id,
        tenant_id=rc.tenant_id,
        workflow_id=rc.workflow_id,
        command_id=rc.command_id,
        state=rc.state,
        workflow_status_snapshot=rc.workflow_status_snapshot,
        workflow_status_observed_at=rc.workflow_status_observed_at,
        workflow_source=rc.workflow_source,
        workflow_version_snapshot=rc.workflow_version_snapshot,
        state_version=rc.state_version,
        projection_schema_version=rc.projection_schema_version,
        pause_reason=rc.pause_reason,
        requested_by=rc.requested_by,
        requested_at=rc.requested_at,
        acknowledged_by=rc.acknowledged_by,
        acknowledged_at=rc.acknowledged_at,
        paused_at=rc.paused_at,
        failed_at=rc.failed_at,
        timed_out_at=rc.timed_out_at,
        superseded_at=rc.superseded_at,
        incident_id=rc.incident_id,
        terminal_reason_code=rc.terminal_reason_code,
        created_at=rc.created_at,
        updated_at=rc.updated_at,
        event_count=len(events),
    )


def _to_run_control_projection(rc: MissionControlRunControl) -> RunControlProjection:
    """Convert a MissionControlRunControl ORM model to a redacted detail projection."""
    events = sorted((rc.events or []), key=lambda e: e.sequence)
    generated_at = datetime.now(UTC)
    source_updated_at = _latest_source_updated(
        rc.created_at,
        rc.updated_at,
        *(e.created_at for e in events),
    )
    return RunControlProjection(
        id=rc.id,
        tenant_id=rc.tenant_id,
        workflow_id=rc.workflow_id,
        command_id=rc.command_id,
        state=rc.state,
        workflow_status_snapshot=rc.workflow_status_snapshot,
        workflow_status_observed_at=rc.workflow_status_observed_at,
        workflow_source=rc.workflow_source,
        workflow_version_snapshot=rc.workflow_version_snapshot,
        state_version=rc.state_version,
        projection_schema_version=rc.projection_schema_version,
        pause_reason=rc.pause_reason,
        requested_by=rc.requested_by,
        requested_at=rc.requested_at,
        confirmation_ref=redact_ref(rc.confirmation_ref),
        acknowledged_by=rc.acknowledged_by,
        acknowledged_at=rc.acknowledged_at,
        paused_at=rc.paused_at,
        failed_at=rc.failed_at,
        timed_out_at=rc.timed_out_at,
        superseded_at=rc.superseded_at,
        incident_id=rc.incident_id,
        recovery_ref=redact_ref(rc.recovery_ref),
        terminal_reason_code=rc.terminal_reason_code,
        last_error=redact_error(rc.last_error),
        created_at=rc.created_at,
        updated_at=rc.updated_at,
        events=[
            RunControlEventProjection(
                id=e.id,
                sequence=e.sequence,
                event_type=e.event_type,
                previous_state=e.previous_state,
                new_state=e.new_state,
                previous_version=e.previous_version,
                new_version=e.new_version,
                principal_id=e.principal_id,
                command_id=e.command_id,
                reason=e.reason,
                payload=redact_dict(e.payload or {}, EXPOSED_PAYLOAD_FIELDS),
                workflow_status_observed_at=e.workflow_status_observed_at,
                previous_event_hash=e.previous_event_hash,
                event_hash=e.event_hash,
                event_schema_version=e.event_schema_version,
                created_at=e.created_at,
            )
            for e in events
        ],
        freshness=classify_freshness(generated_at, source_updated_at),
    )


# ── Correlation / causation chain ─────────────────────────────────────────────


async def get_causation_chain(
    db: AsyncSession,
    *,
    tenant_id: str,
    command_id: str,
) -> CausationChain | None:
    """Assemble the causation chain for a command.

    The chain is ordered by (created_at, sequence, source_type, source_id) for
    a deterministic ordering. It links command events, receipts, and any
    run-control events that reference the command.

    Safety:
    - Run-control events are filtered by tenant_id via a join to
      MissionControlRunControl, preventing cross-tenant child-node leakage.
    - Duplicate hashes are detected and reported as warnings.
    - Missing parents (previous_hash not in the set of node hashes) are
      detected and reported as warnings.
    - The chain is truncated at MAX_CAUSATION_LINKS with ``truncated`` and
      ``total_links`` metadata.

    Returns None if the command does not exist or belongs to a different
    tenant.
    """
    cmd = await get_command(db, tenant_id=tenant_id, command_id=command_id)
    if cmd is None:
        return None

    links: list[CausationLink] = []

    # Command events form the primary chain
    for e in cmd.events:
        links.append(
            CausationLink(
                source_type="command_event",
                source_id=e.id,
                sequence=e.sequence,
                event_type=e.event_type,
                state=e.state,
                hash=e.event_hash,
                previous_hash=e.previous_hash,
                created_at=e.created_at,
                command_id=cmd.id,
            )
        )

    # Receipts extend the chain
    for r in cmd.receipts:
        links.append(
            CausationLink(
                source_type="receipt",
                source_id=r.id,
                sequence=0,
                event_type=r.receipt_type,
                state=cmd.state,
                hash=r.receipt_hash,
                previous_hash=None,
                created_at=r.created_at,
                command_id=cmd.id,
            )
        )

    # Run-control events linked to this command extend the chain further.
    # Join MissionControlRunControl and filter on tenant_id so a run-control
    # event referencing this command but belonging to another tenant cannot
    # leak into the chain.
    rc_query = (
        select(MissionControlRunControlEvent)
        .join(
            MissionControlRunControl,
            MissionControlRunControlEvent.run_control_id == MissionControlRunControl.id,
        )
        .where(
            MissionControlRunControlEvent.command_id == command_id,
            MissionControlRunControl.tenant_id == tenant_id,
        )
    )
    rc_result = await db.execute(rc_query)
    rc_events = list(rc_result.scalars().all())
    for e in rc_events:
        links.append(
            CausationLink(
                source_type="run_control_event",
                source_id=e.id,
                sequence=e.sequence,
                event_type=e.event_type,
                state=e.new_state,
                hash=e.event_hash,
                previous_hash=e.previous_event_hash,
                created_at=e.created_at,
                command_id=e.command_id,
                run_control_id=e.run_control_id,
            )
        )

    # Deterministic sort: (created_at, sequence, source_type, source_id)
    links.sort(
        key=lambda link: (
            link.created_at or _min_dt(),
            link.sequence,
            link.source_type,
            link.source_id,
        )
    )

    # Safety: duplicate hash detection
    warnings: list[str] = []
    seen_hashes: set[str] = set()
    duplicate_hashes: set[str] = set()
    for link in links:
        if link.hash in seen_hashes:
            duplicate_hashes.add(link.hash)
        else:
            seen_hashes.add(link.hash)
    if duplicate_hashes:
        warnings.append(f"Duplicate hashes detected: {sorted(duplicate_hashes)}")

    # Safety: missing parent detection
    node_hashes = {link.hash for link in links}
    missing_parents: list[str] = []
    for link in links:
        if link.previous_hash is not None and link.previous_hash not in node_hashes:
            missing_parents.append(link.previous_hash)
    if missing_parents:
        warnings.append(f"Missing parent hashes: {sorted(set(missing_parents))}")

    # Safety: truncation
    total_links = len(links)
    truncated = total_links > MAX_CAUSATION_LINKS
    if truncated:
        links = links[:MAX_CAUSATION_LINKS]
        warnings.append(
            f"Causation chain truncated at MAX_CAUSATION_LINKS={MAX_CAUSATION_LINKS} "
            f"(total={total_links})"
        )

    generated_at = datetime.now(UTC)
    source_updated_at = _latest_source_updated(
        cmd.created_at,
        cmd.completed_at,
        *(link.created_at for link in links),
    )
    freshness = classify_freshness(generated_at, source_updated_at)

    return CausationChain(
        command_id=cmd.id,
        tenant_id=cmd.tenant_id,
        command_type=cmd.command_type,
        command_state=cmd.state,
        links=links,
        truncated=truncated,
        total_links=total_links,
        warnings=warnings,
        freshness=freshness,
    )
