from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

from .adapters import AgentAdapter, AgentInvocation


ProviderCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass(frozen=True)
class ProviderPolicy:
    timeout_seconds: float = 120.0
    max_output_characters: int = 100_000
    allowed_capabilities: tuple[str, ...] = ()


class CallableAgentAdapter(AgentAdapter):
    """Safe adapter around an injected async provider callable.

    This is the integration seam for Hermes, Codex, Claude Code, Manus, and
    local runtimes. Provider credentials and network clients remain outside
    the shared orchestration core.
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: List[str],
        invoke_callable: ProviderCallable,
        policy: Optional[ProviderPolicy] = None,
    ) -> None:
        self.agent_id = agent_id
        self._capabilities = tuple(capabilities)
        self._invoke_callable = invoke_callable
        self._policy = policy or ProviderPolicy()
        self._cancelled: set[str] = set()
        self._events: dict[str, asyncio.Queue[Dict[str, Any]]] = {}

    async def health(self) -> Dict[str, Any]:
        return {"agent_id": self.agent_id, "status": "ok", "provider": "callable"}

    async def capabilities(self) -> List[str]:
        return list(self._capabilities)

    async def invoke(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentInvocation:
        run_id = uuid.uuid4().hex
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._events[run_id] = queue
        await queue.put({"run_id": run_id, "type": "started", "agent_id": self.agent_id})
        try:
            output = await asyncio.wait_for(
                self._invoke_callable(dict(task), dict(context)),
                timeout=self._policy.timeout_seconds,
            )
            if run_id in self._cancelled:
                raise asyncio.CancelledError
            serialized = json.dumps(output, default=str)
            if len(serialized) > self._policy.max_output_characters:
                raise ValueError("provider output exceeds configured limit")
            await queue.put({"run_id": run_id, "type": "completed", "agent_id": self.agent_id})
            return AgentInvocation(run_id=run_id, output=output)
        except Exception as exc:
            await queue.put({"run_id": run_id, "type": "failed", "agent_id": self.agent_id, "error": type(exc).__name__})
            raise
        finally:
            await queue.put({"run_id": run_id, "type": "closed"})

    async def cancel(self, run_id: str) -> bool:
        self._cancelled.add(run_id)
        queue = self._events.get(run_id)
        if queue is not None:
            await queue.put({"run_id": run_id, "type": "cancel_requested"})
        return True

    async def stream_events(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        queue = self._events.get(run_id)
        if queue is None:
            return
        while True:
            event = await queue.get()
            yield event
            if event.get("type") == "closed":
                self._events.pop(run_id, None)
                return


class OpenAISupervisorAdapter(CallableAgentAdapter):
    """Responses-API adapter with dependency injection and no import-time SDK requirement."""

    def __init__(self, client: Any, model: Optional[str] = None) -> None:
        self._client = client
        self._model = model or os.getenv("OPENAI_SUPERVISOR_MODEL", "gpt-5")
        super().__init__(
            agent_id="openai-supervisor",
            capabilities=["decompose", "delegate", "review", "reconcile", "escalate"],
            invoke_callable=self._invoke_openai,
            policy=ProviderPolicy(timeout_seconds=180.0, max_output_characters=120_000),
        )

    async def _invoke_openai(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are SintraPrime's governed supervisor. Return concise JSON only. "
                        "Do not claim authority to merge, deploy, transfer funds, or send legal, "
                        "financial, or government communications. Escalate those actions to the owner."
                    ),
                },
                {"role": "user", "content": json.dumps({"task": task, "context": context}, default=str)},
            ],
        )
        text = getattr(response, "output_text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"summary": text, "structured": False}
