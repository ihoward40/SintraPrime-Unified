import type { ExecutionPlan, ExecutionStep } from "../schemas/ExecutionPlan.schema.js";
import { ExecutionPlanSchema } from "../schemas/ExecutionPlan.schema.js";
import crypto from "node:crypto";
import { computePlanHash } from "../utils/planHash.js";
import { proposeStatus } from "../analysis/proposeStatus.js";
import { notionLiveGet, notionLiveWhoAmI } from "../adapters/notionLiveRead.js";
import { notionLivePatchWithIdempotency } from "../adapters/notionLiveWrite.js";
import { writeNotionLiveWriteArtifact } from "../artifacts/writeNotionLiveWriteArtifact.js";
import { writeDocsCaptureArtifact } from "../artifacts/writeDocsCaptureArtifact.js";
import { writeBrowserOperatorArtifact } from "../artifacts/writeBrowserOperatorArtifact.js";
import { getIdempotencyRecord, writeIdempotencyRecord } from "../idempotency/idempotencyLedger.js";
import { runBrowserOperatorStep } from "../browserOperator/runBrowserOperator.js";
import { browserL0DomExtract, browserL0Navigate, browserL0Screenshot } from "../browserOperator/l0.js";
import { evidenceRollupSha256 } from "../receipts/evidenceRollup.js";
import { evaluateGuards, pinnedInputSha256 } from "../guards/index.js";

type RunStatus =
  | "running"
  | "success"
  | "failed"
  | "denied"
  | "awaiting_approval"
  | "rejected"
  | "throttled";

type StepStatus = "success" | "failed" | "skipped";

export type StepRunLog = {
  step_id: string;
  action: string;
  adapter: ExecutionStep["adapter"];
  method: ExecutionStep["method"];
  url: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
  status: StepStatus;
  http_status: number | null;
  response: unknown;
  guard?: ReturnType<typeof evaluateGuards>;
  expectations: {
    http_status_expected: number[];
    http_status_ok: boolean;
    json_paths_present?: string[];
    json_paths_ok?: boolean;
  };
  error?: string;
  watch?: {
    enabled?: boolean;
    phases?: string[];
    screenshots?: Array<{
      system: string;
      path: string;
      sha256: string;
      captured_at: string;
    }>;
  };
};

function maybeEvaluateStepGuards(step: ExecutionStep, stepOut: unknown) {
  const payload = (step as any).payload;
  if (!payload || typeof payload !== "object") return null;

  const guard = (payload as any).guard ?? null;
  const src = guard && typeof guard === "object" ? guard : payload;

  const mode = (src as any).guard_mode;
  if (mode !== "CODE_IS_SOURCE" && mode !== "GROUNDED_OUTPUT") return null;

  const renderedPrompt = (src as any).rendered_prompt;
  const pinnedInputText = (src as any).pinned_input_text;
  const strict = (src as any).strict === true;

  if (typeof renderedPrompt !== "string" || typeof pinnedInputText !== "string") return null;

  const pinnedCode = typeof (src as any).pinned_code === "string" ? (src as any).pinned_code : undefined;
  const inputTextForGrounding =
    typeof (src as any).input_text_for_grounding === "string" ? (src as any).input_text_for_grounding : undefined;

  return evaluateGuards({
    mode,
    strict,
    renderedPrompt,
    pinnedInputText,
    pinnedInputSha: pinnedInputSha256(pinnedInputText),
    stepOut,
    pinnedCode,
    inputTextForGrounding,
  });
}

export type ExecutePlanOptions = {
  onStepFinished?: (args: {
    plan: ExecutionPlan;
    step: ExecutionStep;
    stepLog: StepRunLog;
  }) => Promise<void> | void;
};

export type ExecutionRunLog = {
  execution_id: string;
  threadId: string;
  goal: string;
  dry_run: boolean;
  plan_hash?: string;
  started_at: string;
  finished_at?: string;
  status: RunStatus;
  failed_step?: string;
  error?: string;
  receipt_hash?: string;
  agent_versions?: Record<string, string>;
  resolved_capabilities?: Record<string, string>;
  phases_planned?: string[];
  phases_executed?: string[];
  denied_phase?: string;
  artifacts?: Record<
    string,
    {
      outputs: Record<string, unknown>;
      files?: string[];
      metadata: { started_at: string; finished_at: string };
    }
  >;
  policy_denied?: { code: string; reason: string };
  approval_required?: unknown;
  steps: StepRunLog[];
};

function computeReceiptHash(runLog: ExecutionRunLog) {
  // Hash the final run log as an execution receipt.
  // Note: timestamps are included, so receipts differ per run (intended).
  const payload = JSON.stringify(runLog);
  return crypto.createHash("sha256").update(payload).digest("hex");
}

function deriveIdempotencyKey(input: {
  action: string;
  plan_hash: string;
  step_id: string;
  threadId: string;
}) {
  const payload = `${input.action}|${input.plan_hash}|${input.step_id}|${input.threadId}`;
  return crypto.createHash("sha256").update(payload).digest("hex");
}

function getTimeoutMs() {
  const raw = process.env.DEFAULT_STEP_TIMEOUT_MS;
  if (!raw) return 30_000;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : 30_000;
}

function getMaxRuntimeMs() {
  const raw = process.env.POLICY_MAX_RUNTIME_MS;
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function methodAllowsBody(method: string) {
  return method !== "GET" && method !== "HEAD";
}

function hasHeader(headers: Record<string, string>, headerName: string) {
  const wanted = headerName.toLowerCase();
  return Object.keys(headers).some((k) => k.toLowerCase() === wanted);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function normalizeEvidenceOnReceiptResponse(response: unknown): unknown {
  if (!isPlainObject(response)) return response;
  const evidence = (response as any).evidence;
  if (!Array.isArray(evidence) || evidence.length === 0) return response;

  const hasRollup = typeof (response as any).evidence_rollup_sha256 === "string";
  if (hasRollup) return response;

  // Best-effort: rollup only if evidence items look like ArtifactRef.
  const okShape = evidence.every(
    (e: any) =>
      e &&
      typeof e === "object" &&
      typeof e.path === "string" &&
      typeof e.sha256 === "string" &&
      typeof e.mime === "string" &&
      typeof e.bytes === "number"
  );
  if (!okShape) return response;

  const rollup = evidenceRollupSha256(evidence as any);
  return { ...response, evidence, evidence_rollup_sha256: rollup };
}

function getNestedString(root: unknown, keys: string[]): string | null {
  let cur: any = root;
  for (const k of keys) {
    if (!cur || typeof cur !== "object") return null;
    cur = cur[k];
  }
  return typeof cur === "string" ? cur : null;
}

function tryParseJson(text: string): unknown | null {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}


// Minimal JSON path resolver supporting: a.b.c and a[0].b
function getByPath(root: unknown, path: string): unknown {
  if (!path) return undefined;
  const normalized = path.startsWith("$") ? path.replace(/^\$\.?/, "") : path;
  const tokens: Array<string | number> = [];

  // tokenize: split by dots, but also parse [index]
  for (const part of normalized.split(".")) {
    if (!part) continue;
    const re = /([^[\]]+)|(\[(\d+)\])/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(part))) {
      if (m[1]) tokens.push(m[1]);
      if (m[3]) tokens.push(Number(m[3]));
    }
  }

  let cur: any = root;
  for (const t of tokens) {
    if (cur === null || cur === undefined) return undefined;
    cur = cur[t as any];
  }
  return cur;
}

function validateRequiredSecrets(plan: ExecutionPlan) {
  const missing = plan.required_secrets
    .filter((s) => s.source === "env")
    .map((s) => s.name)
    .filter((name) => !process.env[name] || String(process.env[name]).trim() === "");

  return missing;
}

async function executeStep(step: ExecutionStep, timeoutMs: number) {
  const headers: Record<string, string> = { ...(step.headers ?? {}) };

  if (step.idempotency_key && !hasHeader(headers, "Idempotency-Key")) {
    headers["Idempotency-Key"] = step.idempotency_key;
  }

  const method = step.method;

  let body: string | undefined;
  if (methodAllowsBody(method) && step.payload !== undefined && step.payload !== null) {
    if (typeof step.payload === "string") {
      body = step.payload;
    } else {
      if (!hasHeader(headers, "Content-Type")) {
        headers["Content-Type"] = "application/json";
      }
      body = JSON.stringify(step.payload);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(step.url, {
      method,
      headers,
      body,
      signal: controller.signal,
    });

    const text = await res.text();
    const contentType = res.headers.get("content-type") ?? "";
    const json = contentType.includes("application/json") ? tryParseJson(text) : tryParseJson(text);

    return {
      ok: res.ok,
      status: res.status,
      response: json ?? text,
      responseJson: json,
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function executeBrowserOperator(step: ExecutionStep, execution_id: string) {
  const out = await runBrowserOperatorStep({
    execution_id,
    step_id: step.step_id,
    url: step.url,
    payload: (step as any).payload,
  });

  if (out.ok && out.status >= 200 && out.status < 300) {
    try {
      const responseObj = (out.responseJson && typeof out.responseJson === "object") ? (out.responseJson as any) : null;
      const outputs = responseObj && responseObj.outputs && typeof responseObj.outputs === "object" ? responseObj.outputs : {};
      const screenshots = Array.isArray(out.screenshots) ? out.screenshots : [];

      let mode: "offline" | "network" = "offline";
      try {
        const proto = new URL(step.url).protocol;
        mode = proto === "http:" || proto === "https:" ? "network" : "offline";
      } catch {
        // Default offline (best-effort)
      }

      writeBrowserOperatorArtifact({
        execution_id,
        step_id: step.step_id,
        url: step.url,
        mode,
        http_status: out.status,
        outputs,
        screenshots,
      });
    } catch {
      // Best-effort only; do not fail the step.
    }
  }

  return {
    ok: out.ok,
    status: out.status,
    response: out.response,
    responseJson: out.responseJson,
    screenshots: out.screenshots ?? [],
  };
}

async function executeDocsCaptureStep(step: ExecutionStep, timeoutMs: number, execution_id: string) {
  const headers: Record<string, string> = { ...(step.headers ?? {}) };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(step.url, {
      method: step.method,
      headers,
      signal: controller.signal,
    });

    const ab = await res.arrayBuffer();
    const buf = Buffer.from(ab);
    const sha256_hex = crypto.createHash("sha256").update(buf).digest("hex");
    const content_type = res.headers.get("content-type");

    const { metaFile, bodyFile } = writeDocsCaptureArtifact({
      execution_id,
      step_id: step.step_id,
      url: step.url,
      http_status: res.status,
      content_type,
      sha256_hex,
      body_bytes: buf,
    });

    const response = {
      sha256_hex,
      byte_length: buf.length,
      content_type,
      artifact: { metaFile, bodyFile },
    };

    return {
      ok: res.ok,
      status: res.status,
      response,
      responseJson: response,
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function executeBrowserL0Step(step: ExecutionStep, timeoutMs: number, execution_id: string) {
  const action = String(step.action || "");
  const url = step.url;
  const payload = (step as any).payload;

  if (action === "browser.l0.navigate") {
    return await browserL0Navigate({ execution_id, step_id: step.step_id, url, timeoutMs });
  }

  if (action === "browser.l0.screenshot") {
    const fullPage = payload && typeof payload === "object" ? (payload as any).fullPage : undefined;
    return await browserL0Screenshot({
      execution_id,
      step_id: step.step_id,
      url,
      timeoutMs,
      fullPage: typeof fullPage === "boolean" ? fullPage : undefined,
    });
  }

  if (action === "browser.l0.dom_extract") {
    const maxChars = payload && typeof payload === "object" ? (payload as any).maxChars : undefined;
    return await browserL0DomExtract({
      execution_id,
      step_id: step.step_id,
      url,
      timeoutMs,
      maxChars: typeof maxChars === "number" ? maxChars : undefined,
    });
  }

  throw new Error(`Unknown browser.l0 action: ${action}`);
}

export async function executePlan(rawPlan: unknown, opts: ExecutePlanOptions = {}): Promise<ExecutionRunLog> {
  const plan = ExecutionPlanSchema.parse(rawPlan);
  const nowIso = () => new Date().toISOString();

  const existingPlanHash = (rawPlan as any)?.plan_hash;
  const plan_hash =
    typeof existingPlanHash === "string" && existingPlanHash
      ? existingPlanHash
      : computePlanHash(plan);

  const runLog: ExecutionRunLog = {
    execution_id: plan.execution_id,
    threadId: plan.threadId,
    goal: plan.goal,
    dry_run: plan.dry_run,
    plan_hash,
    started_at: nowIso(),
    steps: [],
    status: "running",
  };

  try {
    if (!plan.dry_run) {
      const missing = validateRequiredSecrets(plan);
      if (missing.length) {
        runLog.status = "failed";
        runLog.error = `Missing required env secrets: ${missing.join(", ")}`;
        runLog.finished_at = nowIso();
        runLog.receipt_hash = computeReceiptHash(runLog);
        return runLog;
      }
    }

    const timeoutMs = getTimeoutMs();
    const maxRuntimeMs = getMaxRuntimeMs();
    const startedWall = Date.now();

    for (const step of plan.steps) {
      if (maxRuntimeMs !== null && Date.now() - startedWall > maxRuntimeMs) {
        runLog.status = "denied";
        runLog.policy_denied = {
          code: "POLICY_MAX_RUNTIME_MS",
          reason: `runtime budget exceeded (> ${maxRuntimeMs}ms)`,
        };
        runLog.error = runLog.policy_denied.reason;
        runLog.finished_at = nowIso();
        runLog.receipt_hash = computeReceiptHash(runLog);
        return runLog;
      }

      const stepStarted = nowIso();
      const start = Date.now();

      const stepLog: StepRunLog = {
        step_id: step.step_id,
        action: step.action,
        adapter: step.adapter,
        method: step.method,
        url: step.url,
        started_at: stepStarted,
        finished_at: stepStarted,
        duration_ms: 0,
        status: "skipped",
        http_status: null,
        response: null,
        expectations: {
          http_status_expected: step.expects.http_status,
          http_status_ok: false,
          json_paths_present: step.expects.json_paths_present,
          json_paths_ok: step.expects.json_paths_present ? false : undefined,
        },
      };

      try {
        if (plan.dry_run) {
          stepLog.status = "skipped";
          stepLog.response = { dry_run: true };
        } else {
          const out =
            step.action === "analysis.propose_status"
              ? {
                  ok: true,
                  status: 200,
                  response: proposeStatus(),
                  responseJson: proposeStatus(),
                }
              : step.action === "notion.live.read"
                ? await (async () => {
                    const notionPath =
                      typeof (step as any).notion_path === "string" &&
                      String((step as any).notion_path).trim()
                        ? String((step as any).notion_path)
                        : new URL(step.url).pathname;

                    const r = await notionLiveGet(notionPath);
                    return {
                      ok: r.http_status >= 200 && r.http_status < 300,
                      status: r.http_status,
                      response: r.redacted,
                      responseJson: r.redacted,
                    };
                  })()
                : step.action === "notion.live.write"
                  ? await (async () => {
                      const notionPath =
                        typeof (step as any).notion_path === "string" &&
                        String((step as any).notion_path).trim()
                          ? String((step as any).notion_path)
                          : new URL(step.url).pathname;

                      const props = (step as any).properties;

                      const stepIdempotencyKey =
                        typeof (step as any).idempotency_key === "string" && String((step as any).idempotency_key).trim()
                          ? String((step as any).idempotency_key).trim()
                          : deriveIdempotencyKey({
                              action: String(step.action),
                              plan_hash,
                              step_id: String(step.step_id),
                              threadId: String(plan.threadId),
                            });
                      (step as any).idempotency_key = stepIdempotencyKey;

                      const existing = getIdempotencyRecord(stepIdempotencyKey);
                      if (existing && typeof existing?.http_status === "number") {
                        return {
                          ok: true,
                          status: existing.http_status,
                          response: existing.response ?? null,
                          responseJson: existing.response ?? null,
                        };
                      }

                      const r = await notionLivePatchWithIdempotency(
                        notionPath,
                        { properties: props },
                        stepIdempotencyKey
                      );

                      if (r.http_status >= 400) {
                        throw new Error(`Notion PATCH failed HTTP ${r.http_status}`);
                      }

                      const approved_at =
                        typeof (step as any).approved_at === "string" &&
                        String((step as any).approved_at).trim()
                          ? String((step as any).approved_at)
                          : new Date().toISOString();

                      writeNotionLiveWriteArtifact({
                        execution_id: plan.execution_id,
                        step_id: step.step_id,
                        notion_path: notionPath,
                        request_properties: props,
                        guards: (step as any).guards || [],
                        http_status: r.http_status,
                        response: r.redacted,
                        approved_at,
                      });

                      writeIdempotencyRecord(stepIdempotencyKey, {
                        status: "executed",
                        idempotency_key: stepIdempotencyKey,
                        execution_id: plan.execution_id,
                        plan_hash,
                        threadId: plan.threadId,
                        step_id: step.step_id,
                        action: step.action,
                        notion_path: notionPath,
                        http_status: r.http_status,
                        response: r.redacted,
                        executed_at: new Date().toISOString(),
                      });

                      return {
                        ok: true,
                        status: r.http_status,
                        response: r.redacted,
                        responseJson: r.redacted,
                      };
                    })()
                : step.action === "docs.capture"
                  ? await executeDocsCaptureStep(step, timeoutMs, plan.execution_id)
                  : step.action === "browser.operator" || step.action.startsWith("browser.operator.") || step.adapter === "BrowserOperatorAdapter"
                    ? await executeBrowserOperator(step, plan.execution_id)
                    : step.action === "browser.l0.navigate" ||
                        step.action === "browser.l0.screenshot" ||
                        step.action === "browser.l0.dom_extract"
                      ? await executeBrowserL0Step(step, timeoutMs, plan.execution_id)
                      : await executeStep(step, timeoutMs);
          stepLog.http_status = out.status;
          stepLog.response = normalizeEvidenceOnReceiptResponse(out.response);

          if ((out as any).screenshots && Array.isArray((out as any).screenshots) && (out as any).screenshots.length) {
            stepLog.watch = {
              enabled: true,
              screenshots: (out as any).screenshots,
            };
          }

          const statusOk = step.expects.http_status.includes(out.status);
          stepLog.expectations.http_status_ok = statusOk;

          let jsonPathsOk = true;
          if (step.expects.json_paths_present && step.expects.json_paths_present.length) {
            const root = out.responseJson ?? (isPlainObject(out.response) ? out.response : null);
            for (const p of step.expects.json_paths_present) {
              if (getByPath(root, p) === undefined) {
                jsonPathsOk = false;
                break;
              }
            }
            stepLog.expectations.json_paths_ok = jsonPathsOk;
          }

          let ok = out.ok && statusOk && (step.expects.json_paths_present ? jsonPathsOk : true);

          const guardEval = maybeEvaluateStepGuards(step, stepLog.response);
          if (guardEval) {
            stepLog.guard = guardEval;
            if (guardEval.run_status !== "COMPLETED") {
              ok = false;
              const why = `Guard blocked (${guardEval.run_status})`;
              const detail = guardEval.errors.length ? `: ${guardEval.errors.join(";")}` : "";
              stepLog.error = stepLog.error ? `${stepLog.error}. ${why}${detail}` : `${why}${detail}`;
            }
          }

          stepLog.status = ok ? "success" : "failed";

          if (!ok) {
            const why = !out.ok
              ? `HTTP not ok (${out.status})`
              : !statusOk
                ? `Unexpected status (${out.status}); expected one of ${step.expects.http_status.join(",")}`
                : "Missing required json path";

            let hint: string | null = null;
            if (
              step.action === "notion.live.read" &&
              out.status === 404 &&
              isPlainObject(out.responseJson) &&
              (out.responseJson as any).code === "object_not_found"
            ) {
              try {
                const me = await notionLiveWhoAmI();
                if (me.ok && isPlainObject(me.me)) {
                  const name = typeof (me.me as any).name === "string" ? (me.me as any).name : null;
                  const id = typeof (me.me as any).id === "string" ? (me.me as any).id : null;
                  const workspaceName =
                    isPlainObject((me.me as any).bot) && typeof ((me.me as any).bot as any).workspace_name === "string"
                      ? (((me.me as any).bot as any).workspace_name as string)
                      : null;
                  hint = `Token integration: ${name ?? id ?? "(unknown)"}${workspaceName ? ` (workspace: ${workspaceName})` : ""}. Ensure this integration is shared on the database AND its parent page.`;
                }
              } catch {
                // Best-effort diagnostics only.
              }
            }

            stepLog.error = hint ? `${why}. ${hint}` : why;
          }
        }
      } catch (e: any) {
        stepLog.status = "failed";
        stepLog.error = e?.name === "AbortError" ? `Timeout after ${timeoutMs}ms` : (e?.message ?? String(e));
        stepLog.response = null;
      } finally {
        stepLog.duration_ms = Date.now() - start;
        stepLog.finished_at = nowIso();

        if (!plan.dry_run && stepLog.status === "success" && typeof opts.onStepFinished === "function") {
          try {
            await opts.onStepFinished({ plan, step, stepLog });
          } catch {
            // best-effort only
          }
        }
        runLog.steps.push(stepLog);
      }

      if (stepLog.status === "failed") {
        runLog.status = "failed";
        runLog.failed_step = step.step_id;
        runLog.finished_at = nowIso();
        runLog.receipt_hash = computeReceiptHash(runLog);
        return runLog;
      }
    }

    runLog.status = "success";
    runLog.finished_at = nowIso();
    runLog.receipt_hash = computeReceiptHash(runLog);
    return runLog;
  } catch (e: any) {
    runLog.status = "failed";
    runLog.error = e?.message ?? String(e);
    runLog.finished_at = new Date().toISOString();
    runLog.receipt_hash = computeReceiptHash(runLog);
    return runLog;
  }
}
