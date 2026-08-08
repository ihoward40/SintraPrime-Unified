"""Constitutional invariants — machine-enforceable (directive §2, §20, §140).

Every invariant is a runtime/static validation rule. A prompt, agent,
workflow, or plugin cannot override an invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class Invariant(str, Enum):
    NO_AGENT_SELF_APPROVAL = "NO_AGENT_SELF_APPROVAL"
    NO_AGENT_SELF_PERMISSION_GRANT = "NO_AGENT_SELF_PERMISSION_GRANT"
    NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY = "NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY"
    NO_CROSS_TENANT_IMPLICIT_ACCESS = "NO_CROSS_TENANT_IMPLICIT_ACCESS"
    NO_CROSS_MATTER_IMPLICIT_ACCESS = "NO_CROSS_MATTER_IMPLICIT_ACCESS"
    NO_UNBOUNDED_AUTONOMOUS_LOOP = "NO_UNBOUNDED_AUTONOMOUS_LOOP"
    NO_UNBOUNDED_RETRY = "NO_UNBOUNDED_RETRY"
    NO_UNBOUNDED_PROVIDER_SPEND = "NO_UNBOUNDED_PROVIDER_SPEND"
    NO_SECRET_IN_PROMPT_LOG = "NO_SECRET_IN_PROMPT_LOG"
    NO_SECRET_IN_CHANNEL_MESSAGE = "NO_SECRET_IN_CHANNEL_MESSAGE"
    NO_CERTIFICATION_BY_IMPLEMENTER = "NO_CERTIFICATION_BY_IMPLEMENTER"
    NO_UNVERIFIED_AUTHORITY_ESCALATION = "NO_UNVERIFIED_AUTHORITY_ESCALATION"
    NO_PRODUCTION_DEPLOY_WITHOUT_GATE = "NO_PRODUCTION_DEPLOY_WITHOUT_GATE"
    NO_PROTECTED_BRANCH_AUTO_MERGE = "NO_PROTECTED_BRANCH_AUTO_MERGE"
    NO_CANONICAL_MEMORY_SELF_MODIFICATION = "NO_CANONICAL_MEMORY_SELF_MODIFICATION"
    NO_UNREGISTERED_TOOL_EXECUTION = "NO_UNREGISTERED_TOOL_EXECUTION"
    NO_UNHASHED_WORKFLOW_EXECUTION = "NO_UNHASHED_WORKFLOW_EXECUTION"
    NO_UNVERSIONED_POLICY_EXECUTION = "NO_UNVERSIONED_POLICY_EXECUTION"
    NO_PRIVILEGED_PUBLIC_AGENT = "NO_PRIVILEGED_PUBLIC_AGENT"
    NO_SILENT_EXTERNAL_WRITE = "NO_SILENT_EXTERNAL_WRITE"


@dataclass
class InvariantViolation:
    invariant: Invariant
    detail: str
    actor_id: str = ""
    action: str = ""

    def as_dict(self) -> dict:
        return {
            "invariant": self.invariant.value,
            "detail": self.detail,
            "actor_id": self.actor_id,
            "action": self.action,
        }


@dataclass
class ActionContext:
    """Everything the invariant engine needs to evaluate one action."""

    action: str = ""
    actor_id: str = ""
    actor_type: str = "agent"  # human | agent | service
    target_id: str = ""
    tenant_id: str = ""
    matter_id: str = ""
    approver_id: str = ""
    authority_class: str = "A0"
    capability: str = ""
    capability_registered: bool = True
    workflow_hash: str = ""
    policy_version: str = ""
    external_write: bool = False
    external_target: str = ""
    secret_in_payload: bool = False
    is_public_agent: bool = False
    max_retries: int | None = None
    budget_defined: bool = True
    max_hop_count: int | None = None
    hop_count: int = 0
    metadata: dict = field(default_factory=dict)


class InvariantEngine:
    """Deterministic constitutional gate. Fail closed on any violation."""

    ALL: ClassVar[list] = list(Invariant)

    def evaluate(self, ctx: ActionContext) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        a = ctx.action

        # NO_AGENT_SELF_APPROVAL
        if (
            a in ("approve", "self_approve")
            and ctx.actor_type == "agent"
            and ctx.approver_id == ctx.actor_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_AGENT_SELF_APPROVAL,
                    "agent approved its own action",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_AGENT_SELF_PERMISSION_GRANT
        if a == "grant_capability" and ctx.actor_type == "agent" and ctx.target_id == ctx.actor_id:
            violations.append(
                InvariantViolation(
                    Invariant.NO_AGENT_SELF_PERMISSION_GRANT,
                    "agent granted capability to itself",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY
        if (
            ctx.authority_class in ("A3", "A4")
            and ctx.actor_type != "human"
            and not ctx.approver_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY,
                    f"consequential action requires authority (class {ctx.authority_class})",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_CROSS_TENANT_IMPLICIT_ACCESS
        if (
            ctx.metadata.get("source_tenant")
            and ctx.tenant_id
            and ctx.metadata["source_tenant"] != ctx.tenant_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_CROSS_TENANT_IMPLICIT_ACCESS,
                    f"cross-tenant access {ctx.metadata['source_tenant']}->{ctx.tenant_id}",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_CROSS_MATTER_IMPLICIT_ACCESS
        if (
            ctx.metadata.get("source_matter")
            and ctx.matter_id
            and ctx.metadata["source_matter"] != ctx.matter_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_CROSS_MATTER_IMPLICIT_ACCESS,
                    f"cross-matter access {ctx.metadata['source_matter']}->{ctx.matter_id}",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNBOUNDED_AUTONOMOUS_LOOP
        if ctx.max_hop_count is None and ctx.hop_count > 0:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP,
                    "agent-originated event without hop bound",
                    ctx.actor_id,
                    a,
                )
            )
        if ctx.max_hop_count is not None and ctx.hop_count > ctx.max_hop_count:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP,
                    f"hop {ctx.hop_count} > max {ctx.max_hop_count}",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNBOUNDED_RETRY
        if ctx.max_retries is None and a in ("retry", "resume"):
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNBOUNDED_RETRY, "retry without max_retries", ctx.actor_id, a
                )
            )

        # NO_UNBOUNDED_PROVIDER_SPEND
        if not ctx.budget_defined:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNBOUNDED_PROVIDER_SPEND, "action without budget", ctx.actor_id, a
                )
            )

        # NO_SECRET_IN_PROMPT_LOG / CHANNEL
        if ctx.secret_in_payload:
            if a == "log_prompt":
                violations.append(
                    InvariantViolation(
                        Invariant.NO_SECRET_IN_PROMPT_LOG,
                        "secret present in prompt payload",
                        ctx.actor_id,
                        a,
                    )
                )
            if a == "channel_message":
                violations.append(
                    InvariantViolation(
                        Invariant.NO_SECRET_IN_CHANNEL_MESSAGE,
                        "secret present in channel message",
                        ctx.actor_id,
                        a,
                    )
                )

        # NO_CERTIFICATION_BY_IMPLEMENTER
        if (
            a == "certify"
            and ctx.actor_type == "agent"
            and ctx.metadata.get("implementer_id") == ctx.actor_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_CERTIFICATION_BY_IMPLEMENTER,
                    "implementer certified own work",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNVERIFIED_AUTHORITY_ESCALATION
        if a == "escalate_authority" and not ctx.metadata.get("verified"):
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNVERIFIED_AUTHORITY_ESCALATION,
                    "authority escalation without verification",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_PRODUCTION_DEPLOY_WITHOUT_GATE
        if (
            a == "deploy"
            and ctx.metadata.get("environment") == "production"
            and not ctx.approver_id
        ):
            violations.append(
                InvariantViolation(
                    Invariant.NO_PRODUCTION_DEPLOY_WITHOUT_GATE,
                    "production deploy without gate",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_PROTECTED_BRANCH_AUTO_MERGE
        if a == "merge" and ctx.metadata.get("protected_branch"):
            violations.append(
                InvariantViolation(
                    Invariant.NO_PROTECTED_BRANCH_AUTO_MERGE,
                    "auto-merge of protected branch",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_CANONICAL_MEMORY_SELF_MODIFICATION
        if a == "memory_write" and ctx.metadata.get("canonical") and ctx.actor_type == "agent":
            violations.append(
                InvariantViolation(
                    Invariant.NO_CANONICAL_MEMORY_SELF_MODIFICATION,
                    "agent direct canonical memory write",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNREGISTERED_TOOL_EXECUTION
        if a == "tool_execute" and not ctx.capability_registered:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNREGISTERED_TOOL_EXECUTION,
                    f"unregistered tool {ctx.capability}",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNHASHED_WORKFLOW_EXECUTION
        if a == "workflow_execute" and not ctx.workflow_hash:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNHASHED_WORKFLOW_EXECUTION,
                    "workflow without hash",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_UNVERSIONED_POLICY_EXECUTION
        if a == "policy_execute" and not ctx.policy_version:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNVERSIONED_POLICY_EXECUTION,
                    "policy without version",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_PRIVILEGED_PUBLIC_AGENT
        if ctx.is_public_agent and ctx.authority_class in ("A2", "A3", "A4"):
            violations.append(
                InvariantViolation(
                    Invariant.NO_PRIVILEGED_PUBLIC_AGENT,
                    "public agent with privileged authority",
                    ctx.actor_id,
                    a,
                )
            )

        # NO_SILENT_EXTERNAL_WRITE
        if ctx.external_write and not ctx.metadata.get("audited"):
            violations.append(
                InvariantViolation(
                    Invariant.NO_SILENT_EXTERNAL_WRITE,
                    "external write without audit",
                    ctx.actor_id,
                    a,
                )
            )

        return violations

    def evaluate_all(self, ctx: ActionContext) -> bool:
        return not self.evaluate(ctx)

    def static_check_workflow(self, definition: dict) -> list[InvariantViolation]:
        """Static checks on a workflow definition (§86, §144)."""
        violations: list[InvariantViolation] = []
        if "max_iterations" not in definition and "max_hops" not in definition:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNBOUNDED_AUTONOMOUS_LOOP, "workflow lacks max_iterations"
                )
            )
        if "budget" not in definition:
            violations.append(
                InvariantViolation(Invariant.NO_UNBOUNDED_PROVIDER_SPEND, "workflow lacks budget")
            )
        if "hash" not in definition:
            violations.append(
                InvariantViolation(Invariant.NO_UNHASHED_WORKFLOW_EXECUTION, "workflow lacks hash")
            )
        if "version" not in definition:
            violations.append(
                InvariantViolation(
                    Invariant.NO_UNVERSIONED_POLICY_EXECUTION, "workflow lacks version"
                )
            )
        if definition.get("authority_class") in ("A3", "A4") and "approval" not in definition:
            violations.append(
                InvariantViolation(
                    Invariant.NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY,
                    "high-authority workflow without approval gate",
                )
            )
        return violations
