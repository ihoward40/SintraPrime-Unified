import type { DecisionTrace } from "./decisionTrace.js";
import { decisionTrace } from "./decisionTrace.js";

export function explainSchedulerJob(params: {
  job: {
    job_id: string;
    schedule: string;
    command: string;
    mode: any;
    budgets: any;
    paused?: boolean;
  };
  at: Date;
  manual_trigger: boolean;
}): DecisionTrace {
  return decisionTrace({
    job: params.job as any,
    at: params.at,
    manual_trigger: params.manual_trigger,
  });
}
