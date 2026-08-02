from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List


@dataclass
class AgentInvocation:
    run_id: str
    output: Dict[str, Any]
    evidence: List[str] = field(default_factory=list)


class AgentAdapter(ABC):
    """Provider-neutral contract for Hermes, Codex, Claude, Manus, OpenAI, and local agents."""

    agent_id: str

    @abstractmethod
    async def health(self) -> Dict[str, Any]: ...

    @abstractmethod
    async def capabilities(self) -> List[str]: ...

    @abstractmethod
    async def invoke(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentInvocation: ...

    @abstractmethod
    async def cancel(self, run_id: str) -> bool: ...

    async def stream_events(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        if False:
            yield {"run_id": run_id}


class MockAgentAdapter(AgentAdapter):
    """Deterministic adapter for tests and local demonstrations."""

    def __init__(self, agent_id: str, capabilities: List[str], response: Dict[str, Any]) -> None:
        self.agent_id = agent_id
        self._capabilities = capabilities
        self._response = response
        self.invocations: List[Dict[str, Any]] = []

    async def health(self) -> Dict[str, Any]:
        return {"agent_id": self.agent_id, "status": "ok"}

    async def capabilities(self) -> List[str]:
        return list(self._capabilities)

    async def invoke(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentInvocation:
        self.invocations.append({"task": task, "context": context})
        return AgentInvocation(run_id=f"{self.agent_id}-{len(self.invocations)}", output=dict(self._response))

    async def cancel(self, run_id: str) -> bool:
        return True
