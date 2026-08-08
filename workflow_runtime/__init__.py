"""Phase 5A — Governed Workflow Runtime Foundation.

Deterministic orchestration around nondeterministic intelligence:
SintraPrime controls the process; agents perform bounded computation;
tests verify mechanics; independent evaluators challenge implementation;
governance controls authority; OmniBrain supplies scoped memory;
Mission Control provides visibility; the Principal decides.

DO NOT import or call this package in ways that bypass:
- tenant boundaries
- authorization
- Mission Control command guards
- Principal approval gates
- immutable audit receipts
- capability permissions
- provider governance
- security controls
- existing model routing

No workflow may acquire more authority than the initiating
principal/agent possesses.
"""

from .budgets import BudgetEnvelope, budget_from_spec
from .checkpoint import CheckpointStore
from .models import (
    AcceptanceContract,
    AcceptanceRequirement,
    ContextPackage,
    NodeStatus,
    NodeType,
    WorkflowBudget,
    WorkflowCheckpoint,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeRun,
    WorkflowReceipt,
    WorkflowRun,
    WorkflowStatus,
)
from .node_executor import AgentNodeExecutor, DeterministicExecutor
from .parser import parse_workflow
from .receipts import ReceiptStore
from .registry import WorkflowRegistry, load_defaults
from .retries import CircuitBreaker, RetryPolicy
from .runner import WorkflowRunner
from .state_machine import WorkflowStateMachine
from .validator import validate_workflow

__all__ = [
    "AcceptanceContract",
    "AcceptanceRequirement",
    "AgentNodeExecutor",
    "BudgetGovernor",
    "CheckpointStore",
    "CircuitBreaker",
    "ContextPackage",
    "DeterministicExecutor",
    "NodeStatus",
    "NodeType",
    "ReceiptStore",
    "RetryPolicy",
    "WorkflowBudget",
    "WorkflowCheckpoint",
    "WorkflowDefinition",
    "WorkflowNode",
    "WorkflowNodeRun",
    "WorkflowReceipt",
    "WorkflowRegistry",
    "WorkflowRun",
    "WorkflowRunner",
    "WorkflowStateMachine",
    "WorkflowStatus",
    "load_defaults",
    "parse_workflow",
    "validate_workflow",
]
