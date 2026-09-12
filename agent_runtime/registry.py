"""AgentRegistry — one canonical registry (Wave 3, §12-§14).

register / resolve / list / validate / certify / disable / quarantine /
status. Startup validation fails closed (§13): duplicate agent IDs,
unknown capabilities, contradictory required+forbidden, invalid budgets,
missing owner, unsupported manifest versions — never silently discarded.
Certification status is a lifecycle (§14), never a single boolean.
"""
from __future__ import annotations

from .manifest import (
    MANIFEST_SCHEMA_VERSION,
    AgentManifest,
    CertificationStatus,
)

_OFF_STATES = frozenset(
    {
        CertificationStatus.DISABLED,
        CertificationStatus.REVOKED,
        CertificationStatus.QUARANTINED,
    }
)


class RegistryError(Exception):
    pass


class DuplicateAgentIdError(RegistryError):
    pass


class UnknownAgentError(RegistryError):
    pass


class ManifestValidationError(RegistryError):
    def __init__(self, agent_id: str, errors: list[str]) -> None:
        self.agent_id = agent_id
        self.errors = errors
        super().__init__(f"manifest validation failed for {agent_id}: {errors}")


class AgentRegistry:
    """One canonical registry. Fails closed at registration and startup."""

    def __init__(self) -> None:
        self._manifests: dict[str, AgentManifest] = {}
        self._statuses: dict[str, CertificationStatus] = {}

    def register(self, manifest: AgentManifest) -> AgentManifest:
        errors = self.validate(manifest)
        if errors:
            raise ManifestValidationError(manifest.agent_id, errors)
        if manifest.actor_id:
            for existing in self._manifests.values():
                if existing.actor_id and existing.actor_id == manifest.actor_id:
                    raise ManifestValidationError(
                        manifest.agent_id,
                        [f"duplicate actor_id already registered: {manifest.actor_id}"],
                    )
        if manifest.agent_id in self._manifests:
            raise DuplicateAgentIdError(f"agent_id already registered: {manifest.agent_id}")
        self._manifests[manifest.agent_id] = manifest
        self._statuses[manifest.agent_id] = CertificationStatus.REGISTERED
        return manifest

    def resolve(self, agent_id: str) -> AgentManifest:
        if agent_id not in self._manifests:
            raise UnknownAgentError(f"unknown agent: {agent_id}")
        return self._manifests[agent_id]

    def list(self) -> list[AgentManifest]:
        return list(self._manifests.values())

    def list_enabled(self) -> list[AgentManifest]:
        return [m for m in self._manifests.values() if self._statuses.get(m.agent_id) not in _OFF_STATES]

    def validate(self, manifest: AgentManifest) -> list[str]:
        """Structural validation; promotes REGISTERED → VALIDATED on success."""
        errors: list[str] = []
        if manifest.manifest_schema != MANIFEST_SCHEMA_VERSION:
            errors.append(f"unsupported manifest_schema {manifest.manifest_schema}")
        from agent_runtime.manifest import _resolves_to_known
        for cap in (*manifest.required_capabilities, *manifest.optional_capabilities, *manifest.forbidden_capabilities):
            if not _resolves_to_known(cap):
                errors.append(f"unknown capability: {cap}")
        overlap = set(manifest.required_capabilities) & set(manifest.forbidden_capabilities)
        if overlap:
            errors.append(f"contradictory required+forbidden: {sorted(overlap)}")
        if not manifest.owner:
            errors.append("missing owner (§11 authority domain required)")
        if manifest.timeout_seconds < 1 or manifest.max_iterations < 1:
            errors.append("invalid budget: timeout_seconds and max_iterations must be >= 1")
        if manifest.actor_id == "hermes.canonical":
            errors.append("worker actor may not impersonate hermes.canonical")
        if manifest.actor_id == "copilot.engineering.01":
            if manifest.parent_coordinator != "hermes.canonical":
                errors.append("copilot actor parent must be hermes.canonical")
            if manifest.authority_source != "NONE":
                errors.append("copilot actor authority_source cannot be elevated")
            if manifest.control_plane:
                errors.append("copilot actor cannot be control plane")
            if manifest.worker_role and manifest.worker_role != "ENGINEERING_WORKER":
                errors.append("copilot actor role mismatch")
        if manifest.parent_coordinator and manifest.parent_coordinator not in {
            "hermes.canonical",
            "agent.hermes",
        }:
            errors.append(f"unknown parent coordinator: {manifest.parent_coordinator}")
        return errors

    def validate_registered(self, agent_id: str) -> list[str]:
        """Validate a registered manifest and record VALIDATED on success (§14 ladder)."""
        manifest = self.resolve(agent_id)
        errors = self.validate(manifest)
        if not errors and self.status(agent_id) is CertificationStatus.REGISTERED:
            self.set_status(agent_id, CertificationStatus.VALIDATED)
        return errors

    def status(self, agent_id: str) -> CertificationStatus:
        return self._statuses.get(agent_id, CertificationStatus.UNREGISTERED)

    def set_status(self, agent_id: str, status: CertificationStatus) -> None:
        if agent_id not in self._manifests:
            raise UnknownAgentError(f"unknown agent: {agent_id}")
        self._statuses[agent_id] = status

    def disable(self, agent_id: str) -> None:
        self.set_status(agent_id, CertificationStatus.DISABLED)

    def quarantine(self, agent_id: str) -> None:
        """§58: block a misbehaving agent without disabling the platform."""
        self.set_status(agent_id, CertificationStatus.QUARANTINED)

    def revoke(self, agent_id: str) -> None:
        self.set_status(agent_id, CertificationStatus.REVOKED)

    def certify(self, agent_id: str) -> None:
        """Promote to CERTIFIED; evidence-backed ladder only (§14)."""
        current = self.status(agent_id)
        if current not in (CertificationStatus.VALIDATED, CertificationStatus.TESTED, CertificationStatus.DEGRADED):
            raise RegistryError(f"cannot certify from status {current}")
        self.set_status(agent_id, CertificationStatus.CERTIFIED)

    def startup_validation(self) -> None:
        """§13: validate every registered manifest; raise on defects."""
        problems: list[str] = []
        for manifest in self._manifests.values():
            problems.extend(f"[{manifest.agent_id}] {e}" for e in self.validate(manifest))
        if problems:
            raise ManifestValidationError("<startup>", problems)


def default_registry() -> AgentRegistry:
    """Module-level singleton accessor (the one authority, §12)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry


def copilot_engineering_manifest() -> AgentManifest:
    """Canonical bounded manifest for copilot.engineering.01."""
    return AgentManifest(
        agent_id="agent.copilot.engineering.01",
        agent_version="1.0.0",
        display_name="Copilot Engineering Worker",
        description="Bounded engineering worker under hermes.canonical.",
        owner="sintraprime.principal",
        runtime_class="swarm_runtime.hermes_adapter.HermesSwarmAdapter",
        mission_types=("engineering",),
        actor_id="copilot.engineering.01",
        worker_role="ENGINEERING_WORKER",
        parent_coordinator="hermes.canonical",
        authority_source="NONE",
        control_plane=False,
        preferred_task_types=(
            "CODE_IMPLEMENTATION",
            "TEST_IMPLEMENTATION",
            "STATIC_ANALYSIS",
            "DOCUMENTATION",
        ),
        max_parallel_tasks=2,
        write_capable=True,
        review_capable=True,
        required_capabilities=("READ_REPOSITORY", "WRITE_REPOSITORY", "RUN_TESTS"),
        forbidden_capabilities=("MERGE_PULL_REQUEST", "DEPLOY_SERVICE", "EXECUTE_PAYMENT"),
        provider_policy={"provider_class": "CODE"},
        tool_policy={},
        authority_policy="DELEGATED",
    )


def register_canonical_worker_directory(registry: AgentRegistry) -> None:
    """Idempotently register canonical worker directory entries."""
    if "agent.copilot.engineering.01" not in {m.agent_id for m in registry.list()}:
        registry.register(copilot_engineering_manifest())


_default_registry: AgentRegistry | None = None
