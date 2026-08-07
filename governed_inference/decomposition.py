from __future__ import annotations

from governed_inference.contracts import DecomposedTask, InferenceRequest, RouteTier

TASK_DECOMPOSITION = {
    "code_complex": [
        ("inspect", "extraction", "Identify only the relevant files, commands, and constraints."),
        (
            "plan",
            "summarization",
            "Produce a bounded implementation plan with risks and test targets.",
        ),
        ("patch", "coding", "Implement one cohesive change set with minimal blast radius."),
        ("test", "coding", "Run or describe focused verification and fix direct failures."),
    ],
    "draft_legal_restricted": [
        (
            "extract",
            "extraction",
            "Extract facts, names, dates, monetary figures, and evidence citations.",
        ),
        (
            "outline",
            "summarization",
            "Create a local-only outline preserving controlling legal facts.",
        ),
        (
            "draft",
            "drafting",
            "Draft from the outline without sending restricted data to cloud providers.",
        ),
    ],
}


def decompose_for_local_models(request: InferenceRequest) -> list[DecomposedTask]:
    recipe = TASK_DECOMPOSITION.get(request.task_type)
    if recipe is None:
        return []
    input_cap = max(1000, min(request.max_input_tokens, 6000))
    output_cap = max(300, min(request.max_output_tokens, 1200))
    return [
        DecomposedTask(
            task_id=f"{request.request_id}:{index}:{task_type}",
            parent_request_id=request.request_id,
            task_type=task_type,
            capability=capability,
            route_tier=RouteTier.LOCAL_PRIVATE,
            max_input_tokens=input_cap,
            max_output_tokens=output_cap,
            instruction=instruction,
        )
        for index, (task_type, capability, instruction) in enumerate(recipe, start=1)
    ]
