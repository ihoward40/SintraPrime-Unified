import path from "node:path";
import { spawnSync } from "node:child_process";
import { parseDomainPrefix } from "../domains/parseDomainPrefix.js";
import { startOperatorUiServer } from "../operator-ui/server.js";
import { nowIso as fixedNowIso } from "../utils/clock.js";
import { enforceCliCredits } from "../credits/enforceCliCredits.js";

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function getArgCommand() {
  const raw = process.argv.slice(2).join(" ").trim();
  if (!raw) throw new Error("Missing command argument");
  return raw;
}

function nowIso() {
  return new Date().toISOString();
}

type CliRunResult = {
  exitCode: number;
  stdout: string;
  stderr: string;
  json: unknown | null;
};

function runEngineCli(command: string): CliRunResult {
  const trimmed = String(command ?? "").trim();

  const entry = /^(\/queue\b|\/run\b)/i.test(trimmed)
    ? path.join(process.cwd(), "src", "cli", "run-console.ts")
    : /^\/scheduler\b/i.test(trimmed)
      ? path.join(process.cwd(), "src", "cli", "run-scheduler.ts")
      : /^\/policy\b/i.test(trimmed)
        ? path.join(process.cwd(), "src", "cli", "run-policy.ts")
        : /^\/operator\b/i.test(trimmed)
          ? path.join(process.cwd(), "src", "cli", "run-operator.ts")
          : path.join(process.cwd(), "src", "cli", "run-command.ts");

  const tsxNodeEntrypoint = path.join(process.cwd(), "node_modules", "tsx", "dist", "cli.mjs");

  const res = spawnSync(process.execPath, [tsxNodeEntrypoint, entry, command], {
    env: process.env,
    encoding: "utf8",
    windowsHide: true,
  });

  if (res.error) throw new Error(res.error.message);

  const stdout = String(res.stdout ?? "").trim();
  const stderr = String(res.stderr ?? "").trim();

  let json: unknown | null = null;
  if (stdout) {
    try {
      json = JSON.parse(stdout);
    } catch {
      json = null;
    }
  }

  return { exitCode: res.status ?? 0, stdout, stderr, json };
}

type OperatorUiQueueRow = {
  rank: number;
  job_id: string;
  command: string;
  confidence: { score: number; band: string; action: string };
  status: "REGRESSION" | "AWAITING_APPROVAL" | "AUTO_RUNNABLE" | "HISTORICAL" | "OTHER";
  reason: string;
  last_activity_at: string | null;
  actions: Array<"VIEW_DETAILS" | "SIMULATE" | "APPROVE" | "ACK_REGRESSION" | "ROLLBACK" | "REFRESH">;
};

function computeRow(job: any): OperatorUiQueueRow {
  const job_id = typeof job?.job_id === "string" ? job.job_id : "unknown";
  const command = typeof job?.command === "string" ? job.command : "";
  const confidence = {
    score: typeof job?.confidence?.score === "number" ? job.confidence.score : 0,
    band: typeof job?.confidence?.band === "string" ? job.confidence.band : "LOW",
    action: typeof job?.confidence?.action === "string" ? job.confidence.action : "HUMAN_REVIEW_REQUIRED",
  };

  const regressed = Boolean(job?.regression?.regressed);
  const requiresAck = Boolean(job?.regression?.requires_ack);
  const acknowledged = Boolean(job?.regression?.acknowledged);

  const policyReason = typeof job?.policy_state?.reason === "string" ? job.policy_state.reason : "UNKNOWN";
  const policyAllowed = Boolean(job?.policy_state?.allowed);

  const last_activity_at = typeof job?.last_run?.at === "string" ? job.last_run.at : null;

  let status: OperatorUiQueueRow["status"] = "OTHER";
  if (regressed && requiresAck && !acknowledged) status = "REGRESSION";
  else if (policyReason === "APPROVAL_REQUIRED") status = "AWAITING_APPROVAL";
  else if (policyAllowed && confidence.action === "AUTO_RUN") status = "AUTO_RUNNABLE";
  else if (job?.last_run?.status === "success") status = "HISTORICAL";

  const reason = status === "REGRESSION"
    ? "CONFIDENCE_REGRESSION_UNACKNOWLEDGED"
    : status === "AWAITING_APPROVAL"
      ? "APPROVAL_REQUIRED"
      : policyReason;

  const actions: OperatorUiQueueRow["actions"] = ["VIEW_DETAILS", "SIMULATE", "REFRESH"];
  if (status === "AWAITING_APPROVAL") actions.push("APPROVE");
  if (status === "REGRESSION") actions.push("ACK_REGRESSION");

  // Rollback is only meaningful if an execution_id exists and rollback artifacts exist;
  // the UI will still map 1:1 to /rollback, but we keep it hidden by default here.

  const rank = typeof job?.rank === "number" ? job.rank : 0;

  return {
    rank,
    job_id,
    command,
    confidence,
    status,
    reason,
    last_activity_at,
    actions,
  };
}

function parseOperatorUiCommand(command: string):
  | { kind: "Queue" }
  | { kind: "Approve"; execution_id: string }
  | { kind: "Stats" }
  | { kind: "Job"; job_id: string }
  | { kind: "Simulate"; inner: string; flags: string[] }
  | { kind: "WebServe"; port: number | null }
  | { kind: "WebSelftest"; command: string }
  | null {
  const trimmed = String(command ?? "").trim();
  if (!/^\/operator-ui\b/i.test(trimmed)) return null;

  const rest = trimmed.replace(/^\/operator-ui\s*/i, "").trim();
  const firstSpace = rest.indexOf(" ");
  const op = (firstSpace === -1 ? rest : rest.slice(0, firstSpace)).trim().toLowerCase();
  const tail = (firstSpace === -1 ? "" : rest.slice(firstSpace + 1)).trim();

  if (!op || op === "queue") return { kind: "Queue" };
  if (op === "approve") {
    const execution_id = tail.split(/\s+/)[0];
    if (!execution_id) throw new Error("Usage: /operator-ui approve <execution_id>");
    return { kind: "Approve", execution_id };
  }
  if (op === "stats") return { kind: "Stats" };
  if (op === "job") {
    const job_id = tail.split(/\s+/)[0];
    if (!job_id) throw new Error("Usage: /operator-ui job <job_id>");
    return { kind: "Job", job_id };
  }
  if (op === "simulate") {
    if (!tail) throw new Error("Usage: /operator-ui simulate <command> [--at ...] [--autonomy ...] [--approval true|false]");
    // Forward exactly to /policy simulate.
    const tokens = tail.split(/\s+/);
    const innerTokens: string[] = [];
    const flags: string[] = [];
    for (let i = 0; i < tokens.length; i += 1) {
      const t = tokens[i]!;
      if (t === "--at" || t === "--autonomy" || t === "--approval") {
        const v = tokens[i + 1];
        if (!v) throw new Error("simulate flags require a value");
        flags.push(t, v);
        i += 1;
        continue;
      }
      innerTokens.push(t);
    }
    return { kind: "Simulate", inner: innerTokens.join(" "), flags };
  }

  if (op === "web") {
    const restTokens = tail.split(/\s+/).filter(Boolean);
    const sub = (restTokens[0] || "serve").toLowerCase();

    if (sub === "serve") {
      const portMatch = tail.match(/--port\s+(\d+)/i);
      const port = portMatch?.[1] ? Number(portMatch[1]) : null;
      if (port !== null && (!Number.isFinite(port) || port <= 0 || port >= 65536)) {
        throw new Error("Usage: /operator-ui web serve [--port <1-65535>]");
      }
      return { kind: "WebServe", port };
    }

    if (sub === "selftest") {
      const cmdMatch = tail.match(/--command\s+([\s\S]+)$/i);
      const cmd = String(cmdMatch?.[1] || "/operator stats").trim();
      if (!cmd.startsWith("/")) throw new Error("Usage: /operator-ui web selftest [--command /...]");
      return { kind: "WebSelftest", command: cmd };
    }

    throw new Error("Usage: /operator-ui web serve [--port <1-65535>] | /operator-ui web selftest [--command /...]");
  }

  return null;
}

function mustJson(out: CliRunResult, label: string) {
  if (out.json === null) {
    throw new Error(`${label} did not produce JSON. exit=${out.exitCode} stderr=${out.stderr.slice(0, 200)}`);
  }
  return out.json;
}

function asOperatorQueue(json: unknown): any {
  if (!isRecord(json) || json.kind !== "OperatorQueue") throw new Error("Expected OperatorQueue JSON");
  return json;
}

(async () => {
  try {
    const raw = getArgCommand();
    const domainPrefix = parseDomainPrefix(raw);
    const command = domainPrefix?.inner_command ?? raw;
    const domain_id = domainPrefix?.domain_id ?? null;

    {
      const threadId = (process.env.THREAD_ID || "local_test_001").trim();
      const now_iso = fixedNowIso();
      const denied = enforceCliCredits({ now_iso, threadId, command: raw, domain_id });
      if (denied) {
        console.log(JSON.stringify(denied, null, 0));
        process.exitCode = 1;
        return;
      }
    }

    const parsed = parseOperatorUiCommand(command);
    if (!parsed) {
      throw new Error(
        "Usage: /operator-ui [queue] | /operator-ui approve <execution_id> | /operator-ui job <job_id> | /operator-ui simulate <command> [...] | /operator-ui stats"
      );
    }

    if (parsed.kind === "Queue") {
      const q = asOperatorQueue(mustJson(runEngineCli("/operator queue"), "/operator queue"));
      const jobs = Array.isArray(q.jobs) ? q.jobs : [];
      const rows = jobs.map(computeRow);
      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiQueue",
            generated_at: nowIso(),
            source: { kind: "OperatorQueue", generated_at: typeof q.generated_at === "string" ? q.generated_at : null },
            rows,
          },
          null,
          2
        )
      );
      process.exitCode = 0;
      return;
    }

    if (parsed.kind === "WebServe") {
      const handle = await startOperatorUiServer({ port: parsed.port ?? undefined });
      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiWebServer",
            generated_at: nowIso(),
            port: handle.port,
            url: `http://127.0.0.1:${handle.port}/`,
          },
          null,
          2
        )
      );

      // Keep process alive until terminated.
      await new Promise(() => {
        // intentionally never resolves
      });
      await handle.close();
      process.exitCode = 0;
      return;
    }

    if (parsed.kind === "WebSelftest") {
      const handle = await startOperatorUiServer({ port: 0 });
      const baseUrl = `http://127.0.0.1:${handle.port}`;

      const checks: Record<string, any> = {};
      try {
        const html = await (await fetch(`${baseUrl}/`)).text();
        checks.static_ok = html.includes("Operator Console");

        const approvals = (await (await fetch(`${baseUrl}/api/approvals`)).json()) as any;
        checks.approvals_kind = approvals?.kind;

        const receipts = (await (await fetch(`${baseUrl}/api/receipts?limit=1`)).json()) as any;
        checks.receipts_kind = receipts?.kind;

        const artifacts = (await (await fetch(`${baseUrl}/api/artifacts?prefix=runs&limit=1`)).json()) as any;
        checks.artifacts_kind = artifacts?.kind;

        const cmdRes = (await (
          await fetch(`${baseUrl}/api/command`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ message: parsed.command }),
          })
        ).json()) as any;
        checks.command_kind = cmdRes?.kind;
        checks.command_exit = cmdRes?.exitCode;
        checks.command_json_kind = cmdRes?.json?.kind ?? null;

        const ok =
          checks.static_ok === true &&
          checks.approvals_kind === "ApprovalsList" &&
          checks.receipts_kind === "ReceiptsTail" &&
          checks.artifacts_kind === "ArtifactsList" &&
          checks.command_kind === "OperatorUiCommandResult" &&
          checks.command_exit === 0;

        console.log(
          JSON.stringify(
            {
              kind: "OperatorUiWebSelftest",
              generated_at: nowIso(),
              ok,
              baseUrl,
              command: parsed.command,
              checks,
            },
            null,
            2
          )
        );
        process.exitCode = ok ? 0 : 1;
      } finally {
        await handle.close();
      }
      return;
    }

    if (parsed.kind === "Approve") {
      const beforeQ = asOperatorQueue(mustJson(runEngineCli("/operator queue"), "/operator queue"));
      const beforeJobs = Array.isArray(beforeQ.jobs) ? beforeQ.jobs : [];
      const beforeHas = beforeJobs.some((j: any) => j && j.job_id === parsed.execution_id);

      const approveCmd = domain_id
        ? `/domain ${domain_id} /approve ${parsed.execution_id}`
        : `/approve ${parsed.execution_id}`;

      const approveOut = runEngineCli(approveCmd);
      const approveJson = mustJson(approveOut, "/approve");

      const afterQ = asOperatorQueue(mustJson(runEngineCli("/operator queue"), "/operator queue"));
      const afterJobs = Array.isArray(afterQ.jobs) ? afterQ.jobs : [];
      const afterHas = afterJobs.some((j: any) => j && j.job_id === parsed.execution_id);

      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiActionResult",
            generated_at: nowIso(),
            action: "APPROVE",
            execution_id: parsed.execution_id,
            approve_output: approveJson,
            ui_state_updated: beforeHas && !afterHas,
            queue_after: afterQ,
          },
          null,
          2
        )
      );
      process.exitCode = 0;
      return;
    }

    if (parsed.kind === "Stats") {
      const stats = mustJson(runEngineCli("/operator stats"), "/operator stats");
      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiStats",
            generated_at: nowIso(),
            stats,
          },
          null,
          2
        )
      );
      process.exitCode = 0;
      return;
    }

    if (parsed.kind === "Job") {
      const job = mustJson(runEngineCli(`/operator job ${parsed.job_id}`), "/operator job");
      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiJob",
            generated_at: nowIso(),
            job,
          },
          null,
          2
        )
      );
      process.exitCode = 0;
      return;
    }

    if (parsed.kind === "Simulate") {
      const cmd = ["/policy simulate", parsed.inner, ...parsed.flags].join(" ").trim();
      const sim = mustJson(runEngineCli(cmd), "/policy simulate");
      console.log(
        JSON.stringify(
          {
            kind: "OperatorUiSimulation",
            generated_at: nowIso(),
            request: { command: parsed.inner, flags: parsed.flags },
            simulation: sim,
          },
          null,
          2
        )
      );
      process.exitCode = 0;
      return;
    }
  } catch (err: any) {
    process.exitCode = 1;
    console.error(err?.message ? String(err.message) : String(err));
  }
})();
