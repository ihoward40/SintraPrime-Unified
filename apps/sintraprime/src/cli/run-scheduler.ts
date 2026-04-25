import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { nowUtcIso, shouldRunNow } from "../scheduler/schedule.js";
import { recordRun } from "../scheduler/history.js";
import { readSchedulerHistory } from "../scheduler/readHistory.js";
import { writeSchedulerReceipt } from "../artifacts/writeSchedulerReceipt.js";
import { decisionTrace } from "../scheduler/decisionTrace.js";
import { runSchedulerExplain } from "./run-scheduler-explain.js";
import { nowIso as fixedNowIso } from "../utils/clock.js";
import { enforceCliCredits } from "../credits/enforceCliCredits.js";

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

function nowIso() {
  const fixed = process.env.SMOKE_FIXED_NOW_ISO;
  if (fixed && fixed.trim()) return fixed.trim();
  return nowUtcIso();
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function getArgCommand() {
  const raw = process.argv.slice(2).join(" ").trim();
  if (!raw) throw new Error("Missing command argument");
  return raw;
}

function schedulerDir() {
  return path.join(process.cwd(), "runs", "scheduler");
}

function readJobsRegistry(): JobDefinition[] {
  const file = path.join(process.cwd(), "jobs", "registry.json");
  const json = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(json)) throw new Error("jobs/registry.json must be an array");
  return json as JobDefinition[];
}

function findJob(jobId: string): JobDefinition {
  const jobs = readJobsRegistry();
  const job = jobs.find((j) => j?.job_id === jobId);
  if (!job) throw new Error(`Unknown job_id '${jobId}'`);
  return job;
}

function runEngineCommand(command: string, env: NodeJS.ProcessEnv, timeoutMs: number) {
  const entry = path.join(process.cwd(), "src", "cli", "run-command.ts");
  const tsxBin = path.join(process.cwd(), "node_modules", ".bin", "tsx");
  const tsxNodeEntrypoint = path.join(process.cwd(), "node_modules", "tsx", "dist", "cli.mjs");

  const res = process.platform === "win32"
    ? spawnSync(process.execPath, [tsxNodeEntrypoint, entry, command], {
        env,
        encoding: "utf8",
        timeout: timeoutMs,
      })
    : spawnSync(tsxBin, [entry, command], {
        env,
        encoding: "utf8",
        timeout: timeoutMs,
      });

  if (res.error) {
    const anyErr: any = res.error;
    if (anyErr?.code === "ETIMEDOUT") {
      return {
        exitCode: 3,
        json: {
          kind: "PolicyDenied",
          code: "BUDGET_EXCEEDED",
          reason: `Job runtime exceeded ${timeoutMs}ms`,
        },
      };
    }
    throw new Error(res.error.message);
  }

  const stdout = String(res.stdout ?? "").trim();
  if (!stdout) {
    return { exitCode: res.status ?? 1, json: { kind: "CliError", code: "SCHEDULER_ENGINE_EMPTY", reason: "Engine produced no output" } };
  }

  let json: any = null;
  try {
    json = JSON.parse(stdout);
  } catch {
    json = { kind: "CliError", code: "SCHEDULER_ENGINE_NON_JSON", reason: stdout.slice(0, 240) };
  }

  return { exitCode: res.status ?? 0, json };
}

function parseSchedulerCommand(command: string): { kind: "SchedulerRun"; job_id?: string } | null {
  const trimmed = command.trim();
  const m = trimmed.match(/^\/scheduler\s+run(?:\s+(\S+))?\s*$/i);
  if (!m) return null;
  return { kind: "SchedulerRun", job_id: m[1] };
}

function parseSchedulerHistoryCommand(command: string):
  | { kind: "SchedulerHistory"; job_id?: string; limit?: number; since?: Date }
  | null {
  const trimmed = String(command ?? "").trim();
  if (!/^\/scheduler\s+history\b/i.test(trimmed)) return null;

  const tokens = trimmed.split(/\s+/).slice(2);
  let job_id: string | undefined;
  let limit: number | undefined;
  let since: Date | undefined;

  for (let i = 0; i < tokens.length; i += 1) {
    const t = tokens[i]!;

    if (t === "--limit") {
      const v = tokens[i + 1];
      if (!v) throw new Error("Usage: /scheduler history [job_id] [--limit N] [--since ISO]");
      const n = Number(v);
      if (!Number.isFinite(n) || n <= 0) throw new Error("--limit must be a positive number");
      limit = n;
      i += 1;
      continue;
    }

    if (t === "--since") {
      const v = tokens[i + 1];
      if (!v) throw new Error("Usage: /scheduler history [job_id] [--limit N] [--since ISO]");
      const d = new Date(v);
      if (!Number.isFinite(d.getTime())) throw new Error("--since must be a valid ISO timestamp");
      since = d;
      i += 1;
      continue;
    }

    if (t.startsWith("--")) {
      throw new Error(`Unknown flag: ${t}`);
    }

    if (!job_id) {
      job_id = t;
      continue;
    }

    throw new Error("Usage: /scheduler history [job_id] [--limit N] [--since ISO]");
  }

  return { kind: "SchedulerHistory", job_id, limit, since };
}

function parseSchedulerExplainCommand(command: string):
  | { kind: "SchedulerExplain"; job_id: string; at?: Date }
  | null {
  const trimmed = String(command ?? "").trim();
  if (!/^\/scheduler\s+explain\b/i.test(trimmed)) return null;

  const tokens = trimmed.split(/\s+/).slice(2);
  const job_id = tokens[0];
  if (!job_id) throw new Error("Usage: /scheduler explain <job_id> [--at <timestamp>]");

  let at: Date | undefined;
  for (let i = 1; i < tokens.length; i += 1) {
    const t = tokens[i]!;
    if (t === "--at") {
      const v = tokens[i + 1];
      if (!v) throw new Error("Usage: /scheduler explain <job_id> [--at <timestamp>]");
      const d = new Date(v);
      if (!Number.isFinite(d.getTime())) throw new Error("--at must be a valid ISO timestamp");
      at = d;
      i += 1;
      continue;
    }
    if (t.startsWith("--")) throw new Error(`Unknown flag: ${t}`);
    throw new Error("Usage: /scheduler explain <job_id> [--at <timestamp>]");
  }

  return { kind: "SchedulerExplain", job_id, at };
}

export async function runScheduler(jobId?: string) {
  const jobs = readJobsRegistry();
  const selected = jobId ? jobs.filter((j) => j?.job_id === jobId) : jobs;

  const receipts: any[] = [];

  for (const job of selected) {
    // When running a specific job explicitly, treat it as a manual trigger.
    // When running the whole registry, only run jobs that are due now.
    if (!jobId && !shouldRunNow(job.schedule)) continue;

    const started_at = nowIso();
    const now = new Date(started_at);

    const trace = decisionTrace({
      job,
      at: now,
      manual_trigger: Boolean(jobId),
    });

    if (trace.scheduler_action === "SKIP") {
      const skipped = {
        job_id: job.job_id,
        window_id: trace.window_id,
        skipped: true,
        reason: trace.primary_reason,
      };

      if (jobId) {
        console.log(JSON.stringify(skipped, null, 2));
        return;
      }

      receipts.push(skipped);
      continue;
    }

    // Delegate through the existing engine CLI; no executor shortcuts.
    // Budgets are enforced by policy (via env caps) rather than scheduler-side logic.
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      AUTONOMY_MODE: job.mode,
      POLICY_MAX_STEPS: String(job.budgets.max_steps),
      POLICY_MAX_RUNTIME_MS: String(job.budgets.max_runtime_ms),
      POLICY_MAX_RUNS_PER_DAY: String(job.budgets.max_runs_per_day),
      POLICY_BUDGET_DENY_CODE: "BUDGET_EXCEEDED",
    };

    let outcome: any;
    try {
      const engineOut = runEngineCommand(job.command, env, job.budgets.max_runtime_ms);
      outcome = engineOut.json;
    } catch (err: any) {
      outcome = { kind: "SchedulerError", error: err?.message ? String(err.message) : String(err) };
    }

    recordRun({
      job_id: job.job_id,
      window_id: trace.window_id,
      started_at,
      outcome,
    });

    const receipt = writeSchedulerReceipt({
      job_id: job.job_id,
      schedule: job.schedule,
      window_id: trace.window_id,
      started_at,
      outcome,
    });
    receipts.push(receipt);

    // For explicit single-job runs, surface PolicyDenied directly (smoke expects exit 3).
    if (jobId && isRecord(outcome) && outcome.kind === "PolicyDenied") {
      console.log(JSON.stringify(outcome, null, 2));
      process.exitCode = 3;
      return;
    }
  }

  console.log(
    JSON.stringify(
      {
        kind: "SchedulerRunResult",
        ran: receipts.length,
        receipts,
      },
      null,
      2
    )
  );
}

async function main() {
  const cmd = getArgCommand();

  {
    const threadId = (process.env.THREAD_ID || "local_test_001").trim();
    const now_iso = fixedNowIso();
    const denied = enforceCliCredits({ now_iso, threadId, command: cmd, domain_id: null });
    if (denied) {
      console.log(JSON.stringify(denied, null, 0));
      process.exitCode = 1;
      return;
    }
  }

  const parsedExplain = parseSchedulerExplainCommand(cmd);
  if (parsedExplain) {
    const job = findJob(parsedExplain.job_id);
    const at = parsedExplain.at ?? new Date(nowIso());
    const out = runSchedulerExplain({ job, at });
    console.log(JSON.stringify({ kind: "SchedulerExplain", ...out }, null, 2));
    return;
  }

  const parsedHistory = parseSchedulerHistoryCommand(cmd);
  if (parsedHistory) {
    const rows = readSchedulerHistory({
      job_id: parsedHistory.job_id,
      limit: parsedHistory.limit,
      since: parsedHistory.since,
    });

    console.log(JSON.stringify({ kind: "SchedulerHistory", count: rows.length, rows }, null, 2));
    return;
  }

  const parsed = parseSchedulerCommand(cmd);
  if (!parsed) throw new Error("Unknown scheduler command");

  if (parsed.job_id) {
    // validate job_id eagerly for good error messages
    findJob(parsed.job_id);
  }

  await runScheduler(parsed.job_id);
}

main().catch((e) => {
  const msg = e instanceof Error ? e.message : String(e);
  console.log(JSON.stringify({ kind: "CliError", code: "SCHEDULER_ERROR", reason: msg }, null, 2));
  process.exitCode = 1;
});
