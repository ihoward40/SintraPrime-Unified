"""Deterministic task classification for governed orchestration."""

from __future__ import annotations

from .schemas import ClassificationResult, Role, Sensitivity, TaskType


HIGH_RISK_ACTIONS = (
    "merge code",
    "deploy",
    "spend money",
    "publish public content",
    "send external communications",
    "change legal positions",
    "modify payment settings",
    "access restricted evidence",
)


def classify_task(objective: str, constraints: dict | None = None) -> ClassificationResult:
    """Classify a request without calling any external provider."""
    constraints = constraints or {}
    text = f"{objective} {' '.join(str(value) for value in constraints.values())}".lower()
    task_type = _task_type(text)
    sensitivity = _sensitivity(text, constraints)
    roles = _required_roles(task_type, sensitivity)
    approval_required = sensitivity in {Sensitivity.RESTRICTED, Sensitivity.PRIVILEGED} or any(
        action in text for action in HIGH_RISK_ACTIONS
    )

    return ClassificationResult(
        task_type=task_type,
        sensitivity=sensitivity,
        required_roles=roles,
        recommended_providers=_recommended_providers(task_type),
        expected_cost=0.0,
        expected_latency="mock-fast",
        approval_requirement=approval_required,
        evidence_requirement=_evidence_requirement(task_type),
        prohibited_actions=list(HIGH_RISK_ACTIONS),
    )


def _task_type(text: str) -> TaskType:
    matches: list[TaskType] = []
    keyword_map = {
        TaskType.CODING: ("code", "implementation", "bug", "test", "api", "frontend", "backend"),
        TaskType.RESEARCH: ("research", "cite", "source", "evidence", "fact"),
        TaskType.LEGAL_INFORMATION: ("legal", "law", "trust", "court", "statute", "compliance"),
        TaskType.FINANCIAL_ANALYSIS: ("financial", "budget", "cost", "revenue", "tax", "payment"),
        TaskType.DOCUMENT_GENERATION: ("document", "draft", "memo", "contract", "summary"),
        TaskType.OPERATIONS: ("operations", "workflow", "runbook", "incident", "monitor"),
        TaskType.CUSTOMER_SUPPORT: ("customer", "support", "ticket", "reply", "communication"),
        TaskType.MARKETING: ("marketing", "campaign", "positioning", "copy", "brand"),
        TaskType.SECURITY: ("security", "secret", "permission", "token", "exposure", "vulnerability"),
    }
    for task_type, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            matches.append(task_type)
    if len(set(matches)) > 1:
        return TaskType.MIXED
    return matches[0] if matches else TaskType.OPERATIONS


def _sensitivity(text: str, constraints: dict) -> Sensitivity:
    explicit = str(constraints.get("sensitivity", "")).upper()
    if explicit in Sensitivity.__members__:
        return Sensitivity[explicit]
    if any(word in text for word in ("privileged", "attorney-client", "legal strategy")):
        return Sensitivity.PRIVILEGED
    if any(word in text for word in ("restricted", "tax identifier", "banking", "password", "api key", "token")):
        return Sensitivity.RESTRICTED
    if any(word in text for word in ("confidential", "client", "private")):
        return Sensitivity.CONFIDENTIAL
    if "public" in text:
        return Sensitivity.PUBLIC
    return Sensitivity.INTERNAL


def _required_roles(task_type: TaskType, sensitivity: Sensitivity) -> list[Role]:
    roles = [Role.PLANNER, Role.THINKER, Role.WORKER, Role.CHECKER, Role.RECONCILER]
    if task_type in {TaskType.RESEARCH, TaskType.LEGAL_INFORMATION, TaskType.FINANCIAL_ANALYSIS, TaskType.MIXED}:
        roles.insert(2, Role.RESEARCHER)
    if task_type == TaskType.SECURITY or sensitivity in {Sensitivity.RESTRICTED, Sensitivity.PRIVILEGED}:
        roles.append(Role.SECURITY_REVIEWER)
    if sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED, Sensitivity.PRIVILEGED}:
        roles.append(Role.GOVERNANCE_REVIEWER)
    return list(dict.fromkeys(roles))


def _recommended_providers(task_type: TaskType) -> list[str]:
    if task_type == TaskType.CODING:
        return ["coding_model", "reasoning_model", "checker_model"]
    if task_type in {TaskType.RESEARCH, TaskType.LEGAL_INFORMATION, TaskType.FINANCIAL_ANALYSIS}:
        return ["research_model", "reasoning_model", "checker_model"]
    if task_type == TaskType.SECURITY:
        return ["security_model", "checker_model", "reasoning_model"]
    return ["reasoning_model", "checker_model"]


def _evidence_requirement(task_type: TaskType) -> str:
    if task_type in {TaskType.RESEARCH, TaskType.LEGAL_INFORMATION, TaskType.FINANCIAL_ANALYSIS}:
        return "citations-required"
    if task_type == TaskType.CODING:
        return "tests-or-code-references-required"
    return "supporting-rationale-required"
