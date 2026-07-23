"""
Gate 4.6.5: Broadcast-After-Commit Invariant Test.

Proves that WebSocket/SSE broadcast occurs ONLY after the database commit
has succeeded. If the commit fails (simulated via a mock that raises),
the broadcast must NOT execute.

This test also verifies the happy path: when commit succeeds, the broadcast
payload contains the committed event's data.
"""

import inspect
import pytest
from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime
from uuid import uuid4

from portal.models.observatory import ObservatoryEvent


@pytest.mark.asyncio
async def test_broadcast_does_not_fire_on_commit_failure():
    """If db.commit() raises, _manager.broadcast must NOT be called.

    The router calls commit() before broadcast(). If commit fails, the
    broadcast code is unreachable because the exception propagates.
    """
    from portal.routers.observatory import ingest_event, EventCreateRequest
    from portal.schemas.observatory import EventType

    ts = datetime.now(UTC)
    event = ObservatoryEvent(
        id=uuid4(),
        run_id="commit-fail-test",
        sequence=1,
        hash_version=2,
        event_type="MISSION_CREATED",
        payload={"test": "commit_failure"},
        event_hash="abc123",
        previous_hash=None,
        timestamp=ts,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=RuntimeError("Connection lost"))

    with patch("portal.routers.observatory.EventService.create", return_value=event), \
         patch("portal.routers.observatory._manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        request = EventCreateRequest(
            event_type=EventType.MISSION_CREATED,
            payload={"test": "commit_failure"},
        )

        with pytest.raises(RuntimeError, match="Connection lost"):
            await ingest_event(request, db=mock_session)

        mock_manager.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_fires_after_successful_commit():
    """When commit succeeds, broadcast is called with the committed event data."""
    from portal.routers.observatory import ingest_event, EventCreateRequest
    from portal.schemas.observatory import EventType

    ts = datetime.now(UTC)
    event_id = uuid4()
    event = ObservatoryEvent(
        id=event_id,
        run_id="broadcast-success-test",
        sequence=1,
        hash_version=2,
        event_type="MISSION_CREATED",
        payload={"test": "broadcast"},
        event_hash="abc123hash",
        previous_hash=None,
        timestamp=ts,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("portal.routers.observatory.EventService.create", return_value=event), \
         patch("portal.routers.observatory._manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        request = EventCreateRequest(
            event_type=EventType.MISSION_CREATED,
            payload={"test": "broadcast"},
        )

        result = await ingest_event(request, db=mock_session)

        mock_session.commit.assert_called_once()
        mock_manager.broadcast.assert_called_once()

        # HTTP response contains the committed event's hash
        assert result["event_hash"] == "abc123hash"

        # Broadcast payload contains the committed event's id and type
        broadcast_data = mock_manager.broadcast.call_args[0][0]
        assert broadcast_data["id"] == str(event_id)
        assert broadcast_data["event_type"] == "MISSION_CREATED"


@pytest.mark.asyncio
async def test_broadcast_payload_contains_committed_event_data():
    """The broadcast payload must reflect the event that was actually committed."""
    from portal.routers.observatory import ingest_event, EventCreateRequest
    from portal.schemas.observatory import EventType

    ts = datetime.now(UTC)
    event_id = uuid4()
    event_hash = "sha256_of_committed_event"
    event = ObservatoryEvent(
        id=event_id,
        run_id="payload-test",
        sequence=1,
        hash_version=2,
        event_type="EVIDENCE_CAPTURED",
        payload={"evidence": "doc1.pdf"},
        event_hash=event_hash,
        previous_hash=None,
        timestamp=ts,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("portal.routers.observatory.EventService.create", return_value=event), \
         patch("portal.routers.observatory._manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        request = EventCreateRequest(
            event_type=EventType.EVIDENCE_CAPTURED,
            payload={"evidence": "doc1.pdf"},
        )

        result = await ingest_event(request, db=mock_session)

        assert result["event_hash"] == event_hash
        assert result["id"] == str(event_id)

        broadcast_data = mock_manager.broadcast.call_args[0][0]
        assert broadcast_data["id"] == str(event_id)
        assert broadcast_data["event_type"] == "EVIDENCE_CAPTURED"
        assert broadcast_data["payload"] == {"evidence": "doc1.pdf"}


@pytest.mark.asyncio
async def test_commit_called_before_broadcast_in_source_order():
    """Verify the source code order: commit() appears before broadcast()
    in the ingest_event function."""
    from portal.routers.observatory import ingest_event

    source = inspect.getsource(ingest_event)

    commit_line = None
    broadcast_line = None
    for i, line in enumerate(source.splitlines()):
        if "commit()" in line and "await" in line and commit_line is None:
            commit_line = i
        if "broadcast(" in line and "await" in line and broadcast_line is None:
            broadcast_line = i

    assert commit_line is not None, "commit() call not found in ingest_event source"
    assert broadcast_line is not None, "broadcast() call not found in ingest_event source"
    assert commit_line < broadcast_line, \
        f"commit() at line {commit_line} must come before broadcast() at line {broadcast_line}"
