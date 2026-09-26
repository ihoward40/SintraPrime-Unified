"""Redis transport for cross-process SintraPrime agent messaging."""
from __future__ import annotations

import json
import os
from typing import Any

from redis.asyncio import Redis

from .a2a_protocol import Message, is_external_intent


class RedisA2ATransport:
    """Point-to-point A2A delivery using one Redis list per agent.

    Redis is intentionally an optional transport: the existing in-memory bus
    remains the default for embedded/local use. Set ``A2A_BACKEND=redis`` and
    ``REDIS_URL`` to enable cross-process delivery through the API.
    """

    def __init__(self, redis_url: str | None = None, namespace: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace or os.getenv("A2A_REDIS_NAMESPACE", "sintraprime:a2a")
        self._redis: Redis | None = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def inbox_key(self, agent_id: str) -> str:
        if not agent_id or ":" in agent_id or " " in agent_id:
            raise ValueError("agent_id must be non-empty and may not contain spaces or ':'")
        return f"{self.namespace}:inbox:{agent_id}"

    async def send(self, message: Message) -> None:
        """Enqueue a direct message for the target agent."""
        if is_external_intent(message):
            raise PermissionError("Dispatch blocked: raw Redis transport cannot carry external-action intent")
        if message.to_agent == "*":
            raise ValueError("Redis transport supports direct delivery only")
        await self.redis.rpush(self.inbox_key(message.to_agent), json.dumps(message.to_dict()))
        if message.ttl is not None:
            await self.redis.expire(self.inbox_key(message.to_agent), max(1, int(message.ttl)))

    async def receive(self, agent_id: str, timeout: int = 5) -> Message | None:
        """Block for up to ``timeout`` seconds and return the next message."""
        result = await self.redis.blpop(self.inbox_key(agent_id), timeout=max(0, timeout))
        if result is None:
            return None
        _, raw = result
        message = Message.from_dict(json.loads(raw))
        if is_external_intent(message):
            raise PermissionError("Dispatch blocked: raw Redis message contains external-action intent")
        return None if message.is_expired() else message

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def ping(self) -> bool:
        return bool(await self.redis.ping())
