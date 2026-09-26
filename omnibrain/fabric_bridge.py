"""Decision Fabric <-> agent runtime bridge (SP-OMNIBRAIN-RUNTIME-001).

Constitutional rule (SP-SYSTEM-ONE-DECISION-FABRIC-001 §1):
    Probability may select a workflow. Probability may not create authority.

This module is an ADVISORY seam between the Decision Fabric and the agent
runtime tool gateway. It never grants, extends, or restores authority:

- The fabric classifies a pending tool request (risk / advice class).
- The runtime ToolPolicyGate REMAINS the sole authorization decision.
- If the fabric is unavailable, errors, or returns anything unexpected,
  the bridge returns ADVISORY_UNAVAILABLE and the runtime proceeds under
  its own static policy — the SAME authority it had before asking.
- A DENY advice from the fabric does not by itself authorize anything;
  it only escalates to the runtime's existing refusal/approval paths.

Fail-closed direction: an unavailable advisor must never WEAKEN the
runtime's decision. It may only REINFORCE refusal or leave the static
decision untouched.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Advice model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FabricAdvice:
    """Advisory output. Carries NO authority semantics."""

    advice_class: str          # NORMAL | ELEVATED_RISK | ADVISE_DENY | ADVISORY_UNAVAILABLE
    detail: str
    fabric_decision_id: str | None = None   # ledger provenance, when a decision ran
    provider_failed: bool = False


class FabricRunner(Protocol):
    """Minimal structural type: anything with DecisionEngine.evaluate's shape."""

    def attach(self, engine: Any) -> None: ...


# Effect classes that the fabric may flag as elevated. Mirrors
# agent_runtime.manifest.SideEffectClass semantics without importing it
# (keeps the bridge decoupled and testable in isolation).
_ELEVATED_EFFECT_CLASSES = {
    "EXTERNAL_IRREVERSIBLE",
    "FINANCIAL",
    "LEGAL",
    "CREDENTIAL",
    "DEPLOYMENT",
    "EXTERNAL_REVERSIBLE",
}


class FabricAdvisor:
    """Ask the Decision Fabric to classify a tool request. Advisory only.

    Parameters
    ----------
    engine:
        A ``decision.engine.DecisionEngine`` (mock provider in tests).
    contract:
        A ``decision.contracts.DecisionContract`` whose questions produce
        the advice classification. Must exist and be admitted; the bridge
        never invents contracts.
    run_id:
        Correlation id for the fabric ledger.
    """

    def __init__(self, engine: Any, contract: Any, *, run_id: str = "RUN-OMNIBRAIN-ADVISORY") -> None:
        self._engine = engine
        self._contract = contract
        self._run_id = run_id

    def classify_tool_request(
        self,
        *,
        tool_id: str,
        effect_class: str,
        mission_id: str,
        agent_id: str,
    ) -> FabricAdvice:
        """Classify one pending tool request. NEVER raises to the caller:
        any fabric failure degrades to ADVISORY_UNAVAILABLE (fail-closed
        in the authority sense — the runtime keeps its own static policy)."""
        state = {
            "decision_type": "tool_request_advisory",
            "tool_id": tool_id,
            "effect_class": effect_class,
            "mission_id": mission_id,
            "agent_id": agent_id,
        }
        try:
            result, policy, receipt = asyncio.get_event_loop().run_until_complete(
                self._engine.evaluate(state=state, contract=self._contract, run_id=self._run_id)
            )
        except Exception as exc:  # advisory must never propagate failure
            return FabricAdvice(
                advice_class="ADVISORY_UNAVAILABLE",
                detail=f"fabric unavailable: {type(exc).__name__}",
                provider_failed=True,
            )
        # Non-DECISION results (errors) are already mapped by the fabric policy
        # to fail-closed fallbacks; surface them as unavailable.
        if policy.provider_failed or policy.decision in ("FALLBACK_HERMES", "QUARANTINE"):
            return FabricAdvice(
                advice_class="ADVISORY_UNAVAILABLE",
                detail=f"fabric policy: {policy.decision}: {policy.reason}",
                fabric_decision_id=receipt.get("decision_id"),
                provider_failed=True,
            )
        # Effect-class elevation is a static fact, independent of provider output:
        # a provider cannot downgrade a dangerous request by expressing confidence.
        if effect_class in _ELEVATED_EFFECT_CLASSES:
            return FabricAdvice(
                advice_class="ELEVATED_RISK",
                detail=f"static effect-class elevation: {effect_class}",
                fabric_decision_id=receipt.get("decision_id"),
            )
        # Provider advice may only reinforce refusal (ADVISE_DENY); it can never
        # upgrade the request or waive runtime checks.
        deny_signals = any(
            getattr(a, "primitive", None) is not None
            and getattr(a.primitive, "value", "") == "boolean"
            and getattr(a, "value", None) is True
            for a in result.answers.values()
        )
        if deny_signals:
            return FabricAdvice(
                advice_class="ADVISE_DENY",
                detail="fabric recommends denial (advisory; runtime decides)",
                fabric_decision_id=receipt.get("decision_id"),
            )
        return FabricAdvice(
            advice_class="NORMAL",
            detail="no elevation signals",
            fabric_decision_id=receipt.get("decision_id"),
        )
