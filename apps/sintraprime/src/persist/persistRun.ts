import type { ExecutionRunLog } from "../executor/executePlan.js";
import fs from "node:fs";
import path from "node:path";

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export async function persistRun(runLog: ExecutionRunLog) {
  const planVersion = process.env.PLAN_VERSION ?? "ExecutionPlan@1";
  const denied = runLog.status === "denied";
  const kindFromStatus = (s: unknown) => {
    if (s === "throttled") return "Throttled";
    return "RunReceipt";
  };

  const receipt = {
    kind: (runLog as any).kind ?? kindFromStatus(runLog.status),
    execution_id: runLog.execution_id,
    threadId: runLog.threadId,
    status: runLog.status,
    fingerprint: (runLog as any).fingerprint ?? null,
    autonomy_mode: (runLog as any).autonomy_mode ?? null,
    autonomy_mode_effective: (runLog as any).autonomy_mode_effective ?? null,
    throttle_reason: (runLog as any).throttle_reason ?? null,
    retry_after: (runLog as any).retry_after ?? null,
    receipt_hash: runLog.receipt_hash ?? null,
    plan_hash: (runLog as any).plan_hash ?? null,
    started_at: runLog.started_at,
    finished_at: runLog.finished_at ?? null,
    plan_version: planVersion,
    agent_versions: runLog.agent_versions ?? null,
    resolved_capabilities: runLog.resolved_capabilities ?? null,
    phases_planned: runLog.phases_planned ?? null,
    phases_executed: runLog.phases_executed ?? null,
    denied_phase: runLog.denied_phase ?? null,
    policy_code: runLog.policy_denied?.code ?? null,
    artifacts: runLog.artifacts ?? null,
    policy_denied: runLog.policy_denied ?? null,
    approval_required: (runLog as any).approval_required ?? null,
    policy: {
      checked: true,
      denied,
      code: runLog.policy_denied?.code ?? null,
    },
  };

  // Allow custom receipts to attach structured payloads without expanding the
  // base RunReceipt schema. This supports Tier-22.* deterministic receipts.
  const extra = (runLog as any).receipt;
  if (isRecord(extra)) {
    const reserved = new Set([
      "kind",
      "execution_id",
      "threadId",
      "status",
      "fingerprint",
      "autonomy_mode",
      "autonomy_mode_effective",
      "throttle_reason",
      "retry_after",
      "receipt_hash",
      "plan_hash",
      "started_at",
      "finished_at",
      "plan_version",
      "agent_versions",
      "resolved_capabilities",
      "phases_planned",
      "phases_executed",
      "denied_phase",
      "policy_code",
      "artifacts",
      "policy_denied",
      "approval_required",
      "policy",
    ]);

    for (const [k, v] of Object.entries(extra)) {
      if (reserved.has(k)) continue;
      (receipt as any)[k] = v;
    }
  }

  const persistLocal = process.env.PERSIST_LOCAL_RECEIPTS === "1";

  const writeLocal = () => {
    const runsDir = path.join(process.cwd(), "runs");
    fs.mkdirSync(runsDir, { recursive: true });
    const file = path.join(runsDir, "receipts.jsonl");
    fs.appendFileSync(file, `${JSON.stringify(receipt)}\n`, { encoding: "utf8" });
  };

  const url = process.env.NOTION_RUNS_WEBHOOK;
  if (!url) {
    writeLocal();
    return;
  }

  if (persistLocal) {
    writeLocal();
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Keep the Notion payload small and stable.
    body: JSON.stringify(receipt),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`persistRun failed (${res.status}): ${text}`);
  }
}
