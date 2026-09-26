"""Redis transport with acknowledgement, reclaim, retry, and DLQ semantics."""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from redis.asyncio import Redis

from .a2a_governance import DispatchAudit
from .a2a_protocol import Message, is_external_intent


class RedisA2ATransport:
    """Point-to-point A2A delivery with persistent in-flight and DLQ state."""

    def __init__(self, redis_url: str | None = None, namespace: str | None = None, audit_store: Any | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace or os.getenv("A2A_REDIS_NAMESPACE", "sintraprime:a2a")
        self.audit_store = audit_store
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

    def inflight_key(self, agent_id: str) -> str:
        return f"{self.namespace}:inflight:{self.inbox_key(agent_id).rsplit(':', 1)[-1]}"

    def dlq_key(self, agent_id: str) -> str:
        return f"{self.namespace}:dlq:{self.inbox_key(agent_id).rsplit(':', 1)[-1]}"

    async def _audit(self, message: Message, status: str, reason: str | None = None) -> None:
        if self.audit_store is None:
            return
        self.audit_store.append(DispatchAudit(
            mission_id=message.correlation_id,
            objective="REDIS_DELIVERY",
            agents_used=(message.from_agent, message.to_agent),
            sources_used=(), claims_verified=(), risks_flagged=(),
            user_approval="not required", external_action_taken=False,
            final_output_hash=str(message.headers.get("final_content_hash", "")),
            payload_hash=str(message.headers.get("final_content_hash", "")),
            status=status, reason_code="redis_delivery", reason_detail=reason,
        ))

    async def send(self, message: Message) -> None:
        if is_external_intent(message):
            raise PermissionError("Dispatch blocked: raw Redis transport cannot carry external-action intent")
        if message.to_agent == "*":
            raise ValueError("Redis transport supports direct delivery only")
        await self.redis.rpush(self.inbox_key(message.to_agent), json.dumps(message.to_dict()))
        if message.ttl is not None:
            await self.redis.expire(self.inbox_key(message.to_agent), max(1, int(message.ttl)))

    async def receive_with_delivery(self, agent_id: str, timeout: int = 5) -> tuple[Message, str] | None:
        result = await self.redis.blpop(self.inbox_key(agent_id), timeout=max(0, timeout))
        if result is None:
            return None
        _, raw = result
        message = Message.from_dict(json.loads(raw))
        if is_external_intent(message):
            raise PermissionError("Dispatch blocked: raw Redis message contains external-action intent")
        if message.is_expired():
            await self._audit(message, "expired", "message TTL elapsed before receive")
            return None
        delivery_id = uuid.uuid5(uuid.NAMESPACE_URL, message.message_id).hex
        attempts = int(message.headers.get("redis_attempts", 1))
        envelope = {"delivery_id": delivery_id, "attempts": attempts, "received_at": time.time(), "message": message.to_dict()}
        await self.redis.rpush(self.inflight_key(agent_id), json.dumps(envelope))
        await self._audit(message, "inflight")
        return message, delivery_id

    async def receive(self, agent_id: str, timeout: int = 5) -> Message | None:
        result = await self.receive_with_delivery(agent_id, timeout)
        return result[0] if result else None

    async def ack(self, agent_id: str, delivery_id: str) -> bool:
        removed = await self.redis.lrem(self.inflight_key(agent_id), 1, await self._find_envelope(agent_id, delivery_id))
        return bool(removed)

    async def _find_envelope(self, agent_id: str, delivery_id: str) -> str:
        for raw in await self.redis.lrange(self.inflight_key(agent_id), 0, -1):
            if json.loads(raw).get("delivery_id") == delivery_id:
                return raw
        return ""

    async def reclaim(self, agent_id: str, visibility_timeout: float = 30, max_retries: int = 3) -> int:
        reclaimed = 0
        for raw in await self.redis.lrange(self.inflight_key(agent_id), 0, -1):
            envelope = json.loads(raw)
            if time.time() - float(envelope["received_at"]) < visibility_timeout:
                continue
            message = Message.from_dict(envelope["message"])
            await self.redis.lrem(self.inflight_key(agent_id), 1, raw)
            if int(envelope["attempts"]) >= max_retries:
                await self.redis.rpush(self.dlq_key(agent_id), json.dumps(envelope))
                await self._audit(message, "dlq", "Redis retry limit reached")
            else:
                envelope["attempts"] = int(envelope["attempts"]) + 1
                envelope["received_at"] = time.time()
                message_data = message.to_dict()
                message_data.setdefault("headers", {})["redis_attempts"] = envelope["attempts"]
                await self.redis.rpush(self.inbox_key(agent_id), json.dumps(message_data))
                await self._audit(message, "reclaimed", "Redis visibility timeout elapsed")
            reclaimed += 1
        return reclaimed

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def ping(self) -> bool:
        return bool(await self.redis.ping())
