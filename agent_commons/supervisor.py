from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .adapters import AgentAdapter
from .models import LifecycleStatus, MessageRecord, RunStatus, SupervisorRun
from .store import AgentCommonsStore


@dataclass(frozen=True)
class SupervisorPolicy:
    max_delegation_depth: int = 2
    require_independent_review: bool = True
    material_disagreement_threshold: float = 0.5
    prohibited_actions: tuple[str, ...] = (
        "merge",
        "deploy",
        "send_legal_communication",
        "send_financial_communication",
        "send_government_communication",
        "transfer_funds",
        "execute_unapproved_external_action",
    )


class GovernedSupervisor:
    """Coordinates a builder/reviewer pair while preserving owner authority."""

    def __init__(
        self,
        store: AgentCommonsStore,
        adapters: Mapping[str, AgentAdapter],
        policy: SupervisorPolicy | None = None,
    ) -> None:
        self.store = store
        self.adapters = dict(adapters)
        self.policy = policy or SupervisorPolicy()

    async def run_objective(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
        owner_agent: str,
        objective: str,
        builder_agent: str,
        reviewer_agent: str,
        acceptance_criteria: Iterable[str],
        idempotency_key: str,
        requested_actions: Iterable[str] = (),
    ) -> SupervisorRun:
        self._validate_agents(builder_agent, reviewer_agent)
        blocked_actions = sorted(set(requested_actions).intersection(self.policy.prohibited_actions))

        run = SupervisorRun(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            thread_id=thread_id,
            objective=objective,
            owner_agent=owner_agent,
            builder_agent=builder_agent,
            reviewer_agent=reviewer_agent,
            acceptance_criteria=list(acceptance_criteria),
        )
        run = self.store.save_run(run, idempotency_key=idempotency_key)
        if run.status != RunStatus.PENDING:
            return run

        if blocked_actions:
            run.status = RunStatus.WAITING_APPROVAL
            run.reconciliation = {
                "summary": "Objective requests owner-controlled actions.",
                "blocked_actions": blocked_actions,
                "material_disagreement": True,
            }
            run.approval_id = self.store.create_approval(
                tenant_id,
                run.run_id,
                f"Owner approval required for: {', '.join(blocked_actions)}",
            )
            self._record(
                run,
                "supervisor",
                [owner_agent],
                LifecycleStatus.BLOCKED,
                run.reconciliation,
                True,
            )
            self.store.update_run(run)
            return run

        run.status = RunStatus.RUNNING
        self.store.update_run(run)
        self._record(
            run,
            "supervisor",
            [builder_agent],
            LifecycleStatus.ASSIGNED,
            {
                "objective": objective,
                "acceptance_criteria": run.acceptance_criteria,
                "role": "builder",
            },
        )

        try:
            context = self._build_context(run)
            builder = await self.adapters[builder_agent].invoke(
                {
                    "task_id": run.task_id,
                    "objective": objective,
                    "acceptance_criteria": run.acceptance_criteria,
                },
                context,
            )
            run.builder_result = builder.output
            self._record(
                run,
                builder_agent,
                ["supervisor"],
                LifecycleStatus.RESULT,
                builder.output,
                evidence=builder.evidence,
            )

            review = await self.adapters[reviewer_agent].invoke(
                {
                    "task_id": run.task_id,
                    "objective": "Independently review the builder result",
                    "candidate": builder.output,
                    "acceptance_criteria": run.acceptance_criteria,
                },
                self._build_context(run),
            )
            run.review_result = review.output
            self._record(
                run,
                reviewer_agent,
                ["supervisor"],
                LifecycleStatus.RESULT,
                review.output,
                evidence=review.evidence,
            )
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.reconciliation = {
                "summary": "Agent invocation failed.",
                "failure_type": type(exc).__name__,
                "failed_agent": reviewer_agent if run.builder_result is not None else builder_agent,
            }
            self._record(
                run,
                "supervisor",
                [owner_agent],
                LifecycleStatus.BLOCKED,
                run.reconciliation,
                False,
            )
            self.store.update_run(run)
            raise

        disagreement = self._material_disagreement(builder.output, review.output)
        run.reconciliation = {
            "summary": review.output.get("summary")
            or builder.output.get("summary")
            or "Supervisor run completed.",
            "builder": builder_agent,
            "reviewer": reviewer_agent,
            "material_disagreement": disagreement,
            "acceptance_criteria": run.acceptance_criteria,
        }
        if disagreement:
            run.status = RunStatus.WAITING_APPROVAL
            run.approval_id = self.store.create_approval(
                tenant_id,
                run.run_id,
                "Builder and reviewer materially disagree. Owner decision required.",
            )
            self._record(
                run,
                "supervisor",
                [owner_agent],
                LifecycleStatus.BLOCKED,
                run.reconciliation,
                True,
            )
        else:
            run.status = RunStatus.COMPLETED
            self._record(
                run,
                "supervisor",
                [owner_agent],
                LifecycleStatus.RESULT,
                run.reconciliation,
                False,
            )

        self.store.update_run(run)
        return run

    def approve(
        self,
        tenant_id: str,
        run_id: str,
        approval_id: str,
        note: str = "",
    ) -> SupervisorRun:
        run = self.store.get_run(tenant_id, run_id)
        if run.approval_id != approval_id or run.status != RunStatus.WAITING_APPROVAL:
            raise ValueError("approval does not match a waiting supervisor run")
        self.store.decide_approval(tenant_id, approval_id, approved=True, note=note)
        run.status = RunStatus.COMPLETED
        self._record(
            run,
            run.owner_agent,
            ["supervisor"],
            LifecycleStatus.CLOSED,
            {"decision": "approved", "note": note},
        )
        self.store.update_run(run)
        return run

    def approve_pre_execution(
        self,
        tenant_id: str,
        run_id: str,
        approval_id: str,
        note: str = "",
    ) -> SupervisorRun:
        """Record owner authorization without claiming the work has executed."""
        run = self.store.get_run(tenant_id, run_id)
        if run.approval_id != approval_id or run.status != RunStatus.WAITING_APPROVAL:
            raise ValueError("approval does not match a waiting supervisor run")
        if run.builder_result is not None or not (
            run.reconciliation and run.reconciliation.get("blocked_actions")
        ):
            raise ValueError("run is not a pre-execution action gate")
        self.store.decide_approval(tenant_id, approval_id, approved=True, note=note)
        run.status = RunStatus.PENDING
        run.reconciliation = {
            **run.reconciliation,
            "summary": "Owner approval recorded; supervised execution has not yet run.",
            "authorization_recorded": True,
            "execution_pending": True,
        }
        self._record(
            run,
            run.owner_agent,
            ["supervisor"],
            LifecycleStatus.ACK,
            {
                "decision": "approved",
                "note": note,
                "execution_pending": True,
            },
        )
        self.store.update_run(run)
        return run

    def reject(
        self,
        tenant_id: str,
        run_id: str,
        approval_id: str,
        note: str = "",
    ) -> SupervisorRun:
        run = self.store.get_run(tenant_id, run_id)
        if run.approval_id != approval_id or run.status != RunStatus.WAITING_APPROVAL:
            raise ValueError("approval does not match a waiting supervisor run")
        self.store.decide_approval(tenant_id, approval_id, approved=False, note=note)
        run.status = RunStatus.CANCELLED
        self._record(
            run,
            run.owner_agent,
            ["supervisor"],
            LifecycleStatus.REJECTED,
            {"decision": "rejected", "note": note},
        )
        self.store.update_run(run)
        return run

    def _build_context(self, run: SupervisorRun) -> dict[str, Any]:
        messages = self.store.get_thread(
            run.tenant_id,
            run.workspace_id,
            run.channel_id,
            run.thread_id,
        )
        bounded = messages[-50:]
        return {
            "tenant_id": run.tenant_id,
            "workspace_id": run.workspace_id,
            "channel_id": run.channel_id,
            "thread_id": run.thread_id,
            "task_id": run.task_id,
            "thread_history": bounded,
            "provenance": [
                {"message_id": message["message_id"], "from_agent": message["from_agent"]}
                for message in bounded
            ],
        }

    def _record(
        self,
        run: SupervisorRun,
        from_agent: str,
        to_agents: list[str],
        status: LifecycleStatus,
        payload: dict[str, Any],
        owner_decision_required: bool = False,
        evidence: list[str] | None = None,
    ) -> None:
        self.store.append_message(
            MessageRecord(
                tenant_id=run.tenant_id,
                workspace_id=run.workspace_id,
                channel_id=run.channel_id,
                thread_id=run.thread_id,
                task_id=run.task_id,
                from_agent=from_agent,
                to_agents=to_agents,
                status=status,
                payload=payload,
                evidence=evidence or [],
                owner_decision_required=owner_decision_required,
                trace={"supervisor_run_id": run.run_id},
            )
        )

    def _validate_agents(self, builder_agent: str, reviewer_agent: str) -> None:
        if builder_agent == reviewer_agent:
            raise ValueError("builder and reviewer must be independent agents")
        missing = [
            agent
            for agent in (builder_agent, reviewer_agent)
            if agent not in self.adapters
        ]
        if missing:
            raise KeyError(f"unregistered adapters: {', '.join(missing)}")

    @staticmethod
    def _material_disagreement(
        builder: dict[str, Any], reviewer: dict[str, Any]
    ) -> bool:
        if reviewer.get("material_disagreement") is True:
            return True
        if reviewer.get("approved") is False:
            return True
        builder_decision = builder.get("decision")
        reviewer_decision = reviewer.get("decision")
        return bool(
            builder_decision
            and reviewer_decision
            and builder_decision != reviewer_decision
        )
