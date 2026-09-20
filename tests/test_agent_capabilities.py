from datetime import datetime, timedelta, timezone

import pytest

from agent_capabilities import (
    ActionDecision,
    BrowserAction,
    DefaultActionPolicy,
    GovernedMemoryStore,
    MemoryRecord,
)


@pytest.mark.asyncio
async def test_memory_is_tenant_and_subject_scoped() -> None:
    store = GovernedMemoryStore()
    await store.put(
        MemoryRecord(
            memory_id="m-1",
            tenant_id="tenant-a",
            subject_id="user-1",
            text="User prefers citation-bearing legal research.",
            tags=("preference", "citations"),
        )
    )

    visible = await store.search(
        tenant_id="tenant-a",
        subject_id="user-1",
        query="legal citations",
    )
    wrong_tenant = await store.search(
        tenant_id="tenant-b",
        subject_id="user-1",
        query="legal citations",
    )
    wrong_subject = await store.search(
        tenant_id="tenant-a",
        subject_id="user-2",
        query="legal citations",
    )

    assert [record.memory_id for record in visible] == ["m-1"]
    assert wrong_tenant == []
    assert wrong_subject == []


@pytest.mark.asyncio
async def test_expired_memory_is_not_returned_and_can_be_deleted() -> None:
    store = GovernedMemoryStore()
    await store.put(
        MemoryRecord(
            memory_id="expired",
            tenant_id="tenant-a",
            subject_id="user-1",
            text="Temporary fact",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
    )

    assert await store.search(
        tenant_id="tenant-a", subject_id="user-1", query="temporary"
    ) == []
    assert await store.delete(tenant_id="tenant-a", memory_id="expired") is True
    assert await store.delete(tenant_id="tenant-a", memory_id="expired") is False


def test_default_action_policy_fails_closed() -> None:
    policy = DefaultActionPolicy()

    assert (
        policy.decide(
            BrowserAction(action="read", target="https://example.test"),
            tenant_id="tenant-a",
            actor_id="agent-1",
        )
        is ActionDecision.ALLOW
    )
    assert (
        policy.decide(
            BrowserAction(action="submit", target="#court-filing"),
            tenant_id="tenant-a",
            actor_id="agent-1",
        )
        is ActionDecision.REQUIRE_APPROVAL
    )
    assert (
        policy.decide(
            BrowserAction(action="execute-javascript", target="document"),
            tenant_id="tenant-a",
            actor_id="agent-1",
        )
        is ActionDecision.DENY
    )
    assert (
        policy.decide(
            BrowserAction(action="read", target="https://example.test"),
            tenant_id="",
            actor_id="agent-1",
        )
        is ActionDecision.DENY
    )
