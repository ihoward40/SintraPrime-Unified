"""Focused least-context instruction compiler."""

from __future__ import annotations

from .schemas import ClassificationResult, FocusedInstruction, Role


def compile_instruction(
    *,
    role: Role,
    objective: str,
    classification: ClassificationResult,
    dependencies: list[str] | None = None,
) -> FocusedInstruction:
    """Build role-scoped instructions without forwarding unrestricted context."""
    dependencies = dependencies or []
    output_schema = {
        "role": role.value,
        "result": "string or structured object",
        "confidence": "number between 0 and 1",
        "evidence": "list of redacted evidence references",
        "assumptions": "list of assumptions",
        "unresolved_uncertainty": "list of unresolved issues",
    }
    return FocusedInstruction(
        exact_objective=_role_objective(role, objective),
        permitted_inputs=["objective", "classification", *dependencies],
        required_output_schema=output_schema,
        constraints=[
            f"Task type is {classification.task_type.value}.",
            f"Sensitivity is {classification.sensitivity.value}.",
            "Use deterministic mock-provider behavior in Milestone One.",
            "Do not execute external actions.",
        ],
        prohibited_actions=classification.prohibited_actions,
        evidence_requirements=[classification.evidence_requirement],
        completion_criteria=_completion_criteria(role),
        escalation_conditions=[
            "Principal approval is required for gated actions.",
            "Escalate unsupported claims, security risk, or budget exhaustion.",
        ],
    )


def _role_objective(role: Role, objective: str) -> str:
    prefix = {
        Role.PLANNER: "Create a bounded execution plan for",
        Role.THINKER: "Identify approaches, uncertainty, and assumptions for",
        Role.RESEARCHER: "Gather permitted evidence for",
        Role.WORKER: "Produce the assigned work product for",
        Role.CHECKER: "Independently verify the work product for",
        Role.SECURITY_REVIEWER: "Review secrets, permissions, unsafe actions, and exposure for",
        Role.GOVERNANCE_REVIEWER: "Review authority, policy, and approval requirements for",
        Role.RECONCILER: "Reconcile outputs and preserve unresolved disagreement for",
        Role.PRINCIPAL: "Record the human authority decision required for",
    }[role]
    return f"{prefix}: {objective}"


def _completion_criteria(role: Role) -> list[str]:
    if role == Role.CHECKER:
        return ["Verification result is explicit.", "Contradictions and unsupported claims are listed."]
    if role == Role.RECONCILER:
        return ["Verified result, supported inference, unresolved issue, and Principal decisions are separated."]
    if role == Role.PRINCIPAL:
        return ["Approval request is explicit and no model self-approval is permitted."]
    return ["Output matches required schema.", "Confidence and uncertainty are reported."]
