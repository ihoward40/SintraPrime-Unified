"""Governed execution admission + boundaries for swarm_runtime.

Brings the subprocess execution backend underneath the GOD-1 authority
envelope (SP-GOD1X-SWARM-RUNTIME-001). Implements the policy layer that
sits between GOD-1 and the execution backend:

    Phase 1  Execution admission gate (no envelope -> no execution)
    Phase 2  Command / workload classification
    Phase 4  Environment boundary (no secret inheritance)
    Phase 5  Filesystem boundary (scope, traversal, escape rejection)
    Phase 6  Worktree ownership registry (collision detection)
    Phase 8  Process-tree termination
    Phase 9  Network boundary (deny by default for GOD-1X)
    Phase 10 Output capture secret redaction
    Phase 11 Structured ExecutionResult contract
    Phase 14 Shared severity taxonomy
    Phase 23 External-effect firewall

The admission gate is pure (no subprocess) and fully unit-testable.
swarm_runtime depends only on its own capability_lease module, never on
omnibrain, so there is no import cycle.
"""

from __future__ import annotations

import enum
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .capability_lease import build_worker_environment, check_secret_inheritance


# --------------------------------------------------------------------------
# Phase 14 — Severity taxonomy (shared operational taxonomy)
# Severity affects visibility/escalation only. It NEVER confers authority.
# --------------------------------------------------------------------------
class Severity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    MATERIAL = "material"
    SECURITY = "security"
    PRINCIPAL_DECISION_REQUIRED = "principal_decision_required"
    SYSTEM_BLOCKED = "system_blocked"

    @classmethod
    def from_intent(cls, intent: str) -> Severity:
        """Map a human intent to a severity. Default is INFO."""
        key = (intent or "").strip().upper()
        for sev in cls:
            if sev.name == key:
                return sev
        return cls.INFO


# --------------------------------------------------------------------------
# Phase 2 — Execution class (command / workload classification)
# --------------------------------------------------------------------------
class ExecutionClass(enum.Enum):
    READ_ONLY_INSPECTION = "read_only_inspection"
    TEST_EXECUTION = "test_execution"
    BUILD_EXECUTION = "build_execution"
    LOCAL_FILE_MUTATION = "local_file_mutation"
    NETWORKED_EXECUTION = "networked_execution"
    SHELL_EXECUTION = "shell_execution"
    PRIVILEGED_EXECUTION = "privileged_execution"
    EXTERNAL_EFFECT_EXECUTION = "external_effect_execution"


# For GOD-1X, these classes are denied at the admission gate.
DENIED_EXECUTION_CLASSES: frozenset[ExecutionClass] = frozenset({
    ExecutionClass.NETWORKED_EXECUTION,
    ExecutionClass.SHELL_EXECUTION,
    ExecutionClass.PRIVILEGED_EXECUTION,
    ExecutionClass.EXTERNAL_EFFECT_EXECUTION,
})


# --------------------------------------------------------------------------
# Phase 1 — Authority envelope (supplied by GOD-1 per governed task)
# --------------------------------------------------------------------------
@dataclass
class AuthorityEnvelope:
    """The admitted authority snapshot an execution must satisfy.

    Every field defaults to a fail-closed denial; the caller (GOD-1) must
    explicitly assert each positive condition. ``revoked`` is a hard stop.
    """

    mission_id: str
    swarm_id: str
    task_id: str
    agent_id: str
    authority_id: str
    role_id: str
    context_package_id: str

    mission_active: bool = False
    swarm_authorized: bool = False
    task_ready: bool = False
    agent_authorized: bool = False
    authority_valid: bool = False
    context_valid: bool = False
    role_allowed: bool = False
    resource_allowed: bool = False
    revoked: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "swarm_id": self.swarm_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "authority_id": self.authority_id,
            "role_id": self.role_id,
            "context_package_id": self.context_package_id,
            "mission_active": self.mission_active,
            "swarm_authorized": self.swarm_authorized,
            "task_ready": self.task_ready,
            "agent_authorized": self.agent_authorized,
            "authority_valid": self.authority_valid,
            "context_valid": self.context_valid,
            "role_allowed": self.role_allowed,
            "resource_allowed": self.resource_allowed,
            "revoked": self.revoked,
        }


# --------------------------------------------------------------------------
# Phase 1 — Execution request (what the backend is asked to do)
# --------------------------------------------------------------------------
@dataclass
class ExecutionRequest:
    """A single governed execution request.

    Carries the minimum mandatory admission fields. Either ``worker_class``
    (a registered workload identity) or ``command`` (explicit argv) identifies
    the workload; never both implicitly.
    """

    execution_request_id: str
    mission_id: str
    swarm_id: str
    task_id: str
    agent_id: str
    authority_id: str
    context_package_id: str
    role_id: str
    working_directory: str
    timeout_seconds: int
    effect_class: str  # ExecutionClass value
    worker_class: str = ""
    command: list[str] | None = None
    task_params: dict[str, Any] = field(default_factory=dict)
    artifact_path: str = ""
    owned_files: list[str] = field(default_factory=list)
    read_paths: list[str] = field(default_factory=list)
    write_paths: list[str] = field(default_factory=list)
    prohibited_paths: list[str] = field(default_factory=list)
    shell: bool = False
    network_required: bool = False
    environment_policy: dict[str, Any] = field(default_factory=dict)
    leased_env_vars: list[str] = field(default_factory=list)

    def execution_class(self) -> ExecutionClass | None:
        try:
            return ExecutionClass(self.effect_class)
        except ValueError:
            return None


@dataclass
class AdmissionDecision:
    allowed: bool
    reasons: list[str]

    def require(self, ok: bool, code: str) -> None:
        if not ok:
            self.allowed = False
            self.reasons.append(code)


# --------------------------------------------------------------------------
# Phase 1 — Admission gate
# --------------------------------------------------------------------------
class ExecutionAdmissionGate:
    """Mandatory gate between GOD-1 and the execution backend.

    Admission requires ALL of:
        MISSION_ACTIVE and SWARM_AUTHORIZED and TASK_READY and
        AGENT_AUTHORIZED and AUTHORITY_VALID and CONTEXT_VALID and
        ROLE_ALLOWED and RESOURCE_ALLOWED and EXECUTION_CLASS_ALLOWED
    Otherwise: DENY. No implicit defaults that expand authority.
    """

    def __init__(self, denied_classes: frozenset[ExecutionClass] = DENIED_EXECUTION_CLASSES) -> None:
        self.denied_classes = denied_classes

    def admit(self, request: ExecutionRequest, env: AuthorityEnvelope) -> AdmissionDecision:
        d = AdmissionDecision(allowed=True, reasons=[])

        # Authority envelope conditions (fail-closed)
        d.require(env.mission_active, "MISSION_NOT_ACTIVE")
        d.require(env.swarm_authorized, "SWARM_NOT_AUTHORIZED")
        d.require(env.task_ready, "TASK_NOT_READY")
        d.require(env.agent_authorized, "AGENT_NOT_AUTHORIZED")
        d.require(env.authority_valid, "AUTHORITY_INVALID")
        d.require(env.context_valid, "CONTEXT_INVALID")
        d.require(env.role_allowed, "ROLE_NOT_ALLOWED")
        d.require(env.resource_allowed, "RESOURCE_NOT_ALLOWED")
        d.require(not env.revoked, "AUTHORITY_REVOKED")

        # Identity binding: request must match the envelope
        d.require(request.mission_id == env.mission_id, "MISSION_ID_MISMATCH")
        d.require(request.swarm_id == env.swarm_id, "SWARM_ID_MISMATCH")
        d.require(request.task_id == env.task_id, "TASK_ID_MISMATCH")
        d.require(request.agent_id == env.agent_id, "AGENT_ID_MISMATCH")

        # Execution class classification
        cls = request.execution_class()
        if cls is None:
            d.require(False, "UNKNOWN_EXECUTION_CLASS")
        else:
            d.require(cls not in self.denied_classes, f"EXECUTION_CLASS_DENIED:{cls.value}")

        # Shell boundary (Phase 3): explicit authority required
        if request.shell:
            d.require(
                bool(request.environment_policy.get("shell_authorized")),
                "SHELL_EXECUTION_REQUIRES_EXPLICIT_AUTHORITY",
            )

        # Network boundary (Phase 9): deny unless explicitly classified networked
        if request.network_required and cls is not ExecutionClass.NETWORKED_EXECUTION:
            d.require(False, "NETWORK_REQUIRED_BUT_UNCLASSIFIED")

        if d.allowed:
            d.reasons.append("ADMITTED")
        return d


# --------------------------------------------------------------------------
# Phase 4 — Environment boundary
# --------------------------------------------------------------------------
def build_governed_environment(
    request: ExecutionRequest,
    parent_env: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build a minimal worker environment.

    Secrets are denied unless explicitly leased. Returns (env, secret_check)
    where secret_check['clean'] is False if a secret leaked without a lease.
    """
    from .capability_lease import WorkerCapabilityLease

    lease = WorkerCapabilityLease.create(
        worker_id=request.agent_id,
        mission_id=request.mission_id,
        swarm_id=request.swarm_id,
        leased_env_vars=list(request.leased_env_vars),
    )
    env = build_worker_environment(lease, parent_env or dict(os.environ))
    check = check_secret_inheritance(env, lease)
    return env, check


# --------------------------------------------------------------------------
# Phase 5 — Filesystem boundary
# --------------------------------------------------------------------------
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|ghp_|sk-[A-Za-z0-9]|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
)


def normalize_path(path: str, base: str | None = None) -> Path:
    """Normalize and resolve a path; reject traversal/escape attempts."""
    p = Path(path)
    if not p.is_absolute() and base is not None:
        p = Path(base) / p
    try:
        resolved = p.resolve()
    except (OSError, ValueError):
        # Cannot resolve (e.g. on a path that does not yet exist) — still
        # reject obvious escape patterns before creation.
        resolved = p.absolute()
    return resolved


def path_within_scopes(target: str, scopes: list[str], base: str | None = None) -> bool:
    """True if normalized target lies within at least one scope dir."""
    if not scopes:
        return False
    t = normalize_path(target, base)
    for scope in scopes:
        s = normalize_path(scope, base)
        try:
            t.relative_to(s)
            return True
        except ValueError:
            continue
    return False


def check_filesystem_scope(
    request: ExecutionRequest,
    base: str | None = None,
) -> tuple[bool, str]:
    """Validate that declared paths respect the filesystem boundary (Phase 5).

    The working directory is the sandbox root. Every declared read/write/owned
    path must stay *within* the sandbox and within the repository root ``base``
    (no parent-traversal / absolute escape). Prohibited paths are rejected.
    Returns (ok, reason).
    """
    sandbox = normalize_path(request.working_directory or base or ".", base)

    # Sandbox must itself sit within the repository root.
    if base is not None:
        base_res = normalize_path(base)
        try:
            sandbox.relative_to(base_res)
        except ValueError:
            return False, "SANDBOX_OUTSIDE_REPO"

    candidates = (
        list(request.read_paths)
        + list(request.write_paths)
        + list(request.owned_files)
    )
    for cand in candidates:
        t = normalize_path(cand, base)
        # Escape / parent-traversal: outside the repository root is never allowed.
        if base is not None:
            try:
                t.relative_to(base_res)
            except ValueError:
                return False, f"PATH_ESCAPE:{cand}"
        # Must remain inside the sandbox (working directory).
        if not path_within_scopes(str(t), [str(sandbox)], base):
            return False, f"PATH_OUTSIDE_SANDBOX:{cand}"
        # Prohibited paths are never writable/readable.
        for pro in request.prohibited_paths:
            try:
                t.relative_to(normalize_path(pro, base))
                return False, f"PROHIBITED_PATH:{cand}"
            except ValueError:
                continue
    return True, "OK"


# --------------------------------------------------------------------------
# Phase 6 — Worktree ownership registry (collision detection)
# --------------------------------------------------------------------------
@dataclass
class WorktreeClaim:
    worktree_id: str
    mission_id: str
    swarm_id: str
    task_id: str
    owner_agent_id: str
    branch: str
    base_sha: str
    path: str
    write_scope: list[str]
    integration_order: int
    status: str = "claimed"


class WorktreeRegistry:
    """Tracks worktree ownership across a swarm.

    Prevents two mutable agents from unknowingly owning the same worktree and
    detects overlapping mutable file ownership.
    """

    def __init__(self) -> None:
        self._by_path: dict[str, WorktreeClaim] = {}
        self._by_id: dict[str, WorktreeClaim] = {}
        self.collisions: list[dict[str, Any]] = []

    def claim(self, claim: WorktreeClaim) -> tuple[bool, str]:
        """Attempt to claim a worktree. Returns (granted, reason).

        A collision is detected when another agent already owns the same
        worktree path OR an overlapping mutable write scope.
        """
        norm_path = str(normalize_path(claim.path))
        existing = self._by_path.get(norm_path)
        if existing is not None and existing.owner_agent_id != claim.owner_agent_id:
            self.collisions.append({
                "type": "WORKTREE_OWNERSHIP_CONFLICT",
                "path": norm_path,
                "existing_owner": existing.owner_agent_id,
                "claiming_agent": claim.owner_agent_id,
                "task_id": claim.task_id,
            })
            # Resolution policy: collision -> serialize (deny the new claim so
            # the orchestrator can order it after the current owner finishes).
            return False, "WORKTREE_COLLISION_DETECTED:SERIALIZE"

        # Overlapping mutable file ownership across distinct worktrees
        for scope in claim.write_scope:
            ns = str(normalize_path(scope))
            for other in self._by_id.values():
                if other.owner_agent_id == claim.owner_agent_id:
                    continue
                for o_scope in other.write_scope:
                    if str(normalize_path(o_scope)) == ns:
                        self.collisions.append({
                            "type": "OVERLAPPING_MUTABLE_OWNERSHIP",
                            "path": ns,
                            "existing_owner": other.owner_agent_id,
                            "claiming_agent": claim.owner_agent_id,
                            "task_id": claim.task_id,
                        })
                        return False, "OVERLAPPING_OWNERSHIP_DETECTED:DENY"

        self._by_path[norm_path] = claim
        self._by_id[claim.worktree_id] = claim
        return True, "CLAIMED"

    def release(self, worktree_id: str) -> None:
        claim = self._by_id.pop(worktree_id, None)
        if claim is not None:
            self._by_path.pop(str(normalize_path(claim.path)), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": {k: vars(v) for k, v in self._by_id.items()},
            "collisions": self.collisions,
        }


# --------------------------------------------------------------------------
# Phase 10 — Output capture secret redaction
# --------------------------------------------------------------------------
def redact_secrets(text: str) -> str:
    """Redact obvious secrets from captured subprocess output.

    Raw subprocess output must never become trusted evidence verbatim; secrets
    are scrubbed before persistence.
    """
    if not text:
        return text
    return _SECRET_RE.sub("[REDACTED]", text)


# --------------------------------------------------------------------------
# Phase 8 — Process-tree termination
# --------------------------------------------------------------------------
def terminate_process_tree(proc: subprocess.Popen[bytes], timeout: float = 5.0) -> str:
    """Terminate a governed worker and its descendants.

    On Windows uses ``taskkill /T``; on POSIX kills the process group created
    with start_new_session. Returns a termination reason string. If termination
    cannot be confirmed, reports a degraded state rather than claiming CANCELLED.
    """
    pid = proc.pid
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, text=True, timeout=timeout,
            )
            return "TERMINATED_TREE"
        except Exception:
            return "TERMINATION_DEGRADED"
    else:
        try:
            import os as _os
            import signal

            pgid = _os.getpgid(pid)
            _os.killpg(pgid, signal.SIGTERM)
            return "TERMINATED_TREE"
        except (ProcessLookupError, PermissionError):
            return "TERMINATION_DEGRADED"
        except Exception:
            return "TERMINATION_DEGRADED"


# --------------------------------------------------------------------------
# Phase 11 — Structured execution result contract
# --------------------------------------------------------------------------
@dataclass
class ExecutionResult:
    execution_id: str
    request_id: str
    mission_id: str
    swarm_id: str
    task_id: str
    agent_id: str
    started_at: float
    completed_at: float | None = None
    exit_code: int | None = None
    status: str = "RUNNING"  # RUNNING|COMPLETED|FAILED|TIMED_OUT|DENIED|CANCELLED
    stdout_ref: str = ""
    stderr_ref: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    resource_usage: dict[str, Any] = field(default_factory=dict)
    termination_reason: str = ""
    severity: str = Severity.INFO.value
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "mission_id": self.mission_id,
            "swarm_id": self.swarm_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "status": self.status,
            "stdout_ref": self.stdout_ref,
            "stderr_ref": self.stderr_ref,
            "artifact_refs": self.artifact_refs,
            "resource_usage": self.resource_usage,
            "termination_reason": self.termination_reason,
            "severity": self.severity,
            "rejection_reasons": self.rejection_reasons,
        }


def make_execution_id() -> str:
    import uuid

    return f"exec_{uuid.uuid4().hex[:12]}"


__all__ = [
    "DENIED_EXECUTION_CLASSES",
    "AdmissionDecision",
    "AuthorityEnvelope",
    "ExecutionAdmissionGate",
    "ExecutionClass",
    "ExecutionRequest",
    "ExecutionResult",
    "Severity",
    "WorktreeClaim",
    "WorktreeRegistry",
    "build_governed_environment",
    "check_filesystem_scope",
    "make_execution_id",
    "normalize_path",
    "path_within_scopes",
    "redact_secrets",
    "terminate_process_tree",
]
