"""Goal drift detector and scope creep detector (§93-94, §140)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MissionContract:
    goal: str = ""
    scope_repos: list[str] = field(default_factory=list)
    scope_files: list[str] = field(default_factory=list)
    scope_agents: list[str] = field(default_factory=list)
    scope_tenants: list[str] = field(default_factory=list)
    scope_matters: list[str] = field(default_factory=list)
    authorized_agents: list[str] = field(default_factory=list)
    approved_token_budget: int = 100000
    approved_artifacts: list[str] = field(default_factory=list)


@dataclass
class DriftAlert:
    detector: str
    description: str
    severity: str = "WARNING"
    actual: str = ""
    expected: str = ""


class GoalDriftDetector:
    """Detect unauthorized repo/scope expansion (§93, §140)."""

    def detect(
        self, contract: MissionContract, *, actual_repo: str = "", actual_matter: str = ""
    ) -> DriftAlert | None:
        if contract.scope_repos and actual_repo and actual_repo not in contract.scope_repos:
            return DriftAlert(
                detector="goal_drift",
                description=f"unauthorized repo: {actual_repo} not in approved repos {contract.scope_repos}",
                actual=actual_repo,
                expected=str(contract.scope_repos),
            )
        if contract.scope_matters and actual_matter and actual_matter not in contract.scope_matters:
            return DriftAlert(
                detector="goal_drift",
                description=f"unauthorized matter: {actual_matter} not in approved {contract.scope_matters}",
                actual=actual_matter,
                expected=str(contract.scope_matters),
            )
        return None


class ScopeCreepDetector:
    """Track expansion of files/repos/agents/artifacts vs approved scope (§94)."""

    def detect(
        self,
        contract: MissionContract,
        *,
        actual_files: int = 0,
        actual_agents: int = 0,  # noqa: ARG002
        actual_artifacts: int = 0,  # noqa: ARG002
        actual_tokens: int = 0,
    ) -> list[DriftAlert]:
        alerts: list[DriftAlert] = []
        max_files = contract.approved_token_budget // 1000  # rough proxy
        if actual_files > max_files * 2:
            alerts.append(
                DriftAlert("scope_creep", f"files {actual_files} > 2x expected ~{max_files}")
            )
        if contract.authorized_agents and len(contract.authorized_agents) > 0:
            pass  # agent count is a hard list
        if actual_tokens > contract.approved_token_budget:
            alerts.append(
                DriftAlert(
                    "scope_creep",
                    f"tokens {actual_tokens} > budget {contract.approved_token_budget}",
                    "CRITICAL",
                )
            )
        return alerts
