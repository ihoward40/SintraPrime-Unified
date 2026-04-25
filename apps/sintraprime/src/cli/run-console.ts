import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { nowIso as fixedNowIso } from "../utils/clock.js";
import { enforceCliCredits } from "../credits/enforceCliCredits.js";
import {
  SCHEMA_VERSION,
  assertValid,
  ArtifactIndexSchema,
  QueueItemJsonlSchema,
  QueueListSchema,
  RunDetailsSchema,
  RunTimelineSchema,
  RunRejectedSchema,
} from "./consoleSchemas.js";

function nowIso() {
  return new Date().toISOString();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function approvalsDir() {
  return path.join(process.cwd(), "runs", "approvals");
}

function approvalPath(execution_id: string) {
  return path.join(approvalsDir(), `${execution_id}.json`);
}

function readJsonFile(p: string) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function writeJsonFile(p: string, data: unknown) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(data, null, 2), { encoding: "utf8" });
}

function getArgCommand() {
  const raw = process.argv.slice(2).join(" ").trim();
  if (!raw) throw new Error("Missing command argument");
  return raw;
}

function parseQuotedOrRaw(text: string) {
  const t = text.trim();
  if (!t) return "";
  if (t.startsWith('"')) {
    // Treat as a JSON string literal for PowerShell-proof quoting.
    return JSON.parse(t);
  }
  return t;
}

function parseQueueCommand(command: string):
  | { kind: "QueueList"; status?: string; jsonl?: boolean }
  | { kind: "QueueApprove"; execution_id: string }
  | { kind: "QueueReject"; execution_id: string; reason: string }
  | { kind: "QueueRollback"; execution_id: string }
  | null {
  const trimmed = command.trim();
  if (!/^\/queue\b/i.test(trimmed)) return null;

  const rest = trimmed.replace(/^\/queue\s*/i, "").trim();
  if (!rest) throw new Error("Usage: /queue <list|approve|reject|rollback> ...");

  const firstToken = rest.split(/\s+/)[0];
  const op = (firstToken || "").toLowerCase();
  const tail = rest.slice(firstToken ? firstToken.length : 0).trim();

  if (op === "list") {
    const flags = tail.split(/\s+/).filter(Boolean);
    let status: string | undefined;
    let jsonl = false;
    for (let i = 0; i < flags.length; i += 1) {
      const token = flags[i]!;
      if (token === "--jsonl") {
        jsonl = true;
        continue;
      }
      if (token.startsWith("--status=")) {
        status = token.slice("--status=".length);
        continue;
      }
      if (token === "--status") {
        const next = flags[i + 1];
        if (!next) throw new Error("Usage: /queue list --status <status>");
        status = next;
        i += 1;
        continue;
      }
      throw new Error(`Unknown flag for /queue list: ${token}`);
    }
    return { kind: "QueueList", status, jsonl };
  }

  if (op === "approve") {
    const execution_id = tail.split(/\s+/)[0];
    if (!execution_id) throw new Error("Usage: /queue approve <execution_id>");
    return { kind: "QueueApprove", execution_id };
  }

  if (op === "rollback") {
    const execution_id = tail.split(/\s+/)[0];
    if (!execution_id) throw new Error("Usage: /queue rollback <execution_id>");
    return { kind: "QueueRollback", execution_id };
  }

  if (op === "reject") {
    const firstSpace = tail.indexOf(" ");
    const execution_id = firstSpace === -1 ? tail : tail.slice(0, firstSpace);
    const reasonText = firstSpace === -1 ? "" : tail.slice(firstSpace + 1);
    if (!execution_id) throw new Error("Usage: /queue reject <execution_id> <reason>");
    const reason = parseQuotedOrRaw(reasonText);
    if (!reason || typeof reason !== "string") {
      throw new Error("Usage: /queue reject <execution_id> <reason>");
    }
    return { kind: "QueueReject", execution_id, reason };
  }

  throw new Error(`Unknown /queue op: ${op}`);
}

function parseRunCommand(command: string):
  | { kind: "RunShow"; execution_id: string }
  | { kind: "RunArtifacts"; execution_id: string }
  | { kind: "RunTail"; execution_id: string }
  | null {
  const trimmed = command.trim();
  const match = trimmed.match(/^\/run\s+(show|artifacts|tail)\s+(\S+)\s*$/i);
  if (!match) return null;
  const op = match[1]!.toLowerCase();
  const execution_id = match[2]!;
  if (op === "show") return { kind: "RunShow", execution_id };
  if (op === "artifacts") return { kind: "RunArtifacts", execution_id };
  if (op === "tail") return { kind: "RunTail", execution_id };
  return null;
}

function inferQueueMode(state: Record<string, unknown>) {
  const kind = typeof state.kind === "string" ? state.kind : null;
  const pending = Array.isArray(state.pending_step_ids) ? state.pending_step_ids.length : 0;
  if (kind === "ApprovalRequiredBatch" || pending > 1) return "BATCH_APPROVAL" as const;
  return "APPROVAL_GATED" as const;
}

function loadApprovalQueue() {
  const dir = approvalsDir();
  if (!fs.existsSync(dir)) return [];

  const items = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const full = path.join(dir, f);
      try {
        const state = readJsonFile(full);
        if (!isRecord(state)) return null;
        const execution_id = typeof state.execution_id === "string" ? state.execution_id : f.replace(/\.json$/, "");
        const status = typeof state.status === "string" ? state.status : "unknown";
        if (status !== "awaiting_approval") return null;
        const plan_hash = typeof state.plan_hash === "string" ? state.plan_hash : null;
        const created_at = typeof state.created_at === "string" ? state.created_at : null;
        const mode = inferQueueMode(state);
        const plan = state.plan;
        const goal = isRecord(plan) && typeof plan.goal === "string" ? plan.goal : null;
        const pending_step_ids = Array.isArray(state.pending_step_ids)
          ? state.pending_step_ids.map(String).filter(Boolean)
          : [];

        const summary = goal
          ? goal
          : pending_step_ids.length > 1
            ? `Approval pending (${pending_step_ids.length} steps)`
            : "Approval pending";

        return { execution_id, status, plan_hash, created_at, mode, summary };
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  return items as Array<{
    execution_id: string;
    status: string;
    plan_hash: string | null;
    created_at: string | null;
    mode: "BATCH_APPROVAL" | "APPROVAL_GATED";
    summary: string;
  }>;
}

function readReceiptsTimeline(execution_id: string) {
  const file = path.join(process.cwd(), "runs", "receipts.jsonl");
  if (!fs.existsSync(file)) return [];
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split(/\r?\n/).filter(Boolean);
  const events: Array<{ timestamp: string; event: string }> = [];
  for (const line of lines) {
    try {
      const json = JSON.parse(line);
      if (!isRecord(json)) continue;
      if (json.execution_id !== execution_id) continue;
      const timestamp =
        typeof json.finished_at === "string"
          ? json.finished_at
          : typeof json.started_at === "string"
            ? json.started_at
            : null;
      if (!timestamp) continue;
      const event =
        typeof (json as any).kind === "string"
          ? String((json as any).kind)
          : typeof json.status === "string"
            ? String(json.status)
            : "unknown";
      events.push({ timestamp, event });
    } catch {
      // ignore unreadable lines
    }
  }
  return events;
}

function scanArtifactIndex(execution_id: string) {
  const runsDir = path.join(process.cwd(), "runs");
  const out: Array<{ type: string; path: string }> = [];

  const addFile = (type: string, fullPath: string) => {
    out.push({ type, path: fullPath.replace(/\\/g, "/") });
  };

  if (!fs.existsSync(runsDir)) return out;
  const children = fs.readdirSync(runsDir);
  for (const child of children) {
    const full = path.join(runsDir, child);
    let stat: fs.Stats;
    try {
      stat = fs.statSync(full);
    } catch {
      continue;
    }
    if (!stat.isDirectory()) continue;

    const type = child === "approvals" ? "approval" : child;
    const files = fs.readdirSync(full);
    for (const f of files) {
      if (!f) continue;
      const isApproval = child === "approvals" && f === `${execution_id}.json`;
      const isPrefixed = f.startsWith(`${execution_id}.`);
      if (!isApproval && !isPrefixed) continue;
      addFile(type, path.join(full, f));
    }
  }

  return out.sort((a, b) => {
    if (a.type !== b.type) return a.type.localeCompare(b.type);
    return a.path.localeCompare(b.path);
  });
}

function loadRunArtifacts(execution_id: string) {
  const out: string[] = [];

  const addMatches = (dir: string, prefix: string) => {
    if (!fs.existsSync(dir)) return;
    for (const f of fs.readdirSync(dir)) {
      if (f.startsWith(prefix)) {
        out.push(path.join(dir, f).replace(/\\/g, "/"));
      }
    }
  };

  addMatches(path.join(process.cwd(), "runs", "prestate"), `${execution_id}.`);
  addMatches(path.join(process.cwd(), "runs", "rollback"), `${execution_id}.`);

  // Also include the approval state file if present.
  const ap = approvalPath(execution_id);
  if (fs.existsSync(ap)) out.push(ap.replace(/\\/g, "/"));

  return out.sort((a, b) => a.localeCompare(b));
}

async function markRunRejected(execution_id: string, reason: string) {
  const p = approvalPath(execution_id);
  if (!fs.existsSync(p)) {
    throw new Error(`No approval state found for execution_id '${execution_id}'`);
  }

  const state = readJsonFile(p);
  if (!isRecord(state)) {
    throw new Error(`Invalid approval state JSON for execution_id '${execution_id}'`);
  }

  const status = typeof state.status === "string" ? state.status : "unknown";
  if (status !== "awaiting_approval") {
    throw new Error(`Cannot reject execution_id '${execution_id}': status is '${status}', expected 'awaiting_approval'`);
  }

  const rejected_at = nowIso();
  const next = {
    ...state,
    status: "rejected",
    rejected_at,
    rejection_reason: reason,
  };

  writeJsonFile(p, next);

  const goal = isRecord(state.plan) && typeof (state.plan as any).goal === "string" ? (state.plan as any).goal : "Rejected approval";
  const threadId = isRecord(state.plan) && typeof (state.plan as any).threadId === "string" ? (state.plan as any).threadId : "exec_live_001";
  const plan_hash = typeof state.plan_hash === "string" ? state.plan_hash : null;

  const runLog = {
    execution_id,
    threadId,
    goal,
    dry_run: false,
    plan_hash: plan_hash ?? undefined,
    started_at: rejected_at,
    finished_at: rejected_at,
    status: "rejected",
    agent_versions:
      isRecord(state.plan) && isRecord((state.plan as any).agent_versions)
        ? ((state.plan as any).agent_versions as Record<string, string>)
        : undefined,
    steps: [],
  };

  // Lazy import so read-only operator views do not require executor/planner modules.
  const { persistRun } = await import("../persist/persistRun.js");
  await persistRun(runLog as any);

  const out = { kind: "RunRejected" as const, execution_id, reason };
  return assertValid(RunRejectedSchema, out);
}

function delegateToEngine(command: string) {
  const entry = path.join(process.cwd(), "src", "cli", "run-command.ts");

  const tsxBin = path.join(process.cwd(), "node_modules", ".bin", "tsx");
  const tsxNodeEntrypoint = path.join(process.cwd(), "node_modules", "tsx", "dist", "cli.mjs");

  const res = process.platform === "win32"
    ? spawnSync(process.execPath, [tsxNodeEntrypoint, entry, command], {
        env: process.env,
        encoding: "utf8",
      })
    : spawnSync(tsxBin, [entry, command], {
        env: process.env,
        encoding: "utf8",
      });

  if (res.error) throw new Error(res.error.message);
  const stdout = String(res.stdout ?? "").trim();
  if (!stdout) throw new Error("Engine produced no output");
  process.stdout.write(stdout);
  process.exit(res.status ?? 0);
}

async function main() {
  const command = getArgCommand();

  {
    const threadId = (process.env.THREAD_ID || "local_test_001").trim();
    const now_iso = fixedNowIso();
    const denied = enforceCliCredits({ now_iso, threadId, command, domain_id: null });
    if (denied) {
      console.log(JSON.stringify(denied, null, 0));
      process.exitCode = 1;
      return;
    }
  }

  const q = parseQueueCommand(command);
  if (q) {
    if (q.kind === "QueueList") {
      const all = loadApprovalQueue();
      const filtered = typeof q.status === "string" && q.status.trim()
        ? all.filter((i) => i.status === q.status)
        : all;

      const pending = filtered.sort((a, b) => a.execution_id.localeCompare(b.execution_id));

      if (q.jsonl) {
        for (const item of pending) {
          const line = assertValid(QueueItemJsonlSchema, {
            execution_id: item.execution_id,
            status: item.status,
            plan_hash: item.plan_hash,
          });
          process.stdout.write(JSON.stringify(line) + "\n");
        }
        return;
      }

      const out = assertValid(QueueListSchema, { kind: "QueueList", schema_version: SCHEMA_VERSION, pending });
      console.log(JSON.stringify(out, null, 2));
      return;
    }
    if (q.kind === "QueueApprove") {
      delegateToEngine(`/approve ${q.execution_id}`);
      return;
    }
    if (q.kind === "QueueRollback") {
      delegateToEngine(`/rollback ${q.execution_id}`);
      return;
    }
    if (q.kind === "QueueReject") {
      const out = await markRunRejected(q.execution_id, q.reason);
      console.log(JSON.stringify(out, null, 2));
      return;
    }
  }

  const r = parseRunCommand(command);
  if (r) {
    const p = approvalPath(r.execution_id);
    if (!fs.existsSync(p)) {
      throw new Error(`No approval state found for execution_id '${r.execution_id}'`);
    }

    const state = readJsonFile(p);
    if (!isRecord(state)) throw new Error("Invalid approval state JSON");

    if (r.kind === "RunArtifacts") {
      const artifacts = scanArtifactIndex(r.execution_id);
      const out = assertValid(ArtifactIndexSchema, {
        kind: "ArtifactIndex",
        schema_version: SCHEMA_VERSION,
        execution_id: r.execution_id,
        artifacts,
      });
      console.log(JSON.stringify(out, null, 2));
      return;
    }

    if (r.kind === "RunTail") {
      const events = readReceiptsTimeline(r.execution_id);
      const out = assertValid(RunTimelineSchema, {
        kind: "RunTimeline",
        schema_version: SCHEMA_VERSION,
        execution_id: r.execution_id,
        events,
      });
      console.log(JSON.stringify(out, null, 2));
      return;
    }

    // RunShow: full snapshot.
    const prestates = isRecord(state.prestates) ? (state.prestates as Record<string, any>) : {};
    const prestate = Object.entries(prestates)
      .map(([step_id, v]) => {
        const fp = isRecord(v) && typeof v.fingerprint === "string" ? v.fingerprint : null;
        if (!fp) return null;
        return {
          step_id,
          fingerprint: fp,
          artifact: path.join(process.cwd(), "runs", "prestate", `${r.execution_id}.${step_id}.json`).replace(/\\/g, "/"),
        };
      })
      .filter(Boolean) as Array<{ step_id: string; fingerprint: string; artifact: string }>;

    const plan = isRecord(state.plan) ? (state.plan as Record<string, unknown>) : null;
    const agent_versions = plan && isRecord((plan as any).agent_versions) ? ((plan as any).agent_versions as Record<string, string>) : undefined;

    const pending_step_ids = Array.isArray(state.pending_step_ids)
      ? state.pending_step_ids.map(String).filter(Boolean)
      : [];

    const artifacts = Array.from(
      new Set([
        ...loadRunArtifacts(r.execution_id),
        ...prestate.map((p) => p.artifact),
      ])
    ).sort((a, b) => a.localeCompare(b));

    const out = assertValid(RunDetailsSchema, {
      kind: "RunDetails",
      schema_version: SCHEMA_VERSION,
      execution_id: r.execution_id,
      status: typeof state.status === "string" ? state.status : null,
      plan_hash: typeof state.plan_hash === "string" ? state.plan_hash : null,
      mode: inferQueueMode(state),
      pending_step_ids,
      agent_versions,
      prestate,
      artifacts,
    });

    console.log(JSON.stringify(out, null, 2));
    return;
  }

  throw new Error("Unknown console command");
}

main().catch((e) => {
  const msg = e instanceof Error ? e.message : String(e);
  console.log(JSON.stringify({ kind: "CliError", code: "CONSOLE_ERROR", reason: msg }, null, 2));
  process.exitCode = 1;
});
