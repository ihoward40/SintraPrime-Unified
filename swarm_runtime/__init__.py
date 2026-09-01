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
    EventDispatcher,
    EventDispatchStatus,
    EventEnvelope,
    EventPolicyDecision,
    EventPolicyEngine,
    KillSwitchState,
    SwarmActivationAdapter,
)
from .health_persistence import ProviderHealthStore
from .inference_adapter import SwarmInferenceAdapter, WorkerInferenceRequest, WorkerInferenceResult
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
    "WORKER_REGISTRY",
    "ASTAnalysisWorker",
    "ArtifactStore",
    "BreakerWorker",
    "BuilderWorker",
    # Workers
    "CodeSearchWorker",
    "CrashTestWorker",
    "DatabaseSchemaWorker",
    "DeliberatelyFlawedBuilderWorker",
    "DispatchOutcome",
    "EventDispatchStatus",
    # Events
    "EventDispatcher",
    "EventEnvelope",
    "EventPolicyDecision",
    "EventPolicyEngine",
    "FailoverTestWorker",
    "GitDiffWorker",
    "IndependentBreakerWorker",
    "KillSwitchState",
    "ModelReasoningWorker",
    "OwnershipRegistry",
    "OwnershipViolation",
    "ProviderHealth",
    # Health
    "ProviderHealthStore",
    "ProviderRouter",
    "StaticAnalysisWorker",
    "Supervisor",
    "SwarmActivationAdapter",
    # Core
    "SwarmController",
    "SwarmEvent",
    # Inference
    "SwarmInferenceAdapter",
    "SwarmSummary",
    "TestRunnerWorker",
    # Security
    "WorkerCapabilityLease",
    "WorkerInferenceRequest",
    "WorkerInferenceResult",
    "WorkerSpec",
    "WorkerState",
    "WorkerStatus",
    "build_worker_environment",
    "check_secret_inheritance",
]
