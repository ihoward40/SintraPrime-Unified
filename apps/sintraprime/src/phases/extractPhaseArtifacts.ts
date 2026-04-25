import type { ExecutionPhase, ExecutionStep } from "../schemas/ExecutionPlan.schema.js";
import type { ExecutionRunLog } from "../executor/executePlan.js";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function extractPhaseArtifacts(params: {
  phase: ExecutionPhase;
  phaseRun: ExecutionRunLog;
  executedSteps: ExecutionStep[];
}): { outputs: Record<string, unknown>; files?: string[] } {
  const { phase, phaseRun, executedSteps } = params;
  const outputs: Record<string, unknown> = {};

  const wanted = phase.outputs ?? [];
  if (wanted.length === 0) return { outputs };

  // Prefer last step's response, fall back to last step's payload.
  const lastStepId = executedSteps.length ? executedSteps[executedSteps.length - 1]!.step_id : null;
  const lastStepLog = lastStepId ? phaseRun.steps.find((s) => s.step_id === lastStepId) : undefined;

  const lastResponse = isPlainObject(lastStepLog?.response) ? (lastStepLog!.response as Record<string, unknown>) : null;
  const lastPayload = executedSteps.length && isPlainObject(executedSteps[executedSteps.length - 1]!.payload)
    ? (executedSteps[executedSteps.length - 1]!.payload as Record<string, unknown>)
    : null;

  for (const k of wanted) {
    if (lastResponse && k in lastResponse) {
      outputs[k] = lastResponse[k];
      continue;
    }
    if (lastPayload && k in lastPayload) {
      outputs[k] = lastPayload[k];
    }
  }

  const maybeFiles = outputs.files;
  const files = Array.isArray(maybeFiles) && maybeFiles.every((x) => typeof x === "string") ? (maybeFiles as string[]) : undefined;

  return { outputs, files };
}
