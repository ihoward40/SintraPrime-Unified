import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { notionConfig, notionPath, redactNotion, type NotionConfig } from "./notionLiveRead.js";
import { checkPolicyWithMeta, type PolicyResultWithMeta } from "../policy/checkPolicy.js";
import { ExecutionPlanSchema } from "../schemas/ExecutionPlan.schema.js";
import { computePlanHash } from "../utils/planHash.js";
import { evaluateGuards } from "../guards/evaluateGuards.js";

const hash = (v: string) => crypto.createHash("sha256").update(v).digest("hex");
function canonical(v: unknown): unknown {
  if (v === null || typeof v === "string" || typeof v === "boolean") return v;
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (Array.isArray(v)) return v.map(canonical);
  if (v && typeof v === "object" && (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null)) {
    return Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical((v as Record<string, unknown>)[k])]));
  }
  throw new Error("Invalid Notion JSON body");
}
function bodyText(body: unknown) {
  if (!body || typeof body !== "object" || Array.isArray(body) || Object.keys(body).length !== 1 || !("properties" in body)) throw new Error("Invalid Notion properties body");
  const props = (body as any).properties;
  if (!props || typeof props !== "object" || Array.isArray(props)) throw new Error("Invalid Notion properties body");
  return JSON.stringify(canonical(body));
}
function binding(execution_id: string, step_id: string, dest: string, body: unknown, key: string, config: NotionConfig) {
  if (!execution_id || !step_id) throw new Error("Notion execution identity required");
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(key)) throw new Error("Invalid idempotency key");
  const safePath = notionPath(dest, true);
  const serialized = bodyText(body);
  const digest = hash(JSON.stringify([execution_id, step_id, config.base + safePath, serialized, key, config.version, hash(config.token)]));
  return { digest, serialized, path: safePath, key };
}

// The CLI owns authority: call only after its saved approval, role, skill and policy checks.
// WeakMap identity makes JSON plan fields and copied/forged objects non-authoritative.
declare const approvalBrand: unique symbol;
export type NotionWriteApproval = { readonly [approvalBrand]: true };
type Grant = { execution_id: string; requests: Map<string, string> };
const approvals = new WeakMap<NotionWriteApproval, Grant>();

export function notionWriteRequest(execution_id: string, step: any) {
  if (step?.action !== "notion.live.write" || step.adapter !== "NotionAdapter" || step.method !== "PATCH" || step.read_only !== false || step.approval_scoped !== true) throw new Error("Invalid approved Notion write step");
  const dest = notionPath(step.notion_path ?? new URL(step.url).pathname, true);
  if (step.url !== "https://api.notion.com" + dest) throw new Error("Notion destination mismatch");
  if (step.notion_path_prestate !== undefined && step.notion_path_prestate !== dest) throw new Error("Notion prestate destination mismatch");
  if (!step.prestate || typeof step.prestate !== "object" || Array.isArray(step.prestate) || hash(JSON.stringify(canonical(step.prestate))) !== step.prestate_fingerprint) throw new Error("Notion prestate fingerprint mismatch");
  if (!evaluateGuards(step.prestate, step.guards ?? []).ok) throw new Error("Notion prestate guard failed");
  return binding(execution_id, step.step_id, dest, { properties: step.properties }, step.idempotency_key, notionConfig());
}

export function authorizeApprovedNotionWrites(rawPlan: unknown, policy: PolicyResultWithMeta, approved_execution_id: string): NotionWriteApproval {
  const plan = ExecutionPlanSchema.parse(rawPlan);
  if (!policy.allowed || approved_execution_id !== plan.execution_id || !approved_execution_id) throw new Error("Notion write approval required");
  const rechecked = checkPolicyWithMeta(plan, process.env, new Date(), { execution_id: plan.execution_id, approved_execution_id });
  if (!rechecked.allowed) throw new Error("Notion write policy denied");
  const requests = new Map<string, string>();
  const planHash = (rawPlan as any).plan_hash || computePlanHash(plan);
  for (const step of plan.steps) {
    if (step.action !== "notion.live.write") continue;
    const key = step.idempotency_key?.trim() || hash(`${step.action}|${planHash}|${step.step_id}|${plan.threadId}`);
    const request = notionWriteRequest(plan.execution_id, { ...step, idempotency_key: key });
    if (requests.has(step.step_id)) throw new Error("Duplicate Notion step identity");
    requests.set(step.step_id, request.digest);
  }
  const capability = Object.freeze({}) as NotionWriteApproval;
  approvals.set(capability, { execution_id: plan.execution_id, requests });
  return capability;
}

function recordFile(key: string) { return path.join("runs", "notion-idempotency", hash(key) + ".json"); }
function rejectUnboundLegacyRecord(key: string) {
  if (fs.existsSync(path.join("runs", "idempotency", key + ".json"))) throw new Error("Legacy Notion write outcome requires reconciliation");
}
function successfulRecord(file: string, digest: string) {
  let record: any;
  try { record = JSON.parse(fs.readFileSync(file, "utf8")); }
  catch { throw new Error("Notion write outcome requires reconciliation"); }
  if (record.digest !== digest) throw new Error("Idempotency key request mismatch");
  if (record.status !== "success" || !Number.isInteger(record.http_status) || record.http_status < 200 || record.http_status >= 300 || !("redacted" in record)) throw new Error("Notion write outcome requires reconciliation");
  return { http_status: record.http_status as number, redacted: redactNotion(record.redacted) };
}
// Read-only replay verification for CLI shortcuts; never trusts the legacy generic ledger.
export function getSuccessfulNotionReplay(execution_id: string, step: unknown) {
  const request = notionWriteRequest(execution_id, step);
  const file = recordFile(request.key);
  if (!fs.existsSync(file)) {
    rejectUnboundLegacyRecord(request.key);
    return null;
  }
  return successfulRecord(file, request.digest);
}

export async function notionLivePatchWithIdempotency(dest: string, body: unknown, key: string, approval?: NotionWriteApproval, execution_id = "", step_id = "") {
  const grant = approval && approvals.get(approval);
  if (!grant || grant.execution_id !== execution_id) throw new Error("Notion write approval required");
  const config = notionConfig();
  const request = binding(execution_id, step_id, dest, body, key, config);
  if (grant.requests.get(step_id) !== request.digest) throw new Error("Notion write approval request mismatch");
  const file = recordFile(key);
  if (!fs.existsSync(file)) rejectUnboundLegacyRecord(key);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  try {
    const fd = fs.openSync(file, "wx");
    try { fs.writeFileSync(fd, JSON.stringify({ digest: request.digest, status: "pending" })); }
    finally { fs.closeSync(fd); }
  } catch (error: any) {
    if (error?.code !== "EEXIST") throw new Error("Notion reservation failed");
    return successfulRecord(file, request.digest);
  }
  // Reservation precedes dispatch. Failure or process interruption remains pending and
  // requires explicit reconciliation. Notion provides no remote idempotency guarantee.
  let result: { http_status: number; redacted: ReturnType<typeof redactNotion> };
  try {
    const res = await fetch(config.base + request.path, {
      method: "PATCH", redirect: "error", signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${config.token}`, "Notion-Version": config.version, "Content-Type": "application/json" },
      body: request.serialized,
    });
    const text = await res.text();
    let value: unknown;
    try { value = JSON.parse(text); } catch { value = null; }
    result = { http_status: res.status, redacted: redactNotion(value, config.token) };
  } catch { throw new Error("Notion write outcome requires reconciliation"); }
  if (result.http_status >= 200 && result.http_status < 300) {
    const temporary = file + "." + crypto.randomUUID() + ".tmp";
    try {
      fs.writeFileSync(temporary, JSON.stringify({ digest: request.digest, status: "success", ...result }), { flag: "wx" });
      fs.renameSync(temporary, file);
    } catch { throw new Error("Notion write outcome requires reconciliation"); }
  }
  return result;
}
