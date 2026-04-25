import type { ExecutionPhase, ExecutionPlan } from "../schemas/ExecutionPlan.schema.js";

export type PhaseValidationResult = {
  phases_planned: string[];
};

function isNonEmptyString(x: unknown): x is string {
  return typeof x === "string" && x.trim().length > 0;
}

export function validatePhases(plan: ExecutionPlan): PhaseValidationResult {
  const phases = plan.phases;
  if (!phases) return { phases_planned: [] };

  if (!Array.isArray(phases) || phases.length === 0) {
    throw new Error("phases must be a non-empty array when provided");
  }
  
    // Disallow mixing phased + legacy single-phase steps.
    // The executor runs either phased mode (plan.phases) or legacy mode (plan.steps).
    // Having both is ambiguous and a common source of accidental extra work.
    if (Array.isArray((plan as any).steps) && (plan as any).steps.length > 0) {
      throw new Error("when phases are provided, top-level steps must be omitted (or empty)");
    }

  const ids = phases.map((p) => p.phase_id);
  if (!ids.every(isNonEmptyString)) {
    throw new Error("phase_id must be a non-empty string");
  }

  const seen = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) throw new Error(`phase_id must be unique (duplicate: ${id})`);
    seen.add(id);
  }

  for (let i = 0; i < phases.length; i += 1) {
    const phase: ExecutionPhase = phases[i]!;

    if (!Array.isArray(phase.required_capabilities) || !phase.required_capabilities.every(isNonEmptyString)) {
      throw new Error(`phase '${phase.phase_id}' required_capabilities must be string[]`);
    }

    if (!Array.isArray(phase.steps) || phase.steps.length === 0) {
      throw new Error(`phase '${phase.phase_id}' must contain at least one step`);
    }

    const stepIds = new Set<string>();
    for (const s of phase.steps) {
      if (!isNonEmptyString(s.step_id)) throw new Error(`phase '${phase.phase_id}' step_id must be a non-empty string`);
      if (stepIds.has(s.step_id)) {
        throw new Error(`phase '${phase.phase_id}' step_id must be unique (duplicate: ${s.step_id})`);
      }
      stepIds.add(s.step_id);
    }

    if (phase.inputs_from !== undefined) {
      if (!Array.isArray(phase.inputs_from) || !phase.inputs_from.every(isNonEmptyString)) {
        throw new Error(`phase '${phase.phase_id}' inputs_from must be string[]`);
      }

      for (const dep of phase.inputs_from) {
        const depIndex = ids.indexOf(dep);
        if (depIndex === -1) {
          throw new Error(`phase '${phase.phase_id}' inputs_from references unknown phase '${dep}'`);
        }
        if (depIndex >= i) {
          throw new Error(`phase '${phase.phase_id}' inputs_from must reference only earlier phases (got '${dep}')`);
        }
      }
    }

    if (phase.outputs !== undefined) {
      if (!Array.isArray(phase.outputs) || !phase.outputs.every(isNonEmptyString)) {
        throw new Error(`phase '${phase.phase_id}' outputs must be string[]`);
      }
    }
  }

  return { phases_planned: ids };
}
