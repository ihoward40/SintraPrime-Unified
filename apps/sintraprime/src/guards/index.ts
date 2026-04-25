import crypto from "node:crypto";
import { z } from "zod";
import { capIssuesDeterministic, type GuardIssue } from "./capIssuesDeterministic.js";

export { capIssuesDeterministic } from "./capIssuesDeterministic.js";

/** ---------- hashing ---------- */
export function sha256(s: string) {
  return crypto.createHash("sha256").update(s, "utf8").digest("hex");
}

export function pinnedInputSha256(inputText: string) {
  return sha256(inputText);
}

/** Stable stringify: deterministic key ordering (good enough when you control object creation) */
export function stableStringify(obj: any): string {
  const allKeys: string[] = [];
  JSON.stringify(obj, (k, v) => (allKeys.push(k), v));
  allKeys.sort();
  return JSON.stringify(obj, allKeys);
}

export function pinnedEchoFirst40(inputText: string) {
  return inputText.slice(0, 40);
}

/** ---------- placeholder guard ---------- */
const UNRESOLVED = /\{[a-zA-Z0-9_]+\}/g;

export function findUnresolvedPlaceholders(renderedPrompt: string) {
  const hits = renderedPrompt.match(UNRESOLVED) ?? [];
  return [...new Set(hits)];
}

export function assertNoUnresolvedPlaceholders(renderedPrompt: string) {
  const uniq = findUnresolvedPlaceholders(renderedPrompt);
  if (uniq.length) throw new Error(`UNRESOLVED_PLACEHOLDERS: ${uniq.join(", ")}`);
}

/** ---------- “asking for input” tripwire ---------- */
const ASKING_FOR_INPUT =
  /\b(please provide|can you provide|could you provide|would you provide|paste (the )?(input|excerpt)|share (the )?input|i need (the )?input|send (me )?the input)\b/i;

export function looksLikeAskingForInput(raw: string) {
  return ASKING_FOR_INPUT.test(raw);
}

/** ---------- pin echo guard ---------- */
export function verifyPinEcho(stepOut: any, inputText: string, inputSha: string) {
  const echo = pinnedEchoFirst40(inputText);
  return stepOut?.pinned_input_sha256 === inputSha && stepOut?.pinned_input_echo_first_40 === echo;
}

/** ---------- grounding guards ---------- */
export function verifyQuotesInInput(quotes: { id: string; text: string }[], input: string) {
  const missing = quotes.filter((q) => !input.includes(q.text));
  return { ok: missing.length === 0, missing };
}

export function verifyClaimQuoteIds(quoteIds: Set<string>, claims: { quote_ids: string[] }[]) {
  const bad = claims.filter((c) => c.quote_ids.some((id) => !quoteIds.has(id)));
  return { ok: bad.length === 0, bad };
}

/** ---------- anchor extraction ---------- */
export function extractAnchors(input: string) {
  const amount = input.match(/\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?/g)?.[0];
  const phone = input.match(/\(\d{3}\)\s*\d{3}-\d{4}/)?.[0];
  const time = input.match(/\b\d{1,2}:\d{2}\s*(AM|PM)\b/i)?.[0];
  const ref = input.match(/Reference ID:\s*([A-Z0-9-]+)/i)?.[1];
  return { amount, phone, time, reference_id: ref };
}

/** ---------- Zod schemas used by guards ---------- */
export const Quote = z.object({
  id: z.string().regex(/^Q\d+$/),
  text: z.string().min(1),
});

export const GroundedClaim = z.object({
  claim: z.string().min(1),
  quote_ids: z.array(z.string().regex(/^Q\d+$/)).min(1),
});

export const GroundedOutputBase = z.object({
  quotes: z.array(Quote).min(3),
  claims: z.array(GroundedClaim).min(1),
});

// Minimal wrapper around GroundedOutputBase that includes pin-echo fields.
// This is the most common on-the-wire step output shape for GROUNDED_OUTPUT.
export const GroundedStepOut = GroundedOutputBase.extend({
  pinned_input_sha256: z.string(),
  pinned_input_echo_first_40: z.string(),
}).strict();

/** StepReceipt fields we want enforced by the runner */
export const StepReceipt = z.object({
  step_id: z.string(),
  started_at: z.string(),
  completed_at: z.string(),
  input_sha256: z.string(),
  prompt_sha256: z.string(),
  output_sha256: z.string(),

  template_ok: z.boolean(),
  unresolved_placeholders: z.array(z.string()).default([]),
  pin_echo_ok: z.boolean(),

  schema_ok: z.boolean(),
  grounding_ok: z.boolean(),

  drift_detected: z.boolean(),
  retries: z.number().int().min(0),
  errors: z.array(z.string()).default([]),
});

export const RunReceipt = z.object({
  run_id: z.string(),
  task_type: z.string(),
  started_at: z.string(),
  completed_at: z.string(),
  input_sha256: z.string(),
  final_output_sha256: z.string(),
  strict_mode: z.boolean(),
  run_status: z.enum(["COMPLETED", "BLOCKED_DRIFT", "BLOCKED_SCHEMA", "BLOCKED_GROUNDING"]),
  steps: z.array(StepReceipt),
});

/** ---------- core evaluation ---------- */
export type GuardMode = "CODE_IS_SOURCE" | "GROUNDED_OUTPUT";

export type GuardEvalInput = {
  mode: GuardMode;
  strict: boolean;

  /** prompt + input pinning */
  renderedPrompt: string;
  pinnedInputText: string;
  pinnedInputSha: string;

  /** model output */
  stepOut: any;

  /** optional for CODE_IS_SOURCE */
  pinnedCode?: string;

  /** optional for GROUNDED_OUTPUT */
  inputTextForGrounding?: string;
};

export function evaluateGuards(x: GuardEvalInput) {
  const errors: string[] = [];

  // template / unresolved placeholders
  const unresolved = findUnresolvedPlaceholders(x.renderedPrompt);
  const template_ok = unresolved.length === 0;

  if (!template_ok) errors.push(`UNRESOLVED_PLACEHOLDERS:${unresolved.join(",")}`);

  // “asking for input” is drift in strict mode (and usually always drift)
  const asksForInput = looksLikeAskingForInput(String(x.stepOut ?? ""));
  if (asksForInput) errors.push("ASKING_FOR_INPUT_DETECTED");

  // pin echo
  const pin_echo_ok = verifyPinEcho(x.stepOut, x.pinnedInputText, x.pinnedInputSha);
  if (!pin_echo_ok) errors.push("PIN_ECHO_MISMATCH");

  // schema + grounding
  let schema_ok = true;
  let grounding_ok = true;

  if (x.mode === "GROUNDED_OUTPUT") {
    const parsed = GroundedStepOut.safeParse(x.stepOut);
    if (!parsed.success) {
      schema_ok = false;
      errors.push("SCHEMA_FAIL:GROUNDED_STEP_OUT");
      const allIssues: GuardIssue[] = parsed.error.issues.map((iss) => {
        const p = iss.path.length ? iss.path.join(".") : "(root)";
        return {
          severity: "ERROR",
          ruleId: "ZOD_SCHEMA",
          message: `${p}: ${iss.message}`,
        };
      });

      const capped = capIssuesDeterministic(allIssues, 12);
      for (const i of capped) errors.push(`SCHEMA_ISSUE:${i.message ?? ""}`);
    } else {
      schema_ok = true;
      const quotes = parsed.data.quotes;
      const claims = parsed.data.claims;

      const inputForGrounding = x.inputTextForGrounding ?? x.pinnedInputText;

      const qcheck = verifyQuotesInInput(quotes, inputForGrounding);
      if (!qcheck.ok) {
        grounding_ok = false;
        errors.push(`GROUNDING_MISSING_QUOTES:${qcheck.missing.map((m) => m.id).join(",")}`);
      }

      const quoteIdSet = new Set(quotes.map((q) => q.id));
      const ccheck = verifyClaimQuoteIds(quoteIdSet, claims);
      if (!ccheck.ok) {
        grounding_ok = false;
        errors.push("GROUNDING_BAD_CLAIM_QUOTE_IDS");
      }
    }
  }

  // CODE_IS_SOURCE: output must match pinned code EXACTLY
  if (x.mode === "CODE_IS_SOURCE") {
    const expected = x.pinnedCode ?? "";
    const actual = typeof x.stepOut === "string" ? x.stepOut : stableStringify(x.stepOut);
    if (actual !== expected) {
      schema_ok = false; // treat as schema/contract breach
      errors.push("CODE_IS_SOURCE_MISMATCH");
    }
  }

  // drift logic: fail-closed in strict mode
  const drift_detected =
    asksForInput ||
    !template_ok ||
    !pin_echo_ok ||
    !schema_ok ||
    !grounding_ok ||
    (x.mode === "CODE_IS_SOURCE" && errors.includes("CODE_IS_SOURCE_MISMATCH"));

  const blocked = x.strict && (asksForInput || !template_ok || !pin_echo_ok || !schema_ok || !grounding_ok);

  const run_status = blocked
    ? !schema_ok
      ? "BLOCKED_SCHEMA"
      : !grounding_ok
        ? "BLOCKED_GROUNDING"
        : "BLOCKED_DRIFT"
    : "COMPLETED";

  return {
    template_ok,
    unresolved_placeholders: unresolved,
    pin_echo_ok,
    schema_ok,
    grounding_ok,
    drift_detected,
    run_status,
    errors,
  };
}
