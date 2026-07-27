from __future__ import annotations

from governed_inference.contracts import (
    DataClassification,
    EscalationRequest,
    InferenceRequest,
    RejectedRoute,
    receipt_hash,
)


class EscalationQueue:
    def __init__(self) -> None:
        self.items: list[EscalationRequest] = []

    def enqueue(
        self,
        *,
        request: InferenceRequest,
        classification: DataClassification,
        reason: str,
        denied_routes: list[RejectedRoute],
        estimated_cost_usd: float | None,
    ) -> EscalationRequest:
        item = EscalationRequest(
            escalation_id=receipt_hash(request.request_id, reason, len(self.items)),
            request_id=request.request_id,
            reason=reason,
            denied_routes=denied_routes,
            required_capability=request.capability,
            data_classification=classification,
            estimated_cost_usd=estimated_cost_usd,
        )
        self.items.append(item)
        return item
