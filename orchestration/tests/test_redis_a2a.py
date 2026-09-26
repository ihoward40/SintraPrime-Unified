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


def test_inbox_key_rejects_unsafe_agent_ids():
    transport = RedisA2ATransport(namespace="test")
    with pytest.raises(ValueError):
        transport.inbox_key("agent:admin")
