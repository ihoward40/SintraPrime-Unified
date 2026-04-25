import { explainSchedulerJob } from "../scheduler/explain.js";

type SchedulerMode = "OFF" | "READ_ONLY_AUTONOMY" | "PROPOSE_ONLY_AUTONOMY" | "APPROVAL_GATED_AUTONOMY";

type JobBudgets = {
  max_steps: number;
  max_runtime_ms: number;
  max_runs_per_day: number;
};

type JobDefinition = {
  job_id: string;
  schedule: string;
  command: string;
  mode: SchedulerMode;
  budgets: JobBudgets;
  paused?: boolean;
};

export function runSchedulerExplain(params: { job: JobDefinition; at: Date }) {
  const trace = explainSchedulerJob({ job: params.job, at: params.at, manual_trigger: false });

  // External contract is exactly the trace fields (minus internal scheduler-only fields).
  const { window_id: _window, scheduler_action: _action, ...out } = trace as any;
  return out;
}
