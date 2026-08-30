"""
Hash-chain concurrency control for Observatory events.

Problem: EventService.create() reads the latest hash, computes a new hash,
and inserts the event. Under concurrent access on PostgreSQL, two sessions
can both read the same "latest hash" and produce a fork in the chain.

Solution: Run-scoped locking via observatory_run_heads. Each run has exactly
one row that serves as the authoritative serialization point. Before appending
to the chain, a session must:

1. SELECT ... FOR UPDATE on the run-head row (or INSERT if new run)
2. Read last_sequence and last_event_hash from the locked row
3. Insert the event with sequence = last_sequence + 1
4. Update the run-head row with the new sequence and hash
5. Commit (releases the lock atomically)

This ensures:
- No two sessions can compute hashes based on the same previous_hash
- No forks can appear in the chain
- No gaps can appear (the lock holder always sees the true latest)
- Independent runs serialize independently (no global lock)

On SQLite: FOR UPDATE is a no-op (GIL provides sufficient serialization),
but the row-level design still works correctly.

Genesis rule: The first event in any run has sequence=1, previous_hash=null.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.observatory import ObservatoryRunHead

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def get_or_create_run_head(
    db: AsyncSession,
    run_id: str,
    for_update: bool = True,
) -> ObservatoryRunHead:
    """Get the run-head row, creating it if necessary.

    If for_update is True, the row is locked with SELECT ... FOR UPDATE
    on PostgreSQL (or SQLite where it's a no-op but harmless).

    Returns the run-head row with current last_sequence and last_event_hash.

    Handles concurrent creation: if two sessions try to create the same
    run_id simultaneously, the second session catches IntegrityError,
    rolls back, and re-selects the existing row.
    """
    from sqlalchemy.exc import IntegrityError

    stmt = select(ObservatoryRunHead).where(
        ObservatoryRunHead.run_id == run_id
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await db.execute(stmt)
    head = result.scalar_one_or_none()

    if head is not None:
        return head

    # Try to create the run head. If another session created it first,
    # catch IntegrityError, rollback the flush, and re-select.
    try:
        head = ObservatoryRunHead(
            run_id=run_id,
            last_sequence=0,
            last_event_hash=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            version=1,
        )
        db.add(head)
        await db.flush()

        # Re-select with FOR UPDATE to ensure we hold the lock
        if for_update:
            await db.refresh(head)
        return head
    except IntegrityError:
        # Another session created this run head first.
        # Roll back the failed insert, then re-select the existing row.
        await db.rollback()
        # After rollback, the session is clean. Re-execute the select.
        stmt2 = select(ObservatoryRunHead).where(
            ObservatoryRunHead.run_id == run_id
        )
        if for_update:
            stmt2 = stmt2.with_for_update()
        result2 = await db.execute(stmt2)
        head = result2.scalar_one()
        return head


async def advance_run_head(
    db: AsyncSession,
    run_id: str,
    new_sequence: int,
    new_event_hash: str,
) -> ObservatoryRunHead:
    """Advance the run head to the new sequence and hash.

    Must be called within the same transaction that held the FOR UPDATE lock.
    """
    stmt = select(ObservatoryRunHead).where(
        ObservatoryRunHead.run_id == run_id
    ).with_for_update()
    result = await db.execute(stmt)
    head = result.scalar_one()

    # Sanity check: the new sequence must be exactly one more than the current
    if new_sequence != head.last_sequence + 1:
        raise ValueError(
            f"Sequence gap or duplicate: expected {head.last_sequence + 1}, "
            f"got {new_sequence}"
        )

    head.last_sequence = new_sequence
    head.last_event_hash = new_event_hash
    head.updated_at = datetime.now(UTC)
    head.version += 1
    await db.flush()

    return head


async def verify_no_chain_fork(db: AsyncSession, run_id: str | None = None) -> list[str]:
    """Verify that no fork exists in the hash chain.

    A fork means two events share the same (run_id, previous_hash) combination,
    which would indicate a concurrency control failure.

    Returns a list of previous_hash values that appear more than once.
    An empty list means the chain is clean.
    """
    from portal.models.observatory import ObservatoryEvent
    from sqlalchemy import func, text

    if run_id:
        result = await db.execute(
            select(ObservatoryEvent.previous_hash, func.count())
            .where(
                ObservatoryEvent.run_id == run_id,
                ObservatoryEvent.previous_hash.isnot(None)
            )
            .group_by(ObservatoryEvent.previous_hash)
            .having(func.count() > 1)
        )
    else:
        result = await db.execute(
            select(ObservatoryEvent.previous_hash, func.count())
            .where(ObservatoryEvent.previous_hash.isnot(None))
            .group_by(ObservatoryEvent.previous_hash)
            .having(func.count() > 1)
        )

    fork_points = [row[0] for row in result.all()]
    if fork_points:
        logger.warning(
            "chain.fork_detected fork_points=%d hashes=%s",
            len(fork_points), fork_points[:5],
        )
    return fork_points