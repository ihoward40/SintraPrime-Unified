import fs from "node:fs";
import path from "node:path";

import { computeWindowId } from "./window.js";
import { hasRun, historyPath } from "./history.js";
import { nextEligibleAt, shouldRunAt } from "./schedule.js";
import { readSchedulerHistory } from "./readHistory.js";

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

export type DecisionCode =
  | "ELIGIBLE"
  | "DEDUP_ACTIVE"
  | "BUDGET_EXCEEDED"
  | "OUTSIDE_SCHEDULE"
  | "APPROVAL_REQUIRED"
  | "AUTONOMY_POLICY_DENY"
  | "PRESTATE_STALE"
  | "MANUALLY_PAUSED"
  | "LAST_RUN_FAILED";

export type SchedulerDecision = "ELIGIBLE" | "BLOCKED";

export type DecisionReason = {
  code: DecisionCode;
  detail: string;
  evidence: string;
};

export type PolicyContext = {
  autonomy_mode: SchedulerMode;
  approval_required: boolean;
  budget_state: {
    runs_today: number;
    max_runs_per_day: number;
  };
};

export type DecisionTrace = {
  job_id: string;
  evaluated_at: string;
  would_run: boolean;
  decision: SchedulerDecision;
  primary_reason: DecisionCode;
  reasons: DecisionReason[];
  policy_context: PolicyContext;
  next_eligible_at: string | null;
  to_unblock: string[];

  // Internal fields used by the scheduler runner.
  window_id: string;
  scheduler_action: "SKIP" | "RUN_THROUGH_ENGINE";
};

function isObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function utcDayKey(d: Date) {
  return d.toISOString().slice(0, 10); // YYYY-MM-DD
}

function readRunsTodayFromAutonomyState(at: Date): { dir: string; path: string; count: number } {
  const dir = process.env.AUTONOMY_STATE_DIR || "runs/autonomy/state";
  const key = utcDayKey(at);
  const p = path.join(dir, `runs-${key}.json`);

  if (!fs.existsSync(p)) {
    return { dir, path: p, count: 0 };
  }

  try {
    const json = JSON.parse(fs.readFileSync(p, "utf8"));
    const n = Number((json as any)?.count);
    return { dir, path: p, count: Number.isFinite(n) ? n : 0 };
  } catch {
    return { dir, path: p, count: 0 };
  }
}

function startOfNextUtcDayIso(at: Date): string {
  const d = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), at.getUTCDate() + 1, 0, 0, 0));
  return d.toISOString();
}

function pushUnblock(out: string[], items: string[]) {
  for (const i of items) {
    if (!out.includes(i)) out.push(i);
  }
}

function lastOutcomeSignalsApproval(outcome: unknown): boolean {
  if (!isObject(outcome)) return false;
  const k = String((outcome as any).kind ?? "");
  return k === "ApprovalRequired" || k === "ApprovalRequiredBatch";
}

function lastOutcomeSignalsPrestateStale(outcome: unknown): boolean {
  if (!isObject(outcome)) return false;
  return String((outcome as any).kind ?? "") === "NeedApprovalAgain";
}

function lastOutcomeSignalsAutonomyDeny(outcome: unknown): boolean {
  if (!isObject(outcome)) return false;
  if (String((outcome as any).kind ?? "") !== "PolicyDenied") return false;
  const code = String((outcome as any).code ?? "");
  return code.startsWith("AUTONOMY_");
}

function lastOutcomeSignalsFailure(outcome: unknown): boolean {
  if (!isObject(outcome)) return false;
  const k = String((outcome as any).kind ?? "");
  return k === "SchedulerError" || k === "CliError";
}

export function decisionTrace(params: {
  job: JobDefinition;
  at: Date;
  manual_trigger: boolean;
}): DecisionTrace {
  const job = params.job;
  const at = params.at;

  const evaluated_at = at.toISOString();
  const window_id = computeWindowId(job.job_id, job.schedule, at);

  const reasons: DecisionReason[] = [];
  const to_unblock: string[] = [];

  // Budget snapshot (read-only): from autonomy state file written by execution-time budget guard.
  const budgetSnap = readRunsTodayFromAutonomyState(at);
  const runs_today = budgetSnap.count;
  const max_runs_per_day = job.budgets.max_runs_per_day;

  const policy_context: PolicyContext = {
    autonomy_mode: job.mode,
    approval_required: false,
    budget_state: { runs_today, max_runs_per_day },
  };

  // Last-known outcome from scheduler history (receipts-only).
  const last = readSchedulerHistory({ job_id: job.job_id, limit: 1 })[0] ?? null;
  const lastOutcome = last ? (last as any).outcome : null;

  if (job.paused === true) {
    reasons.push({
      code: "MANUALLY_PAUSED",
      detail: "Job is paused by operator",
      evidence: path.join("jobs", "registry.json"),
    });
    pushUnblock(to_unblock, ["unpause the job"]);
  }

  // Schedule gate: only applies to registry runs; explicit job runs are manual triggers.
  const dueBySchedule = params.manual_trigger ? true : shouldRunAt(job.schedule, at);
  if (!dueBySchedule) {
    const next = nextEligibleAt(job.schedule, at);
    reasons.push({
      code: "OUTSIDE_SCHEDULE",
      detail: "Schedule is not satisfied at evaluated_at",
      evidence: path.join("jobs", "registry.json"),
    });
    if (next) {
      pushUnblock(to_unblock, ["wait until next_eligible_at", "or change schedule"]);
    } else {
      pushUnblock(to_unblock, ["change schedule"]);
    }
  }

  // Dedup gate: only meaningful for scheduler-driven windows.
  const dedupActive = hasRun(job.job_id, window_id);
  if (dedupActive) {
    const p = historyPath(job.job_id, window_id);
    let startedAt = "";
    try {
      const json = JSON.parse(fs.readFileSync(p, "utf8"));
      startedAt = typeof json?.started_at === "string" ? json.started_at : "";
    } catch {
      // ignore
    }

    reasons.push({
      code: "DEDUP_ACTIVE",
      detail: startedAt ? `Same dedup window executed at ${startedAt}` : "Same dedup window already executed",
      evidence: p.replace(/\\/g, "/"),
    });
    pushUnblock(to_unblock, ["wait until next_eligible_at", "or change dedup_key"]);
  }

  // Budget gate: read-only from autonomy state snapshot.
  if (runs_today >= max_runs_per_day) {
    reasons.push({
      code: "BUDGET_EXCEEDED",
      detail: `maxRunsPerDay=${max_runs_per_day}, used=${runs_today}`,
      evidence: budgetSnap.path.replace(/\\/g, "/"),
    });
    pushUnblock(to_unblock, ["wait until next_eligible_at", "or increase maxRunsPerDay"]);
  }

  // Policy/approval signals from last-known outcome receipts.
  if (lastOutcomeSignalsPrestateStale(lastOutcome)) {
    reasons.push({
      code: "PRESTATE_STALE",
      detail: "Last attempt indicated stale prestate (needs re-approval)",
      evidence: last ? historyPath(job.job_id, String((last as any).window_id ?? "")).replace(/\\/g, "/") : "runs/scheduler-history",
    });
    pushUnblock(to_unblock, ["re-approve the pending run"]);
  }

  if (lastOutcomeSignalsApproval(lastOutcome)) {
    policy_context.approval_required = true;
    reasons.push({
      code: "APPROVAL_REQUIRED",
      detail: "Last attempt required approval to proceed",
      evidence: last ? historyPath(job.job_id, String((last as any).window_id ?? "")).replace(/\\/g, "/") : "runs/scheduler-history",
    });
    pushUnblock(to_unblock, ["approve the pending run"]);
  }

  if (lastOutcomeSignalsAutonomyDeny(lastOutcome)) {
    reasons.push({
      code: "AUTONOMY_POLICY_DENY",
      detail: "Last attempt was denied by autonomy policy",
      evidence: last ? historyPath(job.job_id, String((last as any).window_id ?? "")).replace(/\\/g, "/") : "runs/scheduler-history",
    });
    pushUnblock(to_unblock, ["change autonomy mode or command"]);
  }

  if (lastOutcomeSignalsFailure(lastOutcome)) {
    reasons.push({
      code: "LAST_RUN_FAILED",
      detail: "Last attempt failed; retries may be blocked by policy",
      evidence: last ? historyPath(job.job_id, String((last as any).window_id ?? "")).replace(/\\/g, "/") : "runs/scheduler-history",
    });
  }

  // Determine primary reason deterministically by precedence.
  const precedence: DecisionCode[] = [
    "MANUALLY_PAUSED",
    "DEDUP_ACTIVE",
    "BUDGET_EXCEEDED",
    "OUTSIDE_SCHEDULE",
    "PRESTATE_STALE",
    "APPROVAL_REQUIRED",
    "AUTONOMY_POLICY_DENY",
    "LAST_RUN_FAILED",
  ];

  const primary_reason =
    precedence.find((c) => reasons.some((r) => r.code === c)) ?? "ELIGIBLE";

  const blocked = primary_reason !== "ELIGIBLE";

  let next_eligible_at: string | null = null;
  if (primary_reason === "OUTSIDE_SCHEDULE") {
    const next = nextEligibleAt(job.schedule, at);
    next_eligible_at = next ? next.toISOString() : null;
  } else if (primary_reason === "DEDUP_ACTIVE") {
    const next = nextEligibleAt(job.schedule, at);
    next_eligible_at = next ? next.toISOString() : null;
  } else if (primary_reason === "BUDGET_EXCEEDED") {
    next_eligible_at = startOfNextUtcDayIso(at);
  }

  const would_run = !blocked;

  // Scheduler action: even when approvals are required, the scheduler should still
  // delegate through the engine to create approval items; dedup/schedule/budget/paused skip.
  const scheduler_action =
    primary_reason === "OUTSIDE_SCHEDULE" ||
    primary_reason === "DEDUP_ACTIVE" ||
    primary_reason === "BUDGET_EXCEEDED" ||
    primary_reason === "MANUALLY_PAUSED"
      ? "SKIP"
      : "RUN_THROUGH_ENGINE";

  if (!blocked) {
    reasons.push({
      code: "ELIGIBLE",
      detail: "No blocking conditions detected",
      evidence: path.join("jobs", "registry.json"),
    });
    if (!to_unblock.length) {
      pushUnblock(to_unblock, ["no action needed"]);
    }
  }

  return {
    job_id: job.job_id,
    evaluated_at,
    would_run,
    decision: blocked ? "BLOCKED" : "ELIGIBLE",
    primary_reason,
    reasons,
    policy_context,
    next_eligible_at,
    to_unblock,
    window_id,
    scheduler_action,
  };
}
