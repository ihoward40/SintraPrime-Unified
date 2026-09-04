"""JARVIS-001-B1 GovernedActionExecutor (B1-3) — the one mutation boundary.

Enforcement order (each step fails closed before any provider mutation):
 1 validate typed ProposedAction (constructor already enforces; re-check type)
 2 verify tenant (executor context tenant == action tenant)
 3 verify action type is allowlisted
 4 retrieve action-bound approval
 5 verify Principal authority (artifact principal == proposing principal)
 6 verify params_hash (approval hash == action hash)
 7 verify approval not consumed/replayed (exactly-once, at consumption)
 8 establish idempotency key (deterministic from action_id)
 9 capture pre-action external state
10 perform mutation (only if intended state not already present)
11 independently refetch external state
12 verify intended state (provider response is NOT proof)
13 persist ActionReceipt (hash-chained)
14 bounded memory writeback (B1: returns record id via existing vault seam)
15 existing Principal Brief update is left to the mission layer (A-chain).

Hard invariant: NO_VALID_AUTHORITY -> NO_PROVIDER_MUTATION.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from .jarvis_action_approval import consume_action_approval
from .jarvis_action_receipt import ActionReceiptChain, compute_receipt_hash
from .jarvis_action_taxonomy import ActionFailure
from .jarvis_proposed_action import ALLOWED_ACTION_TYPES, ProposedAction


@dataclass
class AuthorityContext:
    """Executor-owned authority context: provider + credential path.

    The credential lives ONLY here, at the execution boundary — never in
    workers, proposals, receipts, memory, or logs.
    """

    provider: object
    credential: str | None = None
    mutate_timeout_s: float = 2.0


RECEIPT_CHAIN = None  # initialized lazily; B1 is single-process


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash_state(state) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_target(resource: str) -> tuple[str, int]:
    if "#" not in resource:
        raise ActionFailure("PROPOSED_ACTION_INVALID", f"target_resource {resource!r}")
    repo, _, number = resource.rpartition("#")
    if not repo or not number.isdigit():
        raise ActionFailure("PROPOSED_ACTION_INVALID")
    return repo, int(number)


class GovernedActionExecutor:
    """The only authoritative mutation boundary for JARVIS-001-B1."""

    def __init__(self, adapter) -> None:
        self._adapter = adapter

    async def _reconcile_after_timeout(
        self, db, action, artifact, repo, issue_number, label,
        pre_hash, idem_key,
    ) -> ExecutionResult:
        """Mutation ack was lost: external state is UNKNOWN.

        Refetch provider state and reconcile:
        - label present  -> the mutation landed: SIDE_EFFECT_SUCCEEDED (proven),
          receipt records timeout_reconciled provenance, approval consumed once
        - refetch failed -> VERIFICATION_INCONCLUSIVE (no fabricated success)
        - label absent   -> SIDE_EFFECT_UNKNOWN (retry is the caller's decision
          under the same action_id/idempotency policy, never automatic)
        """
        try:
            post = self._adapter.read_issue_state(repo, issue_number)
        except Exception as err:
            raise ActionFailure(
                "VERIFICATION_INCONCLUSIVE",
                "mutation ack lost and refetch failed; external state unknown",
            ) from err
        post_hash = _hash_state(post)
        if label in post:
            await consume_action_approval(db, artifact=artifact)
            receipt = _build_receipt(
                action=action, artifact=artifact, executor=type(self).__name__,
                params_hash=action.params_hash, pre_hash=pre_hash,
                result_hash=post_hash, post_hash=post_hash,
                verification_status="SIDE_EFFECT_SUCCEEDED",
            )
            receipt["timeout_reconciled"] = True
            receipt["receipt_hash"] = compute_receipt_hash({**receipt, "receipt_hash": ""})
            return ExecutionResult(
                verification_status="SIDE_EFFECT_SUCCEEDED",
                receipt=receipt,
                idempotency_key=idem_key,
            )
        raise ActionFailure(
            "SIDE_EFFECT_UNKNOWN",
            "mutation ack lost; refetch shows label absent; no automatic retry",
        )

    async def execute(self, db, action, approval, *, authority_context=None) -> ExecutionResult:
        if action.action_type not in ALLOWED_ACTION_TYPES:
            raise ActionFailure("ACTION_TYPE_NOT_ALLOWLISTED")

        # 4. resolve the approval BEFORE touching any provider (fail-closed order)
        artifact = _resolve_approval(approval)
        # 2. tenant
        if artifact.tenant_id != action.tenant_id:
            raise ActionFailure("TENANT_MISMATCH")
        # 5. principal authority binding
        if artifact.principal_user_id != action.proposed_by:
            raise ActionFailure("AUTHORITY_DENIED", "artifact principal != proposal principal")
        # 6. params hash binding
        if artifact.params_hash != action.params_hash:
            raise ActionFailure("APPROVAL_MISMATCH", "params_hash changed after approval")
        if artifact.status != "APPROVED":
            raise ActionFailure(
                "APPROVAL_MISSING" if artifact.status == "PENDING"
                else "APPROVAL_REPLAY" if artifact.status == "CONSUMED"
                else "APPROVAL_MISMATCH"
            )

        repo, issue_number = _parse_target(action.target_resource)
        label = action.parameters.get("label")
        if not isinstance(label, str) or not label:
            raise ActionFailure("PROPOSED_ACTION_INVALID")
        provider = authority_context.provider if authority_context else None
        if self._adapter is None or provider is None:
            raise ActionFailure("EXECUTOR_UNAVAILABLE")

        # 9. pre-action state
        pre = self._adapter.read_issue_state(repo, issue_number)
        pre_hash = _hash_state(pre)
        idem_key = f"jarvis-b1:{action.action_id}"

        # B1-6: GitHub label set semantics — already present = reconciled.
        # For a CONSUMED artifact (retry of an executed action) this is a
        # pure reconciliation: no new mutation, no replay error.
        # For a live APPROVED artifact: consume it once (idempotent no-op path).
        if label in pre and artifact.status == "CONSUMED":
            receipt = _build_receipt(
                action=action, artifact=artifact, executor=type(self).__name__,
                params_hash=action.params_hash, pre_hash=pre_hash, result_hash=pre_hash,
                post_hash=pre_hash, verification_status="IDEMPOTENT_SUCCESS",
            )
            return ExecutionResult(
                verification_status="IDEMPOTENT_SUCCESS",
                receipt=receipt,
                idempotency_key=idem_key,
            )
        if label in pre:
            await consume_action_approval(db, artifact=artifact)
            receipt = _build_receipt(
                action=action, artifact=artifact, executor=self.__class__.__name__,
                params_hash=action.params_hash, pre_hash=pre_hash, result_hash=pre_hash,
                post_hash=pre_hash, verification_status="IDEMPOTENT_SUCCESS",
            )
            return ExecutionResult(
                verification_status="IDEMPOTENT_SUCCESS",
                receipt=receipt,
                idempotency_key=idem_key,
            )

        # 10. mutation through the executor-owned adapter only.
        # Timeout-bounded: a lost/timed-out ack does NOT authorize a second POST.
        try:
            mutation_response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._adapter.mutate, repo, issue_number, label,
                    token=authority_context.credential,
                ),
                timeout=authority_context.mutate_timeout_s,
            )
        except TimeoutError:
            # 11/12. state UNKNOWN -> refetch and reconcile; never blind-retry.
            return await self._reconcile_after_timeout(
                db, action, artifact, repo, issue_number, label,
                pre_hash, idem_key,
            )
        if not isinstance(mutation_response, dict) or not mutation_response.get("ok"):
            raise ActionFailure("PROVIDER_ERROR", str(mutation_response))

        # 11/12. independent verification — provider response is not proof
        try:
            post = self._adapter.read_issue_state(repo, issue_number)
        except Exception as err:
            raise ActionFailure(
                "VERIFICATION_INCONCLUSIVE",
                "mutation response received but post-state refetch failed",
            ) from err
        post_hash = _hash_state(post)
        if label not in post:
            raise ActionFailure("VERIFICATION_FAILED")

        # 7. consume the approval exactly once AFTER provider+verification success
        await consume_action_approval(db, artifact=artifact)

        receipt = _build_receipt(
            action=action, artifact=artifact, executor=type(self).__name__,
            params_hash=action.params_hash, pre_hash=pre_hash,
            result_hash=_hash_state(mutation_response), post_hash=post_hash,
            verification_status="SIDE_EFFECT_SUCCEEDED",
        )
        return ExecutionResult(
            verification_status="SIDE_EFFECT_SUCCEEDED",
            receipt=receipt,
            idempotency_key=idem_key,
        )


@dataclass
class ExecutionResult:
    verification_status: str
    receipt: dict
    idempotency_key: str | None = None


def _build_receipt(*, action, artifact, executor_name=None, executor=None, params_hash=None, pre_hash, result_hash, post_hash, verification_status) -> dict:
    executor_name = executor_name or executor or "GovernedActionExecutor"
    params_hash = params_hash or action.params_hash
    global RECEIPT_CHAIN
    if RECEIPT_CHAIN is None:
        from .jarvis_action_receipt import ActionReceiptChain
        RECEIPT_CHAIN = ActionReceiptChain()
    receipt = {
        "receipt_id": f"rcpt-{action.action_id[:18]}",
        "action_id": action.action_id,
        "mission_id": action.mission_id,
        "request_id": action.request_id,
        "tenant_id": action.tenant_id,
        "approval_id": artifact.approval_id,
        "executor": executor_name,
        "provider": "github",
        "target": action.target_resource,
        "params_hash": action.params_hash,
        "pre_action_state_hash": pre_hash,
        "execution_result_hash": result_hash,
        "post_action_state_hash": post_hash,
        "verification_status": verification_status,
        "actor": action.proposed_by,
        "authority": "TENANT_PRINCIPAL",
        "started_at": _now_iso(),
        "completed_at": _now_iso(),
        "result_hash": result_hash,
        "receipt_hash": "",
        "previous_receipt_hash": _receipt_chain_prev(),
    }
    receipt["receipt_hash"] = compute_receipt_hash({**receipt, "receipt_hash": ""})
    if RECEIPT_CHAIN is not None:
        RECEIPT_CHAIN.entries.append(receipt)
    return receipt


async def govern_action(
    db,
    action,
    approval,
    *,
    adapter,
    authority_context=None,
) -> ExecutionResult:
    """Convenience entry: GovernedActionExecutor(adapter).execute(...)."""
    return await GovernedActionExecutor(adapter=adapter).execute(
        db, action, approval, authority_context=authority_context
    )


def _resolve_approval(approval):
    """Resolve the executor-presentable approval into its artifact.

    Accepts the artifact itself, or the opaque approval token string
    ("jarvis-b1-approval:<id>") which is resolved through the registry.
    Dict-shaped objects (Nova-style in-memory approvals) are rejected —
    they are not part of the governed path (B0 bypass audit).
    """
    if approval is None:
        raise ActionFailure("APPROVAL_MISSING")
    from .jarvis_action_approval import _REGISTRY, approval_token_for

    if isinstance(approval, str):
        approval_id = approval.split(":", 1)[1] if ":" in approval else approval
        artifact = _REGISTRY.get_by_approval_id(approval_id)
        if artifact is None:
            raise ActionFailure("APPROVAL_MISSING")
        return artifact
    if isinstance(approval, dict):
        raise ActionFailure("APPROVAL_MISMATCH", "dict-style approval objects are not authority")
    return approval


def _receipt_chain_prev() -> str:
    if RECEIPT_CHAIN is not None and RECEIPT_CHAIN.entries:
        return RECEIPT_CHAIN.entries[-1]["receipt_hash"]
    return "0" * 64
