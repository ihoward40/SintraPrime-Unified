"""Worker capability leases and environment security.

Workers must NOT inherit the controller's entire environment.
Secrets are denied unless explicitly leased via a capability lease.

Default: DENY_UNDECLARED_CAPABILITY = TRUE
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# Default environment allowlist for worker subprocesses
DEFAULT_ENV_ALLOWLIST: frozenset[str] = frozenset({
    "PATH",
    "PYTHONPATH",
    "PYTHONUNBUFFERED",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LOCALAPPDATA",
    "APPDATA",
    "USERPROFILE",
    "HOME",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "OS",
    "LANG",
    "LC_ALL",
})

# Secrets that must NEVER be automatically propagated
DENIED_SECRETS: frozenset[str] = frozenset({
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "STRIPE_SECRET_KEY",
    "STRIPE_API_KEY",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "JWT_SECRET_KEY",
    "SECRET_KEY",
    "ENCRYPTION_KEY",
    "TWIN_AUTH_TOKEN",
    "HERMES_API_KEY",
})

# Patterns for denied secret prefixes
DENIED_SECRET_PATTERNS: tuple[str, ...] = (
    "AWS_", "GOOGLE_", "STRIPE_", "GITHUB_", "ANTHROPIC_", "OPENAI_",
    "POSTGRES_", "REDIS_", "JWT_", "DATABASE_", "ENCRYPTION_",
)


@dataclass
class WorkerCapabilityLease:
    """Ephemeral scoped capability grant for a worker.

    A worker may only access what its lease explicitly permits.
    DENY_UNDECLARED_CAPABILITY = TRUE by default.
    """
    lease_id: str
    worker_id: str
    tenant_id: str = ""
    principal_id: str = ""
    mission_id: str = ""
    run_id: str = ""
    swarm_id: str = ""

    # Allowed scope
    allowed_tools: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    allowed_network: bool = False
    allowed_provider_classes: list[str] = field(default_factory=list)

    # Explicitly leased secrets (must be justified)
    leased_env_vars: list[str] = field(default_factory=list)

    # Lifecycle
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = no expiry
    revoked: bool = False

    @classmethod
    def create(
        cls,
        worker_id: str,
        *,
        tenant_id: str = "",
        principal_id: str = "",
        mission_id: str = "",
        run_id: str = "",
        swarm_id: str = "",
        allowed_tools: list[str] | None = None,
        allowed_paths: list[str] | None = None,
        allowed_network: bool = False,
        allowed_provider_classes: list[str] | None = None,
        leased_env_vars: list[str] | None = None,
        ttl_seconds: float = 300.0,
    ) -> WorkerCapabilityLease:
        return cls(
            lease_id=f"lease_{uuid.uuid4().hex[:12]}",
            worker_id=worker_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            mission_id=mission_id,
            run_id=run_id,
            swarm_id=swarm_id,
            allowed_tools=allowed_tools or [],
            allowed_paths=allowed_paths or [],
            allowed_network=allowed_network,
            allowed_provider_classes=allowed_provider_classes or [],
            leased_env_vars=leased_env_vars or [],
            expires_at=time.time() + ttl_seconds if ttl_seconds > 0 else 0.0,
        )

    def is_expired(self) -> bool:
        if self.expires_at == 0.0:
            return False
        return time.time() > self.expires_at

    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired()

    def can_access_path(self, path: str) -> bool:
        """Check if a path is within the lease's allowed paths."""
        if not self.allowed_paths:
            return False
        return any(path.startswith(allowed) for allowed in self.allowed_paths)

    def can_use_tool(self, tool: str) -> bool:
        return tool in self.allowed_tools

    def to_dict(self) -> dict:
        return {
            "lease_id": self.lease_id,
            "worker_id": self.worker_id,
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "swarm_id": self.swarm_id,
            "allowed_tools": self.allowed_tools,
            "allowed_paths": self.allowed_paths,
            "allowed_network": self.allowed_network,
            "allowed_provider_classes": self.allowed_provider_classes,
            "leased_env_vars": self.leased_env_vars,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
        }


def build_worker_environment(
    lease: WorkerCapabilityLease,
    parent_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a minimal environment for a worker subprocess.

    Only allowlisted variables are propagated.
    Secrets are denied unless explicitly leased.
    """
    parent_env = parent_env or dict(os.environ)
    worker_env: dict[str, str] = {}

    # Propagate allowlisted variables
    for key in DEFAULT_ENV_ALLOWLIST:
        if key in parent_env:
            worker_env[key] = parent_env[key]

    # Add explicitly leased variables (must be in parent env)
    for key in lease.leased_env_vars:
        if key in parent_env:
            # Verify it's not in the denied list unless explicitly leased
            worker_env[key] = parent_env[key]

    return worker_env


def check_secret_inheritance(
    env: dict[str, str],
    lease: WorkerCapabilityLease | None = None,
) -> dict[str, Any]:
    """Verify no secrets leaked into worker environment without lease.

    Returns:
        {"clean": bool, "leaked": list[str]}
    """
    leaked: list[str] = []
    leased_keys = set(lease.leased_env_vars) if lease else set()

    for key in env:
        if key in DENIED_SECRETS and key not in leased_keys:
            leaked.append(key)
        elif any(key.startswith(pat) for pat in DENIED_SECRET_PATTERNS):
            if key not in leased_keys and key not in DEFAULT_ENV_ALLOWLIST:
                leaked.append(key)

    return {
        "clean": len(leaked) == 0,
        "leaked": leaked,
        "SWARM_SECRET_INHERITANCE_DEFAULT": "DENIED" if len(leaked) == 0 else "LEAKED",
    }
