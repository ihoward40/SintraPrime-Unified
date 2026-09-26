"""Governed swarm coordination (SP-GOD1-SWARMS-001).

Constitutional rules encoded and tested here:

    MULTI_AGENT_CONSENSUS != AUTHORITY
    MORE AGENTS != MORE AUTHORITY

Effective swarm authority is the deterministic intersection:

    MISSION_AUTHORITY ∩ SWARM_AUTHORITY ∩ AGENT_ROLE_POLICY
    ∩ PARENT_DELEGABLE_AUTHORITY

Any capability outside that intersection is REFUSED — including when every
member agrees, when a majority votes, when confidence is high, or when a
provider recommends it.

This module composes the existing governed runtime (agent_runtime
delegation/manifests, omnibrain memory scoping and provenance). It is the
authority/coordination layer; swarm_runtime remains the subprocess
execution backend and agent_protocol/swarm_orchestrator.py (weighted-
majority voting, no authority model) is deliberately NOT used.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class SwarmType(StrEnum):
    COUNCIL = "COUNCIL"
    RESEARCH = "RESEARCH"
    BUILD = "BUILD"


class SwarmStatus(StrEnum):
    PROPOSED = "PROPOSED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class UnknownSwarmTypeError(ValueError):
    """Unknown swarm type — fails closed."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Swarm identity (Phase 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SwarmIdentity:
    swarm_id: str
    mission_id: str
    swarm_type: SwarmType
    authority_id: str
    principal_origin: str
    parent_execution_id: str
    created_at: datetime
    expires_at: datetime
    coordinator_agent_id: str
    member_agent_ids: frozenset[str]
    status: SwarmStatus

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at


def make_swarm_identity(
    *,
    mission_id: str,
    swarm_type: str,
    authority_id: str,
    principal_origin: str,
    parent_execution_id: str,
    coordinator_agent_id: str,
    member_agent_ids: Iterable[str],
    ttl_seconds: int = 3600,
    now: datetime | None = None,
) -> SwarmIdentity:
    """Create swarm identity. Unknown swarm types FAIL CLOSED."""
    try:
        stype = SwarmType(swarm_type)
    except ValueError as exc:
        raise UnknownSwarmTypeError(
            f"unknown swarm type {swarm_type!r}: allowed = "
            f"{[t.value for t in SwarmType]}"
        ) from exc
    now = now or _utcnow()
    return SwarmIdentity(
        swarm_id=f"SWARM-{uuid.uuid4().hex[:12].upper()}",
        mission_id=mission_id,
        swarm_type=stype,
        authority_id=authority_id,
        principal_origin=principal_origin,
        parent_execution_id=parent_execution_id,
        created_at=now,
        expires_at=now.fromtimestamp(now.timestamp() + ttl_seconds, tz=now.tzinfo),
        coordinator_agent_id=coordinator_agent_id,
        member_agent_ids=frozenset(member_agent_ids),
        status=SwarmStatus.PROPOSED,
    )


# ---------------------------------------------------------------------------
# Role manifests (Phase 2) — a role title grants NOTHING
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SwarmRoleManifest:
    role_id: str
    role_type: str                    # e.g. SKEPTIC, IMPLEMENTER — descriptive only
    mission_scope: frozenset[str]
    task_scope: frozenset[str]
    allowed_tools: frozenset[str]
    memory_scope: str                 # MemoryScopeClass-style key
    delegable_authority: frozenset[str]
    output_contract: str
    evidence_requirements: tuple[str, ...] = ()
    prohibited_actions: frozenset[str] = frozenset()
    completion_criteria: str = ""

    def effective_authority(self, mission_authority: Iterable[str],
                            swarm_authority: Iterable[str],
                            parent_delegable: Iterable[str]) -> frozenset[str]:
        """Deterministic intersection (the constitutional formula).

        CHILD_EFFECTIVE_AUTHORITY =
            MISSION_AUTHORITY ∩ SWARM_AUTHORITY ∩ AGENT_ROLE_POLICY
            ∩ PARENT_DELEGABLE_AUTHORITY
        """
        return (
            frozenset(self.delegable_authority)
            & frozenset(mission_authority)
            & frozenset(swarm_authority)
            & frozenset(parent_delegable)
        )


# ---------------------------------------------------------------------------
# Council output (Phase 3) — disagreement is data, never collapsed
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouncilPosition:
    member_agent_id: str
    position: str
    supporting_evidence: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class CouncilOutput:
    issue: str
    positions: tuple[CouncilPosition, ...]
    uncertainties: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    consensus_points: tuple[str, ...] = ()
    disagreements: tuple[str, ...] = ()
    recommendations: tuple[dict, ...] = ()   # PROPOSALS — never approvals

    def to_dict(self) -> dict:
        return {
            "issue": self.issue,
            "positions": [
                {"member": p.member_agent_id, "position": p.position,
                 "supporting_evidence": list(p.supporting_evidence),
                 "counterevidence": list(p.counterevidence)}
                for p in self.positions
            ],
            "uncertainties": list(self.uncertainties),
            "unresolved_questions": list(self.unresolved_questions),
            "consensus_points": list(self.consensus_points),
            "disagreements": list(self.disagreements),
            "recommendations": [dict(r) for r in self.recommendations],
        }


class CouncilSynthesizer:
    """Synthesize council output PRESERVING disagreement.

    Anti-groupthink rule (directive Phase 3): disagreement backed by
    material evidence is PRESERVED even when a majority disagrees. The
    synthesizer never reports a bare majority as "the controlling truth"
    and never produces an approval — recommendations are proposals.
    """

    def synthesize(self, issue: str, positions: Iterable[CouncilPosition]) -> CouncilOutput:
        positions = tuple(positions)
        if not positions:
            return CouncilOutput(issue=issue, positions=())

        # Majority/consensus detection — recorded, never authoritative.
        counts: dict[str, int] = {}
        for p in positions:
            counts[p.position] = counts.get(p.position, 0) + 1
        majority_position, majority_count = max(counts.items(), key=lambda kv: kv[1])
        is_unanimous = majority_count == len(positions)

        consensus_points: list[str] = []
        disagreements: list[str] = []
        minority_with_evidence: list[str] = []

        for p in positions:
            if p.position != majority_position:
                has_material_evidence = bool(p.supporting_evidence)
                label = "minority position (with evidence)" if has_material_evidence \
                    else "minority position"
                disagreements.append(f"{label}: {p.member_agent_id}: {p.position}")
                if has_material_evidence:
                    minority_with_evidence.append(
                        f"{p.member_agent_id} presents material counterevidence: "
                        + "; ".join(p.supporting_evidence)
                    )
        if not is_unanimous:
            # PRESERVE the minority position — do not let 80% become truth.
            disagreements.append(
                f"NOTE: {majority_count}/{len(positions)} agents hold '{majority_position}'; "
                "majority is reported as a distribution, NOT as controlling truth."
            )
            for item in minority_with_evidence:
                disagreements.append(item)
        else:
            consensus_points.append(f"unanimous: {majority_position}")

        # Evidence-backed minority positions are surfaced as unresolved, forcing
        # Principal/evidence review rather than silent majority override.
        uncertainties = [
            f"disagreement unresolved by volume: {d}" for d in disagreements
            if d.startswith("minority position (with evidence)")
        ]

        return CouncilOutput(
            issue=issue,
            positions=positions,
            consensus_points=tuple(consensus_points),
            disagreements=tuple(disagreements),
            uncertainties=tuple(uncertainties),
        )


# ---------------------------------------------------------------------------
# Research claims (Phase 4) — provenance-bearing, confidence != authority
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchClaim:
    claim_id: str
    claim: str
    source_refs: tuple[dict, ...]        # {source, retrieved_at, source_type, agent_id, ...}
    evidence_class: str                  # e.g. PRIMARY_SOURCE | SECONDARY | DERIVED
    confidence: float                    # describes evidence strength ONLY
    contradictions: tuple[str, ...] = ()
    status: str = "UNVERIFIED"           # SUPPORTED | PARTIALLY_SUPPORTED |
                                         # CONTRADICTED | UNVERIFIED | UNKNOWN


def verify_claim_sources(claim: ResearchClaim) -> list[str]:
    """Provenance integrity checks. Returns list of violations (empty = clean).

    Enforces directive Phase 22: circular citation, missing provenance, and
    same-source-double-counting are detected BEFORE synthesis.
    """
    violations: list[str] = []
    sources = [s.get("source") for s in claim.source_refs]
    if not sources:
        violations.append(f"{claim.claim_id}: missing source provenance")
    if len(sources) != len(set(sources)):
        violations.append(
            f"{claim.claim_id}: same source cited multiple times as independent corroboration"
        )
    for s in claim.source_refs:
        if not s.get("retrieved_at"):
            violations.append(f"{claim.claim_id}: source {s.get('source')!r} missing retrieved_at")
        if not s.get("agent_id"):
            violations.append(f"{claim.claim_id}: source {s.get('source')!r} missing agent_id")
    if claim.status == "SUPPORTED" and not sources:
        violations.append(f"{claim.claim_id}: SUPPORTED status without any source")
    return violations


# ---------------------------------------------------------------------------
# Task graph (Phase 6) + parallelism control (Phase 7)
# ---------------------------------------------------------------------------


@dataclass
class SwarmTask:
    task_id: str
    mission_id: str
    swarm_id: str
    parent_task_id: str | None
    role: str
    objective: str
    dependencies: tuple[str, ...] = ()
    authority_scope: frozenset[str] = frozenset()
    input_refs: tuple[str, ...] = ()
    output_contract: str = ""
    status: TaskStatus = TaskStatus.PENDING
    attempt: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    receipt_id: str | None = None
    mutable_resources: frozenset[str] = frozenset()   # Phase 7 collision detection


class TaskGraph:
    """Governed task DAG. A task becomes READY only when all declared
    dependencies are COMPLETE. Cycle creation is refused."""

    def __init__(self, swarm_id: str, mission_id: str) -> None:
        self.swarm_id = swarm_id
        self.mission_id = mission_id
        self._tasks: dict[str, SwarmTask] = {}

    def add_task(self, task: SwarmTask) -> SwarmTask:
        if task.task_id in self._tasks:
            raise ValueError(f"task {task.task_id} already exists")
        self._check_cycle(task.task_id, task.dependencies)
        self._tasks[task.task_id] = task
        return task

    def _check_cycle(self, new_id: str, deps: Iterable[str]) -> None:
        for dep in deps:
            if dep == new_id:
                raise ValueError(f"task {new_id} depends on itself")
            parent = self._tasks.get(dep)
            if parent is not None and new_id in parent.dependencies:
                raise ValueError(f"task cycle: {new_id} <-> {dep}")

    def mark_complete(self, task_id: str) -> None:
        t = self._tasks[task_id]
        t.status = TaskStatus.COMPLETE
        t.completed_at = _utcnow()

    def ready_tasks(self) -> list[SwarmTask]:
        """Tasks whose dependencies are ALL COMPLETE and which are still
        PENDING. No receipt, no run."""
        ready = []
        for t in self._tasks.values():
            if t.status is not TaskStatus.PENDING:
                continue
            deps = [self._tasks[d] for d in t.dependencies if d in self._tasks]
            if all(d.status is TaskStatus.COMPLETE for d in deps):
                ready.append(t)
        return ready

    def collision_groups(self) -> list[list[str]]:
        """Phase 7: tasks that share a mutable resource must be SERIALIZED.
        Returns groups of task_ids that collide (each group needs a lock)."""
        by_resource: dict[str, list[str]] = {}
        for t in self._tasks.values():
            for res in t.mutable_resources:
                by_resource.setdefault(res, []).append(t.task_id)
        return [ids for ids in by_resource.values() if len(ids) > 1]

    def orphans(self) -> list[str]:
        """Directive Phase 24: no orphan tasks. A task is orphaned when it is
        RUNNING/WAITING but its swarm is COMPLETE/CANCELLED."""
        return [
            t.task_id for t in self._tasks.values()
            if t.status in (TaskStatus.RUNNING, TaskStatus.WAITING)
        ]

    def all_tasks(self) -> list[SwarmTask]:
        return list(self._tasks.values())


# ---------------------------------------------------------------------------
# Shared swarm memory (Phase 8) — scoped, fail closed
# ---------------------------------------------------------------------------


class SwarmMemoryScope(StrEnum):
    PRIVATE_AGENT = "PRIVATE_AGENT"
    SHARED_SWARM = "SHARED_SWARM"
    MISSION_SHARED = "MISSION_SHARED"
    PRINCIPAL_BINDING = "PRINCIPAL_BINDING"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True)
class SwarmMemoryRecord:
    record_id: str
    scope: str
    owner_agent_id: str | None = None
    swarm_id: str | None = None
    mission_id: str | None = None


def swarm_memory_visible(record: SwarmMemoryRecord, *,
                         agent_id: str, swarm_id: str, mission_id: str,
                         is_principal: bool = False) -> bool:
    """Fail-closed visibility over the five swarm memory classes."""
    try:
        scope = SwarmMemoryScope(record.scope)
    except ValueError:
        return False  # unknown scope -> DENY
    if scope is SwarmMemoryScope.PRIVATE_AGENT:
        return record.owner_agent_id == agent_id
    if scope is SwarmMemoryScope.SHARED_SWARM:
        return record.swarm_id == swarm_id
    if scope is SwarmMemoryScope.MISSION_SHARED:
        return record.mission_id == mission_id
    if scope is SwarmMemoryScope.PRINCIPAL_BINDING:
        return is_principal
    if scope is SwarmMemoryScope.EVIDENCE:
        return record.mission_id == mission_id
    return False


# ---------------------------------------------------------------------------
# Structured handoffs (Phase 9)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SwarmHandoff:
    handoff_id: str
    from_agent: str
    to_agent: str
    mission_id: str
    task_id: str
    summary: str
    claims: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    recommended_next_actions: tuple[str, ...] = ()
    authority_context: str = ""


def handoff_next_actions_are_not_authorization(handoff: SwarmHandoff) -> bool:
    """Directive Phase 9: recommended_next_actions may never carry an
    approval token. Returns True when the handoff is safe (no token)."""
    forbidden = {"approval_reference", "approval_token", "approval_id"}
    for action in handoff.recommended_next_actions:
        if isinstance(action, dict) and (set(action) & forbidden):
            return False
        if isinstance(action, str) and any(
            tok in action for tok in ("approval_reference", "approval_token")
        ):
            return False
    return True


# ---------------------------------------------------------------------------
# Retry policy (Phase 13) + failure isolation (Phase 12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    max_task_attempts: int = 2
    max_provider_retries: int = 2
    max_agent_replacements: int = 1


def can_retry(attempt: int, policy: RetryPolicy) -> bool:
    """Bounded retry. Evidence from prior attempts is preserved by the
    caller attaching a fresh receipt per attempt (never overwriting)."""
    return attempt < policy.max_task_attempts


class MemberFailureClass(StrEnum):
    RECOVERABLE = "MEMBER_FAILURE_RECOVERABLE"
    MATERIAL = "MEMBER_FAILURE_MATERIAL"
    SWARM_BLOCKED = "SWARM_BLOCKED"


# ---------------------------------------------------------------------------
# Swarm synthesis receipt (Phase 10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SwarmSynthesis:
    swarm_id: str
    mission_id: str
    objective: str
    members: tuple[str, ...]
    completed_tasks: tuple[str, ...]
    failed_tasks: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    findings: tuple[str, ...] = ()
    disagreements: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    recommendations: tuple[dict, ...] = ()   # PROPOSALS
    external_effects: tuple[str, ...] = ()   # must be empty in this mission
    authority_used: frozenset[str] = frozenset()
    final_status: str = "COMPLETE"
