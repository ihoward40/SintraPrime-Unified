export type ScoreFeatures = {
  steps: number;
  writes: number;
  approval_required: boolean;
  domains: string[];
  capabilities: string[];
  budgets?: { max_steps?: number; max_runtime_ms?: number };
  agent_versions_pinned?: boolean;
  timeouts_capped?: boolean;
  capabilities_resolved?: boolean;
  unresolved_capabilities?: string[];
};

function uniqSorted(values: string[]) {
  return Array.from(new Set(values)).sort();
}

export function extractScoreFeatures(input: {
  plan?: any;
  policy_simulation?: any;
  capabilities_resolved?: boolean;
  unresolved_capabilities?: string[];
  policy_env?: NodeJS.ProcessEnv;
}): ScoreFeatures {
  const plan = input.plan ?? {};
  const stepsArr = Array.isArray(plan.steps) ? plan.steps : [];

  const steps = stepsArr.length;

  const writes = stepsArr.filter((s: any) => s?.read_only === false).length;

  const domains = uniqSorted(
    stepsArr.map((s: any) => {
      try {
        return new URL(String(s?.url ?? "")).hostname;
      } catch {
        return "invalid";
      }
    })
  );

  const capabilities = Array.isArray(plan.required_capabilities)
    ? plan.required_capabilities.filter((c: any) => typeof c === "string")
    : [];

  const approval_required =
    Boolean(plan.requires_approval) ||
    Boolean(input.policy_simulation?.decision === "APPROVAL_REQUIRED") ||
    Boolean(input.policy_simulation?.decision === "APPROVAL_REQUIRED" || input.policy_simulation?.requireApproval);

  const budgetsFromPlan = plan.budgets
    ? {
        max_steps: plan.budgets.max_steps,
        max_runtime_ms: plan.budgets.max_runtime_ms,
      }
    : undefined;

  const maxStepsEnv = input.policy_env ? Number(input.policy_env.POLICY_MAX_STEPS ?? NaN) : NaN;
  const maxRuntimeEnv = input.policy_env ? Number(input.policy_env.POLICY_MAX_RUNTIME_MS ?? NaN) : NaN;
  const budgetsFromEnv =
    Number.isFinite(maxStepsEnv) || Number.isFinite(maxRuntimeEnv)
      ? {
          max_steps: Number.isFinite(maxStepsEnv) ? maxStepsEnv : undefined,
          max_runtime_ms: Number.isFinite(maxRuntimeEnv) ? maxRuntimeEnv : undefined,
        }
      : undefined;

  const budgets = budgetsFromPlan ?? budgetsFromEnv;

  const agent_versions = plan.agent_versions;
  const agent_versions_pinned =
    !!agent_versions &&
    typeof agent_versions === "object" &&
    typeof agent_versions.validator === "string" &&
    agent_versions.validator.trim().length > 0 &&
    typeof agent_versions.planner === "string" &&
    agent_versions.planner.trim().length > 0;

  const env = input.policy_env;
  const capMs = env ? Number(env.POLICY_MAX_RUNTIME_MS ?? NaN) : NaN;
  const timeouts = stepsArr
    .map((s: any) => (typeof s?.timeout_ms === "number" ? s.timeout_ms : null))
    .filter((n: any) => typeof n === "number");
  const timeouts_capped = Number.isFinite(capMs)
    ? timeouts.every((t: number) => t <= capMs)
    : true;

  return {
    steps,
    writes,
    approval_required,
    domains,
    capabilities,
    budgets,
    agent_versions_pinned,
    timeouts_capped,
    capabilities_resolved: input.capabilities_resolved,
    unresolved_capabilities: Array.isArray(input.unresolved_capabilities) ? input.unresolved_capabilities : undefined,
  };
}
