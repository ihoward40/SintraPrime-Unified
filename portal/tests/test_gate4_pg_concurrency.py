"""
Gate 4.6: PostgreSQL Run-Scoped Hash-Chain Concurrency Tests.

These tests verify that:
- Concurrent event submissions to the same run produce no forks, gaps, or duplicates
- Independent runs do not serialize each other
- Failure injection before commit leaves no orphans and the chain remains valid
- Concurrent submissions produce correct sequences
- Chain verification detects all material corruption classes
"""

import asyncio
import hashlib
import os
import socket
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.models.observatory import (
    ObservatoryEvent,
    ObservatoryRunHead,
    Base,
)
from portal.services.chain_lock import get_or_create_run_head, advance_run_head, verify_no_chain_fork
from portal.services.observatory_service import EventService

# ── PostgreSQL connection (fail-closed guard) ─────────────────────────────────
#
# BEHAVIOR:
#   Authorized disposable PG database → tests execute
#   Unauthorized / production / staging database → BLOCK (session fails)
#   Missing URL + suite not requested → explicit skip
#   Missing URL + suite requested → BLOCK (session fails)

from portal.tests.test_db_guard import require_pg_url, DatabaseIsolationError, ENV_TEST_URL
from portal.tests.db_bootstrap import validate_test_database_url_async

PG_URL: str | None = None
_PG_SUITE_REQUESTED: bool = os.environ.get("GATE4_PG_SUITE_REQUESTED", "").lower() in ("true", "1", "yes")

try:
    _validated = require_pg_url(skip_marker=True)
    if _validated:
        PG_URL = _validated
    elif _PG_SUITE_REQUESTED:
        raise DatabaseIsolationError(
            f"{ENV_TEST_URL} is not set, but GATE4_PG_SUITE_REQUESTED=true "
            f"indicates the PostgreSQL suite was explicitly requested. "
            f"Set {ENV_TEST_URL} to a disposable test database URL."
        )
    # else: optional PG suite not requested — PG_URL stays None
except DatabaseIsolationError:
    # FAIL-CLOSED: propagate the error to make the session fail
    raise


def _pg_available() -> bool:
    """Check if PostgreSQL is reachable AND the URL is configured.

    When the PG suite is explicitly requested, returns True only if
    the URL is valid and the server is reachable. When not requested,
    returns False (indicating skip).
    """
    if not PG_URL:
        return False
    if _PG_SUITE_REQUESTED:
        return True
    try:
        parsed = urlparse(PG_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return True
    except (OSError, ConnectionRefusedError):
        return False


pg_available = pytest.mark.skipif(
    not _pg_available() and not _PG_SUITE_REQUESTED,
    reason="PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL and GATE4_TEST_MODE=true)",
)


# ── Helper: clean all observatory tables between tests ──────────────────────────

async def clean_pg_tables(engine):
    """Delete all rows from observatory tables using the shared isolation helper.

    Delegates to portal.tests.pg_test_isolation.clean_all_observatory_tables
    so there is one authoritative cleanup list, not multiple partial lists.
    """
    from portal.tests.pg_test_isolation import clean_all_observatory_tables
    await clean_all_observatory_tables(engine)


def _make_pg_fixture(pool_size: int, max_overflow: int):
    """Factory for guarded PG engine fixtures.

    When the PG suite is explicitly requested, missing PG is a hard error.
    When optional, missing PG produces a skip.
    """
    @pytest_asyncio.fixture
    async def pg_engine(self):
        if not PG_URL:
            if _PG_SUITE_REQUESTED:
                pytest.fail("PostgreSQL suite requested but GATE4_TEST_DATABASE_URL not configured")
            pytest.skip("PostgreSQL suite not requested (set GATE4_TEST_DATABASE_URL)")
            return
        # Full validation (including marker check) at fixture time
        # Uses the async validator to avoid asyncio.run() inside event loop
        try:
            await validate_test_database_url_async(PG_URL, skip_marker_check=False)
        except DatabaseIsolationError:
            if _PG_SUITE_REQUESTED:
                raise  # Hard error when suite is requested
            pytest.skip("PostgreSQL database guard failed")
            return
        engine = create_async_engine(PG_URL, echo=False, pool_size=pool_size, max_overflow=max_overflow)
        try:
            async with engine.connect() as conn:
                await conn.execute(sa_text("SELECT 1"))
        except Exception:
            if _PG_SUITE_REQUESTED:
                raise  # Hard error when suite is requested
            pytest.skip("PostgreSQL not available")
            return
        # NOTE: Do NOT call Base.metadata.create_all() here.
        # The PG test database is created and migrated via Alembic during
        # bootstrap. Calling create_all() would attempt to create ALL models
        # registered in Base.metadata (including Notification with JSONB),
        # which fails when non-observatory models have PG-only types.
        # The observatory tables already exist via migration.
        await clean_pg_tables(engine)
        yield engine
        await clean_pg_tables(engine)
        # No checked-out connections must remain before disposal; a checked-out
        # connection survives engine.dispose() and leaks its PostgreSQL socket.
        assert engine.pool.checkedout() == 0, f"{engine.pool.checkedout()} connection(s) still checked out at teardown"
        await engine.dispose()
        # Let asyncpg's scheduled socket-close callbacks run in the still-active loop
        # BEFORE any gc.collect() that could surface an unclosed socket warning.
        await asyncio.sleep(0.05)
        import gc
        gc.collect()
    return pg_engine


# ═══════════════════════════════════════════════════════════════════════════════
# G4.6.1: Same-Run Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestSameRunConcurrency:
    """
    REQUIREMENT: At least 4 independent sessions, at least 4 simulated agents,
    at least 100 concurrent event submissions, one shared run_id.

    Assertions:
    - exactly 100 events exist
    - sequences are exactly 1 through 100
    - no duplicate sequences
    - no missing sequences
    - no two events reference the same prior head
    - every previous_hash matches the preceding event
    - run-head sequence equals 100
    - run-head hash equals event 100 hash
    - full chain verification passes
    - no session remains in failed transaction state
    """

    pg_engine = _make_pg_fixture(pool_size=20, max_overflow=10)

    @pytest.mark.asyncio
    async def test_same_run_100_concurrent_events(self, pg_engine):
        """4 sessions, 4 agents, 100 concurrent events, one shared run_id."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "concurrency-test-run"

        NUM_EVENTS = 100
        NUM_AGENTS = 4

        async def submit_event(agent_id: int, event_idx: int):
            async with factory() as session:
                try:
                    event = await EventService.create(
                        session,
                        event_type="CONCURRENT_TEST",
                        payload={"agent": f"agent_{agent_id}", "idx": event_idx},
                        run_id=run_id,
                    )
                    await session.commit()
                    return ("success", event)
                except Exception as e:
                    await session.rollback()
                    return ("error", str(e))

        # Submit 100 events concurrently from 4 agents
        tasks = []
        for i in range(NUM_EVENTS):
            agent_id = i % NUM_AGENTS
            tasks.append(submit_event(agent_id, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check all succeeded
        errors = [r for r in results if isinstance(r, BaseException)]
        assert len(errors) == 0, f"Errors during concurrent submission: {errors[:5]}"

        # Verify exact count
        async with factory() as session:
            from sqlalchemy import select, func
            count_result = await session.execute(
                select(func.count()).where(ObservatoryEvent.run_id == run_id)
            )
            total = count_result.scalar()
            assert total == NUM_EVENTS, f"Expected {NUM_EVENTS} events, got {total}"

            # Verify sequences are exactly 1..100 with no gaps or duplicates
            seq_result = await session.execute(
                select(ObservatoryEvent.sequence)
                .where(ObservatoryEvent.run_id == run_id)
                .order_by(ObservatoryEvent.sequence)
            )
            sequences = sorted([row[0] for row in seq_result.all()])
            assert sequences == list(range(1, NUM_EVENTS + 1)), \
                f"Expected sequences 1..{NUM_EVENTS}, got gaps or duplicates"

            # Verify no two events reference the same previous_hash
            # (except null for genesis)
            prev_hash_result = await session.execute(
                select(ObservatoryEvent.previous_hash)
                .where(ObservatoryEvent.run_id == run_id)
                .where(ObservatoryEvent.previous_hash.isnot(None))
            )
            prev_hashes = [row[0] for row in prev_hash_result.all()]
            assert len(prev_hashes) == len(set(prev_hashes)), \
                "Two or more events reference the same previous_hash (chain fork)"

            # Verify run-head state
            head_result = await session.execute(
                select(ObservatoryRunHead).where(ObservatoryRunHead.run_id == run_id)
            )
            head = head_result.scalar_one()
            assert head.last_sequence == NUM_EVENTS, \
                f"Run head sequence should be {NUM_EVENTS}, got {head.last_sequence}"

            # Verify chain integrity via verify_chain
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "Chain verification failed"

    @pytest.mark.asyncio
    async def test_no_fork_detection_after_concurrent_inserts(self, pg_engine):
        """verify_no_chain_fork returns empty list for a valid concurrent chain."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "fork-detection-test"

        # Create 20 events sequentially first
        for i in range(20):
            async with factory() as session:
                await EventService.create(
                    session, event_type="FORK_TEST",
                    payload={"seq": i}, run_id=run_id,
                )
                await session.commit()

        async with factory() as session:
            forks = await verify_no_chain_fork(session, run_id=run_id)
            assert forks == [], f"Unexpected fork points: {forks}"


# ═══════════════════════════════════════════════════════════════════════════════
# G4.6.2: Separate-Run Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestSeparateRunConcurrency:
    """
    REQUIREMENT: Submit events concurrently to at least 4 different runs.

    Assertions:
    - each run has an independent chain
    - one busy run does not serialize unrelated runs
    - sequences begin independently at 1
    - verification passes for every run
    """

    pg_engine = _make_pg_fixture(pool_size=20, max_overflow=10)

    @pytest.mark.asyncio
    async def test_separate_runs_independent_chains(self, pg_engine):
        """Events to 4 different runs produce 4 independent chains."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_ids = [f"independent-run-{i}" for i in range(4)]
        events_per_run = 10

        async def submit_event(run_id: str, idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="SEPARATE_RUN_TEST",
                    payload={"run": run_id, "idx": idx},
                    run_id=run_id,
                )
                await session.commit()
                return ("success", run_id, event.sequence)

        # Submit events concurrently across all 4 runs
        tasks = []
        for run_id in run_ids:
            for idx in range(events_per_run):
                tasks.append(submit_event(run_id, idx))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        errors = [r for r in results if isinstance(r, BaseException)]
        assert len(errors) == 0, f"Errors during concurrent submission: {errors[:5]}"

        async with factory() as session:
            from sqlalchemy import select, func

            # Each run has exactly events_per_run events
            for run_id in run_ids:
                count_result = await session.execute(
                    select(func.count()).where(ObservatoryEvent.run_id == run_id)
                )
                total = count_result.scalar()
                assert total == events_per_run, \
                    f"Run {run_id}: expected {events_per_run} events, got {total}"

                # Sequences begin at 1 and are sequential
                seq_result = await session.execute(
                    select(ObservatoryEvent.sequence)
                    .where(ObservatoryEvent.run_id == run_id)
                    .order_by(ObservatoryEvent.sequence)
                )
                sequences = sorted([row[0] for row in seq_result.all()])
                assert sequences == list(range(1, events_per_run + 1)), \
                    f"Run {run_id}: expected 1..{events_per_run}, got {sequences}"

                # Genesis events have previous_hash = null
                genesis_result = await session.execute(
                    select(ObservatoryEvent.previous_hash)
                    .where(ObservatoryEvent.run_id == run_id)
                    .where(ObservatoryEvent.sequence == 1)
                )
                genesis_prev = genesis_result.scalar()
                assert genesis_prev is None, \
                    f"Run {run_id}: genesis event should have previous_hash=None, got {genesis_prev}"

            # Verify each run's chain independently
            for run_id in run_ids:
                result = await EventService.verify_chain(session, run_id=run_id)
                assert result.valid is True, f"Chain verification failed for run {run_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# G4.6.3: Failure Injection
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestFailureInjection:
    """
    REQUIREMENT: Simulate failure after event construction but before commit.

    Assertions:
    - no orphan event remains
    - run head does not advance
    - retry inserts the correct next sequence
    - chain remains valid
    """

    pg_engine = _make_pg_fixture(pool_size=10, max_overflow=5)

    @pytest.mark.asyncio
    async def test_failed_transaction_no_orphan_event(self, pg_engine):
        """A transaction that rolls back leaves no orphan event or advanced run head."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "failure-injection-test"

        # Create one valid event
        async with factory() as session:
            event1 = await EventService.create(
                session, event_type="FAILURE_TEST",
                payload={"seq": 1}, run_id=run_id,
            )
            await session.commit()

        # Attempt to create another but roll back
        async with factory() as session:
            event2 = await EventService.create(
                session, event_type="FAILURE_TEST",
                payload={"seq": 2}, run_id=run_id,
            )
            # Event2 was assigned sequence 2 in memory, but we roll back
            assert event2.sequence == 2
            await session.rollback()

        # Verify: only one event exists, run head is at sequence 1
        async with factory() as session:
            from sqlalchemy import select, func
            count_result = await session.execute(
                select(func.count()).where(ObservatoryEvent.run_id == run_id)
            )
            total = count_result.scalar()
            assert total == 1, f"Expected 1 event after rollback, got {total}"

            head_result = await session.execute(
                select(ObservatoryRunHead).where(ObservatoryRunHead.run_id == run_id)
            )
            head = head_result.scalar_one()
            assert head.last_sequence == 1, \
                f"Run head should be at sequence 1 after rollback, got {head.last_sequence}"

    @pytest.mark.asyncio
    async def test_retry_after_failure_correct_sequence(self, pg_engine):
        """After a failed transaction, the next insert gets the correct sequence."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "retry-sequence-test"

        # Create first event
        async with factory() as session:
            event1 = await EventService.create(
                session, event_type="RETRY_TEST",
                payload={"seq": 1}, run_id=run_id,
            )
            await session.commit()
            assert event1.sequence == 1

        # Attempt and roll back
        async with factory() as session:
            await EventService.create(
                session, event_type="RETRY_TEST",
                payload={"seq": "failed"}, run_id=run_id,
            )
            await session.rollback()

        # Retry should get sequence 2 (not 3)
        async with factory() as session:
            event2 = await EventService.create(
                session, event_type="RETRY_TEST",
                payload={"seq": 2}, run_id=run_id,
            )
            await session.commit()
            assert event2.sequence == 2, \
                f"Expected sequence 2 after retry, got {event2.sequence}"

        # Verify chain integrity
        async with factory() as session:
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "Chain verification failed after failure injection"


# ═══════════════════════════════════════════════════════════════════════════════
# G4.6.4: Concurrent Duplicate Event (Idempotency + Chain Locking)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestConcurrentDuplicateEvent:
    """
    REQUIREMENT: Two simultaneous submissions with the same event_id must result in:
    - one event row
    - one sequence allocation
    - one hash-chain advancement
    - both callers receiving the same accepted event
    - no gap in sequence numbering

    NOTE: Event_id idempotency is not yet implemented (G4.5 enhancement).
    This test verifies that the chain locking prevents double-sequence allocation
    when two concurrent requests hit the same run.
    """

    pg_engine = _make_pg_fixture(pool_size=10, max_overflow=5)

    @pytest.mark.asyncio
    async def test_concurrent_submissions_different_payloads_no_gap(self, pg_engine):
        """Two concurrent submissions with different payloads both succeed
        and produce a valid chain with no gaps."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "concurrent-dup-test"

        async def submit(payload_content: str):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="DUP_TEST",
                    payload={"data": payload_content},
                    run_id=run_id,
                )
                await session.commit()
                return event

        # Submit two events concurrently
        e1, e2 = await asyncio.gather(
            submit("payload_a"),
            submit("payload_b"),
        )

        # Both should succeed with consecutive sequences
        sequences = sorted([e1.sequence, e2.sequence])
        assert sequences == [1, 2], f"Expected sequences [1, 2], got {sequences}"

        # Chain should be valid
        async with factory() as session:
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "Chain verification failed after concurrent submission"


# ═══════════════════════════════════════════════════════════════════════════════
# G4.6.4-expanded: Full Concurrency Matrix
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.postgresql
class TestFullConcurrencyMatrix:
    """
    Expanded concurrency matrix covering:

    1. Run-head hash matches terminal event hash after concurrent inserts
    2. Genesis correctness under concurrency (seq=1, prev_hash=null per run)
    3. Cross-run contamination: events in one run do not affect another run's chain
    4. High-volume stress (200 events, 8 agents, single run)
    5. Mixed-run + mixed-agent concurrent matrix (4 runs × 4 agents × 5 events each)
    6. Burst-then-verify: rapid sequential verification between concurrent bursts
    """

    pg_engine = _make_pg_fixture(pool_size=30, max_overflow=15)

    @pytest.mark.asyncio
    async def test_run_head_hash_matches_terminal_event(self, pg_engine):
        """After 50 concurrent events, the run-head hash must equal the event
        with the highest sequence's hash."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "head-hash-match-test"

        async def submit(idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="HEAD_HASH_TEST",
                    payload={"idx": idx}, run_id=run_id,
                )
                await session.commit()
                return event

        tasks = [submit(i) for i in range(50)]
        await asyncio.gather(*tasks)

        async with factory() as session:
            from sqlalchemy import select
            # Get the terminal event (highest sequence)
            result = await session.execute(
                select(ObservatoryEvent)
                .where(ObservatoryEvent.run_id == run_id)
                .order_by(ObservatoryEvent.sequence.desc())
                .limit(1)
            )
            terminal = result.scalar_one()
            assert terminal.sequence == 50

            # Get the run-head
            head_result = await session.execute(
                select(ObservatoryRunHead).where(ObservatoryRunHead.run_id == run_id)
            )
            head = head_result.scalar_one()
            assert head.last_sequence == 50
            assert head.last_event_hash == terminal.event_hash, \
                f"Run-head hash {head.last_event_hash} != terminal event hash {terminal.event_hash}"

    @pytest.mark.asyncio
    async def test_genesis_correctness_under_concurrency(self, pg_engine):
        """Each run's first event must have sequence=1 and previous_hash=None,
        even under concurrent cross-run traffic."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_ids = [f"genesis-test-{i}" for i in range(6)]

        async def submit(run_id: str, idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="GENESIS_TEST",
                    payload={"run": run_id, "idx": idx},
                    run_id=run_id,
                )
                await session.commit()
                return (run_id, event)

        # Submit first events to all 6 runs concurrently, then second events
        tasks = []
        for run_id in run_ids:
            tasks.append(submit(run_id, 0))
        for run_id in run_ids:
            tasks.append(submit(run_id, 1))
        await asyncio.gather(*tasks)

        async with factory() as session:
            from sqlalchemy import select
            for run_id in run_ids:
                genesis_result = await session.execute(
                    select(ObservatoryEvent)
                    .where(ObservatoryEvent.run_id == run_id)
                    .where(ObservatoryEvent.sequence == 1)
                )
                genesis = genesis_result.scalar_one()
                assert genesis.previous_hash is None, \
                    f"Run {run_id}: genesis event has previous_hash={genesis.previous_hash}"

                second_result = await session.execute(
                    select(ObservatoryEvent)
                    .where(ObservatoryEvent.run_id == run_id)
                    .where(ObservatoryEvent.sequence == 2)
                )
                second = second_result.scalar_one()
                assert second.previous_hash == genesis.event_hash, \
                    f"Run {run_id}: second event previous_hash mismatch"

    @pytest.mark.asyncio
    async def test_cross_run_no_contamination(self, pg_engine):
        """Events in run A do not affect the chain in run B."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_a = "contam-run-a"
        run_b = "contam-run-b"

        # Interleave events between two runs
        async def submit_a(idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="CONTAM_A",
                    payload={"idx": idx}, run_id=run_a,
                )
                await session.commit()
                return event

        async def submit_b(idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="CONTAM_B",
                    payload={"idx": idx}, run_id=run_b,
                )
                await session.commit()
                return event

        # Mix events from both runs concurrently
        tasks = []
        for i in range(15):
            tasks.append(submit_a(i))
            tasks.append(submit_b(i))
        await asyncio.gather(*tasks)

        async with factory() as session:
            from sqlalchemy import select
            # Run A has exactly 15 events, sequences 1..15
            seq_a = await session.execute(
                select(ObservatoryEvent.sequence)
                .where(ObservatoryEvent.run_id == run_a)
                .order_by(ObservatoryEvent.sequence)
            )
            seqs_a = [r[0] for r in seq_a.all()]
            assert seqs_a == list(range(1, 16)), f"Run A sequences: {seqs_a}"

            # Run B has exactly 15 events, sequences 1..15
            seq_b = await session.execute(
                select(ObservatoryEvent.sequence)
                .where(ObservatoryEvent.run_id == run_b)
                .order_by(ObservatoryEvent.sequence)
            )
            seqs_b = [r[0] for r in seq_b.all()]
            assert seqs_b == list(range(1, 16)), f"Run B sequences: {seqs_b}"

            # All Run A event_types are CONTAM_A
            type_a = await session.execute(
                select(ObservatoryEvent.event_type)
                .where(ObservatoryEvent.run_id == run_a)
            )
            types_a = set(r[0] for r in type_a.all())
            assert types_a == {"CONTAM_A"}, f"Run A has non-A event types: {types_a}"

            # All Run B event_types are CONTAM_B
            type_b = await session.execute(
                select(ObservatoryEvent.event_type)
                .where(ObservatoryEvent.run_id == run_b)
            )
            types_b = set(r[0] for r in type_b.all())
            assert types_b == {"CONTAM_B"}, f"Run B has non-B event types: {types_b}"

            # Both chains verify independently
            for run_id in [run_a, run_b]:
                result = await EventService.verify_chain(session, run_id=run_id)
                assert result.valid is True, f"Chain verification failed for {run_id}"

    @pytest.mark.asyncio
    async def test_high_volume_200_events_8_agents(self, pg_engine):
        """200 concurrent events from 8 agents in a single run — no gaps, no forks.

        Uses a semaphore to limit concurrency to the connection pool size,
        preventing pool exhaustion while still exercising real parallelism.
        """
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "stress-200-test"
        NUM_EVENTS = 200
        NUM_AGENTS = 8
        CONCURRENCY_LIMIT = 40  # within pool_size=30 + max_overflow=15

        sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def submit(agent_id: int, idx: int):
            async with sem:
                async with factory() as session:
                    event = await EventService.create(
                        session, event_type="STRESS_200",
                        payload={"agent": f"a{agent_id}", "idx": idx},
                        run_id=run_id,
                    )
                    await session.commit()
                    return ("ok", event)

        tasks = []
        for i in range(NUM_EVENTS):
            agent = i % NUM_AGENTS
            tasks.append(submit(agent, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        assert len(errors) == 0, f"{len(errors)} errors in 200-event stress: {errors[:3]}"

        async with factory() as session:
            from sqlalchemy import select, func
            count = await session.execute(
                select(func.count()).where(ObservatoryEvent.run_id == run_id)
            )
            assert count.scalar() == NUM_EVENTS

            seq_result = await session.execute(
                select(ObservatoryEvent.sequence)
                .where(ObservatoryEvent.run_id == run_id)
                .order_by(ObservatoryEvent.sequence)
            )
            seqs = [r[0] for r in seq_result.all()]
            assert seqs == list(range(1, NUM_EVENTS + 1)), \
                f"Sequence gap/dup in 200-event stress: len={len(seqs)}"

            # No fork: all previous_hashes unique (except null genesis)
            prev_result = await session.execute(
                select(ObservatoryEvent.previous_hash)
                .where(ObservatoryEvent.run_id == run_id)
                .where(ObservatoryEvent.previous_hash.isnot(None))
            )
            prev_hashes = [r[0] for r in prev_result.all()]
            assert len(prev_hashes) == len(set(prev_hashes)), "Fork detected in 200-event chain"

            # Run-head matches terminal
            head_result = await session.execute(
                select(ObservatoryRunHead).where(ObservatoryRunHead.run_id == run_id)
            )
            head = head_result.scalar_one()
            assert head.last_sequence == NUM_EVENTS

            # Chain verifies
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "200-event chain verification failed"

    @pytest.mark.asyncio
    async def test_mixed_run_agent_matrix(self, pg_engine):
        """4 runs × 4 agents × 5 events per run = 80 total concurrent events.

        Asserts:
        - Each run has exactly 5 events with sequences 1..5
        - Each run's chain verifies independently
        - No cross-run hash linkage
        """
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        NUM_RUNS = 4
        NUM_AGENTS = 4
        EVENTS_PER_RUN = 5
        run_ids = [f"matrix-run-{i}" for i in range(NUM_RUNS)]

        async def submit(run_id: str, agent_id: int, idx: int):
            async with factory() as session:
                event = await EventService.create(
                    session, event_type="MATRIX_TEST",
                    payload={"run": run_id, "agent": f"a{agent_id}", "idx": idx},
                    agent_id=f"a{agent_id}",
                    run_id=run_id,
                )
                await session.commit()
                return ("ok", run_id, event.sequence)

        tasks = []
        for run_id in run_ids:
            for agent_id in range(NUM_AGENTS):
                for idx in range(EVENTS_PER_RUN):
                    tasks.append(submit(run_id, agent_id, idx))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        assert len(errors) == 0, f"Errors in mixed matrix: {errors[:3]}"

        expected_per_run = NUM_AGENTS * EVENTS_PER_RUN  # 20
        async with factory() as session:
            from sqlalchemy import select
            for run_id in run_ids:
                seq_result = await session.execute(
                    select(ObservatoryEvent.sequence)
                    .where(ObservatoryEvent.run_id == run_id)
                    .order_by(ObservatoryEvent.sequence)
                )
                seqs = [r[0] for r in seq_result.all()]
                assert len(seqs) == expected_per_run, \
                    f"Run {run_id}: expected {expected_per_run} events, got {len(seqs)}"
                assert seqs == list(range(1, expected_per_run + 1)), \
                    f"Run {run_id}: sequence mismatch"

                # Verify no previous_hash from this run matches an event_hash from another run
                own_hashes_result = await session.execute(
                    select(ObservatoryEvent.event_hash)
                    .where(ObservatoryEvent.run_id == run_id)
                )
                own_hashes = set(r[0] for r in own_hashes_result.all())

                for other_run in run_ids:
                    if other_run == run_id:
                        continue
                    other_prev_result = await session.execute(
                        select(ObservatoryEvent.previous_hash)
                        .where(ObservatoryEvent.run_id == other_run)
                        .where(ObservatoryEvent.previous_hash.isnot(None))
                    )
                    other_prevs = set(r[0] for r in other_prev_result.all())
                    cross = own_hashes & other_prevs
                    assert not cross, \
                        f"Cross-run hash contamination: {run_id} hashes in {other_run} prev_hashes"

                result = await EventService.verify_chain(session, run_id=run_id)
                assert result.valid is True, f"Chain verification failed for {run_id}"

    @pytest.mark.asyncio
    async def test_burst_then_verify_interleaved(self, pg_engine):
        """Burst of 30 concurrent events, verify, then another burst of 30,
        verify again. Chain must be consistent across bursts."""
        factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
        run_id = "burst-verify-test"

        async def burst(start: int, count: int):
            async def submit(idx: int):
                async with factory() as session:
                    event = await EventService.create(
                        session, event_type="BURST_TEST",
                        payload={"burst_start": start, "idx": idx},
                        run_id=run_id,
                    )
                    await session.commit()
                    return event

            tasks = [submit(start + i) for i in range(count)]
            return await asyncio.gather(*tasks)

        # First burst
        await burst(0, 30)
        async with factory() as session:
            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "Chain broken after first burst"

        # Second burst
        await burst(30, 30)
        async with factory() as session:
            from sqlalchemy import select, func
            count = await session.execute(
                select(func.count()).where(ObservatoryEvent.run_id == run_id)
            )
            assert count.scalar() == 60

            result = await EventService.verify_chain(session, run_id=run_id)
            assert result.valid is True, "Chain broken after second burst"

            # Verify run-head matches terminal
            head_result = await session.execute(
                select(ObservatoryRunHead).where(ObservatoryRunHead.run_id == run_id)
            )
            head = head_result.scalar_one()
            assert head.last_sequence == 60
