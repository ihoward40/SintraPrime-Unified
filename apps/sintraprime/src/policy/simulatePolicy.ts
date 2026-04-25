import crypto from "node:crypto";

import type { ExecutionPlan, ExecutionStep } from "../schemas/ExecutionPlan.schema.js";
import { checkPlanPolicy, checkPolicyWithMeta } from "./checkPolicy.js";
import { materializePhaseSteps } from "../phases/materializePhaseSteps.js";

export type PolicySimulationPhaseTrace = {
  phase_id: string;
  steps_count: number;
  policy: unknown;
};

export type PolicySimulationOutput = {
  kind: "PolicySimulation";
  simulation: true;
  evaluated_at: string;
  command: string;
  execution_id: string;
  threadId: string;
  autonomy_mode: string;
  approval: boolean;
  would_run: boolean;
  decision: "ALLOWED" | "DENIED" | "APPROVAL_REQUIRED";
  primary_reason: string;
  policy: unknown;
  phases: PolicySimulationPhaseTrace[];
};

function stableFingerprint(obj: any) {
  const stable = (value: any): any => {
    if (value === null || value === undefined) return value;
    if (Array.isArray(value)) return value.map(stable);
    if (typeof value !== "object") return value;
    const keys = Object.keys(value).sort();
    const out: any = {};
    for (const k of keys) out[k] = stable(value[k]);
    return out;
  };

  const json = JSON.stringify(stable(obj));
  return crypto.createHash("sha256").update(json).digest("hex");
}

function ensureSimulatedPrestateForApprovedWrites(steps: ExecutionStep[]) {
  for (const step of steps as any[]) {
    const approvalScoped = step?.approval_scoped === true;
    const readOnly = step?.read_only;
    if (!approvalScoped || readOnly === true) continue;

    const action = typeof step?.action === "string" ? step.action : "";
    const isNotionLiveWrite = action === "notion.live.write";
    if (!isNotionLiveWrite) continue;

    if (step.prestate === undefined) {
      step.prestate = {
        _simulated: true,
        step_id: String(step.step_id ?? ""),
        action,
        url: String(step.url ?? ""),
      };
    }

    const fp = typeof step.prestate_fingerprint === "string" ? step.prestate_fingerprint.trim() : "";
    if (!fp) {
      step.prestate_fingerprint = stableFingerprint(step.prestate);
    }
  }
}

function summarizePolicyResult(policy: any): { decision: PolicySimulationOutput["decision"]; primary_reason: string; would_run: boolean } {
  if (policy && policy.allowed === true) {
    return { decision: "ALLOWED", primary_reason: "ALLOWED", would_run: true };
  }
  if (policy && policy.requireApproval === true && policy.approval) {
    const code = typeof policy.approval.code === "string" ? policy.approval.code : "APPROVAL_REQUIRED";
    return { decision: "APPROVAL_REQUIRED", primary_reason: code, would_run: false };
  }
  const denied = policy && policy.denied ? policy.denied : null;
  const code = denied && typeof denied.code === "string" ? denied.code : "DENIED";
  return { decision: "DENIED", primary_reason: code, would_run: false };
}

export function simulatePolicy(params: {
  plan: ExecutionPlan;
  command: string;
  env: NodeJS.ProcessEnv;
  at: Date;
  autonomy_mode: string;
  approval: boolean;
}): PolicySimulationOutput {
  const { plan, env, at } = params;

  const phases: PolicySimulationPhaseTrace[] = [];

  const planDenied = checkPlanPolicy(plan as any, env);
  if (planDenied) {
    const policy = { allowed: false, denied: planDenied };
    const summary = summarizePolicyResult(policy);
    return {
      kind: "PolicySimulation",
      simulation: true,
      evaluated_at: at.toISOString(),
      command: params.command,
      execution_id: plan.execution_id,
      threadId: plan.threadId,
      autonomy_mode: params.autonomy_mode,
      approval: params.approval,
      would_run: summary.would_run,
      decision: summary.decision,
      primary_reason: summary.primary_reason,
      policy,
      phases,
    };
  }

  const phasesCount = Array.isArray(plan.phases) ? plan.phases.length : 0;
  const totalStepsPlanned = Array.isArray(plan.phases)
    ? plan.phases.reduce((acc, p) => acc + (Array.isArray(p?.steps) ? p.steps.length : 0), 0)
    : Array.isArray(plan.steps)
      ? plan.steps.length
      : 0;

  const artifacts: Record<string, { outputs: Record<string, unknown> }> = {};
  if (Array.isArray(plan.phases)) {
    for (const p of plan.phases) {
      if (p?.phase_id) artifacts[String(p.phase_id)] = { outputs: {} };
    }
  }

  let finalPolicy: any = { allowed: true };

  if (Array.isArray(plan.phases) && plan.phases.length) {
    for (const phase of plan.phases) {
      const phaseId = String(phase.phase_id ?? "").trim();
      const phaseSteps = materializePhaseSteps({ phase, artifacts });

      const execPlan: any = {
        ...plan,
        phases: undefined,
        steps: phaseSteps,
      };

      const meta: any = {
        phase_id: phaseId || undefined,
        phases_count: phasesCount,
        total_steps_planned: totalStepsPlanned,
        execution_id: String(execPlan.execution_id),
        approved_execution_id: params.approval ? String(execPlan.execution_id) : undefined,
        command: params.command,
      };

      if (params.approval) {
        ensureSimulatedPrestateForApprovedWrites(execPlan.steps);
      }

      const policy = checkPolicyWithMeta(execPlan, env, at, meta);
      phases.push({ phase_id: phaseId || "unknown", steps_count: phaseSteps.length, policy });
      finalPolicy = policy;

      if (!(policy as any).allowed) break;
    }
  } else {
    const steps = Array.isArray(plan.steps) ? plan.steps : [];
    const execPlan: any = { ...plan, phases: undefined, steps };

    const meta: any = {
      phases_count: 0,
      total_steps_planned: steps.length,
      execution_id: String(execPlan.execution_id),
      approved_execution_id: params.approval ? String(execPlan.execution_id) : undefined,
      command: params.command,
    };

    if (params.approval) {
      ensureSimulatedPrestateForApprovedWrites(execPlan.steps);
    }

    const policy = checkPolicyWithMeta(execPlan, env, at, meta);
    phases.push({ phase_id: "single", steps_count: steps.length, policy });
    finalPolicy = policy;
  }

  const summary = summarizePolicyResult(finalPolicy);

  return {
    kind: "PolicySimulation",
    simulation: true,
    evaluated_at: at.toISOString(),
    command: params.command,
    execution_id: plan.execution_id,
    threadId: plan.threadId,
    autonomy_mode: params.autonomy_mode,
    approval: params.approval,
    would_run: summary.would_run,
    decision: summary.decision,
    primary_reason: summary.primary_reason,
    policy: finalPolicy,
    phases,
  };
}
