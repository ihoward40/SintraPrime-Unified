import type { ExecutionPhase, ExecutionStep } from "../schemas/ExecutionPlan.schema.js";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function materializePhaseSteps(params: {
  phase: ExecutionPhase;
  artifacts: Record<string, { outputs: Record<string, unknown> }>;
}): ExecutionStep[] {
  const { phase, artifacts } = params;
  const inputsFrom = phase.inputs_from ?? [];
  if (inputsFrom.length === 0) return phase.steps;

  const injectedArtifacts: Record<string, { outputs: Record<string, unknown> }> = {};
  for (const id of inputsFrom) {
    const a = artifacts[id];
    if (a) injectedArtifacts[id] = { outputs: a.outputs };
  }

  return phase.steps.map((step) => {
    // Inject phase-scoped execution context into request bodies deterministically.
    const injection = { artifacts: injectedArtifacts };

    if (!isPlainObject(step.payload)) {
      return { ...step, payload: injection };
    }

    // If the step already has a payload object, merge in the injected artifacts without
    // mutating the original payload object.
    return { ...step, payload: { ...step.payload, ...injection } };
  });
}
