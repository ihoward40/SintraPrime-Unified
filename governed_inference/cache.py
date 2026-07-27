from __future__ import annotations

from dataclasses import replace

from governed_inference.contracts import CacheStatus, InferenceRequest, InferenceResult, stable_hash


class ExactInferenceCache:
    def __init__(self) -> None:
        self._entries: dict[str, InferenceResult] = {}

    def key_for(self, request: InferenceRequest) -> str:
        return stable_hash(
            {
                "messages": request.messages,
                "system_prompt_version": request.metadata.get("system_prompt_version", "default"),
                "route_class": request.metadata.get("route_class", request.capability),
                "schema": request.structured_output_schema,
                "temperature": request.temperature,
                "tools": request.tools,
                "data_classification": request.data_classification.value,
                "policy_version": request.metadata.get("policy_version", "default"),
                "redaction_version": request.metadata.get("redaction_version", "none"),
            }
        )

    def get(self, request: InferenceRequest) -> InferenceResult | None:
        cached = self._entries.get(self.key_for(request))
        if cached is None:
            return None
        return replace(
            cached,
            request_id=request.request_id,
            cache_status=CacheStatus.HIT,
            provider_request_id=None,
        )

    def set(self, request: InferenceRequest, result: InferenceResult) -> None:
        self._entries[self.key_for(request)] = result
