"""AgentHandoff — structured agent-to-agent task transfer."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import HandoffStatus


@dataclass
class AgentHandoff:
    """Structured handoff between agents (directive §XXVIII)."""

    handoff_id: str
    source_agent: str
    target_agent: str
    channel_id: str
    tenant_id: str
    task: str = ""
    input_artifacts: list[str] = field(default_factory=list)
    expected_output_schema: str = ""
    deadline: str = ""
    budget: dict = field(default_factory=dict)
    status: HandoffStatus = HandoffStatus.PENDING
    result_artifacts: list[str] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""
    correlation_id: str = ""
    workflow_run_id: str = ""
    metadata: dict = field(default_factory=dict)
