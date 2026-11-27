from __future__ import annotations

import json
import time

import pytest

from orchestration.a2a_protocol import Message, MessageType, Priority
from orchestration.redis_a2a import RedisA2ATransport


class FakeRedis:
    def __init__(self):
        self.items: dict[str, list[str]] = {}

    async def rpush(self, key: str, value: str):
        self.items.setdefault(key, []).append(value)

    async def expire(self, key: str, seconds: int):
        return True

    async def blpop(self, key: str, timeout: int = 0):
        values = self.items.get(key, [])
        if not values:
            return None
        return key, values.pop(0)

    async def lrange(self, key: str, start: int, end: int):
        values = self.items.get(key, [])
        return values[start:] if end == -1 else values[start:end + 1]

    async def lrem(self, key: str, count: int, value: str):
        values = self.items.get(key, [])
        removed = 0
        remaining = []
        for item in values:
            if item == value and (count == 0 or removed < count):
                removed += 1
            else:
                remaining.append(item)
        self.items[key] = remaining
        return removed

    async def ping(self):
        return True


@pytest.mark.asyncio
async def test_send_and_receive_round_trip():
    transport = RedisA2ATransport(namespace="test")
    fake = FakeRedis()
    transport._redis = fake
    message = Message(
        from_agent="research",
        to_agent="drafting",
        message_type=MessageType.DELEGATION,
        payload={"case_id": "C-1"},
        priority=Priority.HIGH,
        ttl=60,
    )

    await transport.send(message)
    received = await transport.receive("drafting")

    assert received is not None
    assert received.message_id == message.message_id
    assert received.payload == {"case_id": "C-1"}
    assert received.priority == Priority.HIGH


@pytest.mark.asyncio
async def test_expired_messages_are_not_delivered():
    transport = RedisA2ATransport(namespace="test")
    fake = FakeRedis()
    transport._redis = fake
    message = Message(
        from_agent="research",
        to_agent="drafting",
        message_type=MessageType.REQUEST,
        payload={},
        ttl=1,
        timestamp=time.time() - 10,
    )
    await fake.rpush(transport.inbox_key("drafting"), json.dumps(message.to_dict()))

    assert await transport.receive("drafting") is None


@pytest.mark.asyncio
async def test_ack_removes_inflight_delivery():
    transport = RedisA2ATransport(namespace="test")
    fake = FakeRedis()
    transport._redis = fake
    message = Message(from_agent="research", to_agent="drafting", message_type=MessageType.REQUEST, payload={})
    await transport.send(message)
    received = await transport.receive_with_delivery("drafting")
    assert received is not None
    _, delivery_id = received
    assert await transport.ack("drafting", delivery_id) is True
    assert fake.items[transport.inflight_key("drafting")] == []


@pytest.mark.asyncio
async def test_reclaim_retries_then_moves_to_dlq():
    transport = RedisA2ATransport(namespace="test")
    fake = FakeRedis()
    transport._redis = fake
    message = Message(from_agent="research", to_agent="drafting", message_type=MessageType.REQUEST, payload={})
    await transport.send(message)
    received = await transport.receive_with_delivery("drafting")
    assert received is not None
    raw = fake.items[transport.inflight_key("drafting")][0]
    envelope = json.loads(raw)
    envelope["received_at"] = time.time() - 100
    fake.items[transport.inflight_key("drafting")] = [json.dumps(envelope)]
    assert await transport.reclaim("drafting", visibility_timeout=1, max_retries=2) == 1
    assert await transport.receive("drafting") is not None
    received = await transport.receive_with_delivery("drafting", timeout=0)
    assert received is None
    raw = fake.items[transport.inflight_key("drafting")][0]
    envelope = json.loads(raw)
    envelope["received_at"] = time.time() - 100
    fake.items[transport.inflight_key("drafting")] = [json.dumps(envelope)]
    assert await transport.reclaim("drafting", visibility_timeout=1, max_retries=2) == 1
    assert len(fake.items[transport.dlq_key("drafting")]) == 1


def test_inbox_key_rejects_unsafe_agent_ids():
    transport = RedisA2ATransport(namespace="test")
    with pytest.raises(ValueError):
        transport.inbox_key("agent:admin")
