"""Governed PARL facade for SintraPrime-wide agent orchestration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from parl.god_mode import PrincipalCommandPolicy, PrincipalSession
from parl.orchestrator import PARLOrchestrator, Task


class GovernedPARLOrchestrator(PARLOrchestrator):
    """PARL orchestrator with Principal Command admission control.

    This preserves the existing PARL implementation and registration model,
    while placing one policy boundary in front of every subtask spawned by
    this facade.  Existing read/orchestration work stays compatible; elevated
    work must carry a valid Principal session and, where applicable, a
    downstream approval receipt.
    """

    def __init__(self, *args: Any, command_policy: Optional[PrincipalCommandPolicy] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.command_policy = command_policy or PrincipalCommandPolicy()

    def decompose_and_run(
        self,
        description: str,
        subtask_specs: List[Dict[str, Any]],
        training_step: Optional[int] = None,
        timeout: Optional[float] = None,
        principal_session: Optional[PrincipalSession] = None,
    ) -> Task:
        self.command_policy.authorize_specs(subtask_specs, session=principal_session)
        return super().decompose_and_run(
            description=description,
            subtask_specs=subtask_specs,
            training_step=training_step,
            timeout=timeout,
        )
