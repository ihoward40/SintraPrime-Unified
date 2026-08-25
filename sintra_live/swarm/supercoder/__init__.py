"""SuperCoder Swarm Runtime V2 — durable coding missions that survive worker timeouts.

Core invariant: WORKER_TIMEOUT != MISSION_TIMEOUT
A worker may die at any time. The mission never loses progress.
"""
from __future__ import annotations

from .mission import (
    CodingMission,
    MissionPhase,
    MissionStatus,
)
from .checkpoint import (
    Checkpoint,
    CheckpointStore,
    CheckpointSequence,
)
from .work_packet import (
    WorkPacket,
    PacketStatus,
    PacketScheduler,
)
from .context_capsule import ContextCapsule
from .path_locks import PathLock, PathLockRegistry
from .role_registry import (
    SuperCoderRole,
    QualityLevel,
    RoleRegistry,
)
from .recovery import (
    TimeoutRecovery,
    RecoveryState,
    RecoveryEngine,
)
from .rotation import WorkerRotation
from .supervisor import SuperCoderSupervisor
from .certification import CertificationChain

__all__ = [
    "CodingMission",
    "MissionPhase",
    "MissionStatus",
    "Checkpoint",
    "CheckpointStore",
    "CheckpointSequence",
    "WorkPacket",
    "PacketStatus",
    "PacketScheduler",
    "ContextCapsule",
    "PathLock",
    "PathLockRegistry",
    "SuperCoderRole",
    "QualityLevel",
    "RoleRegistry",
    "TimeoutRecovery",
    "RecoveryState",
    "RecoveryEngine",
    "WorkerRotation",
    "SuperCoderSupervisor",
    "CertificationChain",
]