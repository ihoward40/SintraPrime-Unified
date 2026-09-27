"""Adapters binding agentic_runtime to existing SintraPrime machinery."""
from __future__ import annotations
import uuid
from typing import Any, Callable, Dict, Optional

from agents.nova.approval_gateway import ApprovalGateway, ApprovalStatus
from agents.nova.execution_ledger import ExecutionLedger, LedgerEntry
from local_models.model_router import ModelRouter, TaskType

from .capabilities import ModelCapabilityRegistry


class ApprovalGatewayAdapter:
    """Fail-closed bridge to Nova's existing ApprovalGateway.

    Pending requests are never interpreted as authorization. A caller may
    provide a resolver for an already-approved request or configure the
    existing gateway's own auto-approval policy.
    """
    def __init__(self, gateway: ApprovalGateway, resolver: Optional[Callable[[Any], bool]] = None):
        self.gateway = gateway
        self.resolver = resolver

    def __call__(self, action: str, context: Dict[str, Any]) -> bool:
        request = self.gateway.submit_for_approval(
            action=action,
            metadata={"description": action, "params": context, "agentic_runtime": True},
            requested_by=str(context.get("requested_by", "agentic_runtime")),
        )
        if request.status in {ApprovalStatus.APPROVED.value, ApprovalStatus.AUTO_APPROVED.value}:
            return True
        if self.resolver is not None:
            return bool(self.resolver(request))
        return False


class ExecutionLedgerAdapter:
    def __init__(self, ledger: ExecutionLedger, *, user_id: str = "agentic_runtime", case_id: Optional[str] = None):
        self.ledger = ledger
        self.user_id = user_id
        self.case_id = case_id

    def __call__(self, event: str, payload: Dict[str, Any]) -> None:
        self.ledger.append(LedgerEntry(
            entry_id=str(uuid.uuid4()),
            action_id=str(payload.get("action_id", uuid.uuid4())),
            action_type=event,
            params=payload,
            result={"ok": payload.get("ok")} if "ok" in payload else None,
            status="PASS" if payload.get("ok") is True else ("FAIL" if payload.get("ok") is False else "RECORDED"),
            user_id=self.user_id,
            approval_status=str(payload.get("approval_status", "GOVERNED")),
            case_id=self.case_id,
            evidence={"source": "agentic_runtime"},
        ))


class CapabilityRouterAdapter:
    """Select only verified capability profiles, then invoke existing ModelRouter."""
    def __init__(self, router: ModelRouter, registry: ModelCapabilityRegistry):
        self.router = router
        self.registry = registry

    def complete(self, prompt: str, *, required: set[str], min_context: int = 0, task: TaskType = TaskType.GENERAL):
        candidates = self.registry.candidates(required, min_context, verified_only=True)
        if not candidates:
            raise RuntimeError("NO_VERIFIED_MODEL_CAPABILITY_MATCH")
        profile = candidates[0]
        return self.router.complete(prompt, model=profile.model_id, task=task)
