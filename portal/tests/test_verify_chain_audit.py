"""
Gate 4.6 — verify_chain Caller Audit

Tests for every caller of verify_chain and chain-head lookup methods,
documenting:
- file and function
- full-chain or scoped-chain verification
- start/end boundaries
- expected chain head
- error behavior
- fail-open or fail-closed behavior
- whether result affects authorization or mutation
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.models.observatory import ObservatoryEvent, ObservatoryRunHead, Base
from portal.services.observatory_service import EventService
from portal.services.chain_lock import get_or_create_run_head, advance_run_head


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(factory):
    async with factory() as session:
        yield session


class TestVerifyChainCallerAudit:
    """
    CALLER AUDIT SUMMARY (production code):

    1. portal/routers/observatory.py::verify_chain (line 244)
       - Type: READ-ONLY endpoint
       - Scope: Global (all runs, no run_id filter)
       - Boundaries: Start = first event per run, End = last event per run
       - Error behavior: Returns {valid: False, reason: str} — no exception
       - Fail behavior: FAIL-OPEN (returns result, no mutation gated)
       - Mutation impact: NONE — read-only diagnostic endpoint

    2. portal/services/observatory_service.py::EventService.create (line 120)
       - Uses: get_or_create_run_head, advance_run_head (NOT verify_chain)
       - Type: MUTATION — creates events
       - Chain-head lookup: get_or_create_run_head with FOR UPDATE lock
       - Error behavior: IntegrityError on concurrent creation → rollback + re-select
       - Fail behavior: FAIL-CLOSED (exception on integrity violation)
       - Mutation impact: HIGH — event creation depends on correct chain head
       - AUDIT NOTE: verify_chain is NOT called before mutation. This is correct
         for performance (verification after batch, not before each event), but
         means a corrupted chain head would produce corrupted events until
         verify_chain is next called.

    3. portal/services/chain_lock.py::get_or_create_run_head (line 48)
       - Type: Chain-head lookup used during mutation
       - Boundaries: Returns the single run-head row for a given run_id
       - Expected chain head: last_event_hash from the run-head row
       - Error behavior: IntegrityError → rollback + re-select
       - Fail behavior: FAIL-CLOSED (raises if row cannot be found after rollback)
       - Mutation impact: HIGH — incorrect chain head corrupts all subsequent events

    4. portal/services/chain_lock.py::advance_run_head (line 111)
       - Type: Chain-head update after event creation
       - Boundaries: Updates the run-head row within the same transaction
       - Error behavior: Sanity check fails (sequence mismatch) → raises
       - Fail behavior: FAIL-CLOSED (exception prevents commit)
       - Mutation impact: HIGH — must be called within same transaction as event insert

    KEY FINDING: No production code calls verify_chain before performing a mutation.
    The only production caller is the read-only /events/chain/verify endpoint.
    This means verify_chain is a POST-HOC verification tool, not a pre-mutation guard.

    RECOMMENDATION: For mutation-sensitive operations (approvals, kill-switch activation,
    evidence package sealing), add a pre-mutation verify_chain check that FAILS CLOSED.
    """

    @pytest.mark.asyncio
    async def test_verify_chain_empty_db_returns_valid(self, db):
        """verify_chain on empty database returns valid=True."""
        result = await EventService.verify_chain(db)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_verify_chain_single_run_full_chain(self, db):
        """Full-chain verification for a single run with valid chain."""
        event1 = await EventService.create(
            db, event_type="AUDIT", payload={"step": 1}, run_id="audit-run-1",
        )
        await db.commit()
        event2 = await EventService.create(
            db, event_type="AUDIT", payload={"step": 2}, run_id="audit-run-1",
        )
        await db.commit()

        result = await EventService.verify_chain(db, run_id="audit-run-1")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_verify_chain_scoped_to_run(self, db):
        """Scoped verification only checks the specified run."""
        await EventService.create(
            db, event_type="AUDIT", payload={"run": "A"}, run_id="audit-run-A",
        )
        await db.commit()
        await EventService.create(
            db, event_type="AUDIT", payload={"run": "B"}, run_id="audit-run-B",
        )
        await db.commit()

        result_a = await EventService.verify_chain(db, run_id="audit-run-A")
        result_b = await EventService.verify_chain(db, run_id="audit-run-B")
        assert result_a.valid is True
        assert result_b.valid is True

    @pytest.mark.asyncio
    async def test_verify_chain_detects_tampered_hash(self, factory):
        """verify_chain detects a tampered event hash — FAIL-CLOSED.

        Uses file-based SQLite to allow direct table updates.
        """
        import tempfile, os
        db_path = os.path.join(tempfile.gettempdir(), "tamper_test.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            event = await EventService.create(
                db, event_type="AUDIT", payload={"step": 1}, run_id="tamper-run",
            )
            await db.commit()

            # Tamper with the event hash directly in the database
            await db.execute(
                ObservatoryEvent.__table__.update()
                .where(ObservatoryEvent.id == event.id)
                .values(event_hash="tampered_hash_value")
            )
            await db.commit()

        # Verify with a fresh session to avoid identity map caching
        async with factory() as db:
            result = await EventService.verify_chain(db, run_id="tamper-run")
            assert result.valid is False, "Tampered hash should be detected"

        await engine.dispose()
        os.remove(db_path)

    @pytest.mark.asyncio
    async def test_verify_chain_detects_broken_link(self, factory):
        """verify_chain detects a broken chain link — FAIL-CLOSED."""
        import tempfile, os
        db_path = os.path.join(tempfile.gettempdir(), "broken_link_test.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            event1 = await EventService.create(
                db, event_type="AUDIT", payload={"step": 1}, run_id="link-run",
            )
            await db.commit()
            event2 = await EventService.create(
                db, event_type="AUDIT", payload={"step": 2}, run_id="link-run",
            )
            await db.commit()

            # Break the chain link
            await db.execute(
                ObservatoryEvent.__table__.update()
                .where(ObservatoryEvent.id == event2.id)
                .values(previous_hash="broken_link_hash")
            )
            await db.commit()

        async with factory() as db:
            result = await EventService.verify_chain(db, run_id="link-run")
            assert result.valid is False

        await engine.dispose()
        os.remove(db_path)

    @pytest.mark.asyncio
    async def test_verify_chain_detects_sequence_gap(self, factory):
        """verify_chain detects a sequence gap — FAIL-CLOSED."""
        import tempfile, os
        db_path = os.path.join(tempfile.gettempdir(), "gap_test.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            event1 = await EventService.create(
                db, event_type="AUDIT", payload={"step": 1}, run_id="gap-run",
            )
            await db.commit()

            # Insert second event
            event2 = await EventService.create(
                db, event_type="AUDIT", payload={"step": 3}, run_id="gap-run",
            )
            await db.commit()

            # Tamper sequence number to create a gap
            await db.execute(
                ObservatoryEvent.__table__.update()
                .where(ObservatoryEvent.id == event2.id)
                .values(sequence=5)
            )
            await db.commit()

        async with factory() as db:
            result = await EventService.verify_chain(db, run_id="gap-run")
            assert result.valid is False

        await engine.dispose()
        os.remove(db_path)

    @pytest.mark.asyncio
    async def test_get_or_create_run_head_creates_genesis(self, db):
        """get_or_create_run_head creates a new run-head for a new run_id."""
        head = await get_or_create_run_head(db, "head-test-run", for_update=False)
        await db.flush()
        assert head.run_id == "head-test-run"
        assert head.last_sequence == 0
        assert head.last_event_hash is None

    @pytest.mark.asyncio
    async def test_get_or_create_run_head_returns_existing(self, db):
        """get_or_create_run_head returns existing row for an existing run_id."""
        head1 = await get_or_create_run_head(db, "existing-run", for_update=False)
        await db.flush()
        head2 = await get_or_create_run_head(db, "existing-run", for_update=False)
        assert head1.run_id == head2.run_id

    @pytest.mark.asyncio
    async def test_advance_run_head_updates_sequence_and_hash(self, db):
        """advance_run_head updates last_sequence and last_event_hash."""
        head = await get_or_create_run_head(db, "advance-run", for_update=False)
        await db.flush()
        updated = await advance_run_head(db, "advance-run", 1, "hash_abc123")
        assert updated.last_sequence == 1
        assert updated.last_event_hash == "hash_abc123"

    @pytest.mark.asyncio
    async def test_advance_run_head_sanity_check_rejects_wrong_sequence(self, db):
        """advance_run_head rejects a sequence that doesn't follow the current head."""
        head = await get_or_create_run_head(db, "sanity-run", for_update=False)
        await db.flush()
        # head.last_sequence == 0, so next should be 1
        # Try to skip to sequence 3 — should fail
        with pytest.raises(ValueError):
            await advance_run_head(db, "sanity-run", 3, "hash_wrong")

    @pytest.mark.asyncio
    async def test_no_production_mutation_calls_verify_chain_first(self):
        """
        AUDIT ASSERTION: No production code calls verify_chain before mutation.

        This is confirmed by the caller search:
        - portal/routers/observatory.py::verify_chain — read-only endpoint
        - All other callers are in test files

        This test exists as documentation, not runtime verification.
        It asserts that the audit finding is recorded: verify_chain is
        post-hoc only, and mutation-sensitive operations (approvals, kill-switch,
        evidence sealing) do NOT verify chain integrity before proceeding.
        """
        # This test documents the finding. No runtime assertion needed
        # beyond confirming the method exists.
        assert hasattr(EventService, "verify_chain")
        assert callable(EventService.verify_chain)

    @pytest.mark.asyncio
    async def test_mutation_sensitive_caller_must_verify_before_commit(self, factory):
        """
        PROOF-OF-CONCEPT: A mutation-sensitive operation MUST verify chain
        integrity before committing, or risk corrupting the chain.

        This test simulates an approval flow that creates an event without
        verifying the chain first, then shows that verify_chain detects the
        corruption after the fact.
        """
        import tempfile, os
        db_path = os.path.join(tempfile.gettempdir(), "mutation_audit_test.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            # Create initial event
            event1 = await EventService.create(
                db, event_type="APPROVAL", payload={"action": "approve"},
                run_id="approval-run",
            )
            await db.commit()

            # Tamper with the chain (simulating a concurrent corruption)
            await db.execute(
                ObservatoryEvent.__table__.update()
                .where(ObservatoryEvent.id == event1.id)
                .values(event_hash="corrupted_hash")
            )
            await db.commit()

        async with factory() as db:
            # A mutation-sensitive operation that creates another event
            # will chain to the corrupted hash — propagating the corruption
            event2 = await EventService.create(
                db, event_type="APPROVAL", payload={"action": "execute"},
                run_id="approval-run",
            )
            await db.commit()

        # verify_chain AFTER the fact detects the corruption
        async with factory() as db:
            result = await EventService.verify_chain(db, run_id="approval-run")
            assert result.valid is False, \
                "Chain should be invalid after tampered event, but verify_chain returned valid"

        await engine.dispose()
        os.remove(db_path)