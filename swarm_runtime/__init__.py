"""Swarm runtime for SintraPrime/Hermes agent orchestration.

Canonical architecture (corrected ordering):
    Principal
       ↓
    Mission Control
       ↓
    Principal Gateway / Authority
       ↓
    Mission Runtime (orchestration/durable_execution.py)
       ↓
    Collaborative Governance (PR #277 governance layer)
       ↓
    Event Dispatcher / Activation Policy  ← triggers execution
       ↓
    Swarm Controller                      ← sole execution authority
       ↓
    Worker Scheduler
       ├─ Deterministic Tool Worker
       ├─ Model Reasoning Worker (→ SwarmInferenceAdapter → GovernedInferenceRouter)
       ├─ Builder Worker (isolated worktree, file ownership)
       └─ Breaker Worker (independent verification)
            ↓
    GovernedInferenceRouter (canonical provider authority)
            ↓
    Providers / Local Models / Deterministic Tools
            ↓
    Artifact Store
            ↓
    Evidence / Receipt Ledger

Invariants:
    POLICY_BEFORE_EXECUTION = TRUE
    EVENT_DISPATCH != EXECUTION_AUTHORITY
    COLLABORATION != EXECUTION_AUTHORITY
    INTELLIGENCE != AUTHORITY
    PROVIDER_ROUTING_AUTHORITIES = 1 (GovernedInferenceRouter)
"""
from __future__ import annotations

from .artifact_store import ArtifactStore
from .capability_lease import (
    WorkerCapabilityLease,
    build_worker_environment,
    check_secret_inheritance,
)
from .controller import SwarmController, SwarmSummary
from .event_dispatcher import (
    DispatchOutcome,
    EventDispatchStatus,
    EventEnvelope,
    EventPolicyDecision,
    EventPolicyEngine,
    KillSwitchState,
    SwarmActivationAdapter,
)
from .governed_execution import (
    AuthorityEnvelope,
    ExecutionAdmissionGate,
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    Severity,
    WorktreeClaim,
    WorktreeRegistry,
    build_governed_environment,
    check_filesystem_scope,
    make_execution_id,
    redact_secrets,
    terminate_process_tree,
)
from .health_persistence import ProviderHealthStore
from .hermes_adapter import DelegateTask, HermesSwarmAdapter, SwarmResult, is_swarm_eligible
from .inference_adapter import SwarmInferenceAdapter, WorkerInferenceRequest, WorkerInferenceResult
from .network_sandbox import (
    PROXY_ENV_VARS,
    NetworkSandbox,
    NetworkSandboxMode,
)
from .ownership import OwnershipRegistry, OwnershipViolation
from .provider_router import ProviderHealth, ProviderRouter
from .supervisor import Supervisor
from .tool_workers import (
    WORKER_REGISTRY,
    ASTAnalysisWorker,
    BreakerWorker,
    BuilderWorker,
    CodeSearchWorker,
    CrashTestWorker,
    DatabaseSchemaWorker,
    DeliberatelyFlawedBuilderWorker,
    FailoverTestWorker,
    GitDiffWorker,
    IndependentBreakerWorker,
    ModelReasoningWorker,
    StaticAnalysisWorker,
    TestRunnerWorker,
)
from .worker import SwarmEvent, WorkerSpec, WorkerState, WorkerStatus

__version__ = "0.2.0"

__all__ = [
    "PROXY_ENV_VARS",
    "WORKER_REGISTRY",
    "ASTAnalysisWorker",
    "ArtifactStore",
    "AuthorityEnvelope",
    "BreakerWorker",
    "BuilderWorker",
    # Workers
    "CodeSearchWorker",
    "CrashTestWorker",
    "DatabaseSchemaWorker",
    "DelegateTask",
    "DeliberatelyFlawedBuilderWorker",
    "DispatchOutcome",
    "EventDispatchStatus",
    "EventEnvelope",
    "EventPolicyDecision",
    "EventPolicyEngine",
    "ExecutionAdmissionGate",
    "ExecutionClass",
    "ExecutionRequest",
    "ExecutionResult",
    "FailoverTestWorker",
    "GitDiffWorker",
    # Events
    "Governed execution",
    "HermesSwarmAdapter",
    "IndependentBreakerWorker",
    "KillSwitchState",
    "ModelReasoningWorker",
    "NetworkSandbox",
    "NetworkSandboxMode",
    "OwnershipRegistry",
    "OwnershipViolation",
    "ProviderHealth",
    # Health
    "ProviderHealthStore",
    "ProviderRouter",
    "Severity",
    "StaticAnalysisWorker",
    "Supervisor",
    "SwarmActivationAdapter",
    # Core
    "SwarmController",
    "SwarmEvent",
    # Inference
    "SwarmInferenceAdapter",
    "SwarmResult",
    "SwarmSummary",
    "TestRunnerWorker",
    # Security
    "WorkerCapabilityLease",
    "WorkerInferenceRequest",
    "WorkerInferenceResult",
    "WorkerSpec",
    "WorkerState",
    "WorkerStatus",
    "WorktreeClaim",
    "WorktreeRegistry",
    "build_governed_environment",
    "build_worker_environment",
    "check_filesystem_scope",
    "check_secret_inheritance",
    "is_swarm_eligible",
    "make_execution_id",
    "redact_secrets",
    "terminate_process_tree",
]
