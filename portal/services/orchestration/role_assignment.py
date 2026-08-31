"""Role selection rules for orchestration execution modes."""

from __future__ import annotations

from .schemas import ExecutionMode, Role


MODE_ROLES: dict[ExecutionMode, list[Role]] = {
    ExecutionMode.SINGLE: [Role.WORKER, Role.CHECKER],
    ExecutionMode.PLAN_AND_EXECUTE: [Role.PLANNER, Role.WORKER, Role.CHECKER, Role.RECONCILER],
    ExecutionMode.THINK_WORK_CHECK: [Role.THINKER, Role.WORKER, Role.CHECKER, Role.RECONCILER],
    ExecutionMode.PARALLEL_COMPARE: [Role.THINKER, Role.WORKER, Role.CHECKER, Role.RECONCILER],
    ExecutionMode.RESEARCH_SYNTHESIS: [Role.RESEARCHER, Role.CHECKER, Role.WORKER, Role.RECONCILER],
    ExecutionMode.CODE_REVIEW_LOOP: [Role.PLANNER, Role.WORKER, Role.CHECKER, Role.SECURITY_REVIEWER, Role.RECONCILER],
    ExecutionMode.HIGH_ASSURANCE: [
        Role.PLANNER,
        Role.THINKER,
        Role.WORKER,
        Role.CHECKER,
        Role.SECURITY_REVIEWER,
        Role.GOVERNANCE_REVIEWER,
        Role.RECONCILER,
        Role.PRINCIPAL,
    ],
}


def assign_roles(mode: ExecutionMode, classified_roles: list[Role]) -> list[Role]:
    """Merge mode-required roles with classification-required roles."""
    return list(dict.fromkeys([*MODE_ROLES[mode], *classified_roles]))
