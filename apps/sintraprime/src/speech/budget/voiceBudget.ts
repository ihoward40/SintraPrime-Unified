import { scaleBudgetByConfidence } from "./confidenceBudget.js";

export type VoiceBudgetDecision =
  | { allowed: true; reason?: string; effective_budget?: number }
  | { allowed: false; reason: "VOICE_BUDGET_EXHAUSTED"; effective_budget?: number };

type BudgetState = { base_budget: number; used: number };

const budgetByFingerprint = new Map<string, BudgetState>();

function parseBaseBudgetFromEnv(env: NodeJS.ProcessEnv = process.env): number | null {
  const raw = String(env.SPEECH_VOICE_BUDGET ?? "").trim();
  if (!raw) return null;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

export function canSpeakNow(opts: {
  fingerprint: string;
  severity?: "calm" | "warning" | "urgent";
  confidence?: number;
  env?: NodeJS.ProcessEnv;
}): VoiceBudgetDecision {
  const baseBudget = parseBaseBudgetFromEnv(opts.env);
  if (baseBudget === null) return { allowed: true };

  if (opts.severity === "urgent") {
    return { allowed: true, reason: "URGENT_BYPASS", effective_budget: baseBudget };
  }

  const state = (() => {
    const existing = budgetByFingerprint.get(opts.fingerprint);
    if (existing) return existing;
    const s: BudgetState = { base_budget: baseBudget, used: 0 };
    budgetByFingerprint.set(opts.fingerprint, s);
    return s;
  })();

  // If base budget changes between calls, clamp deterministically.
  state.base_budget = baseBudget;

  const effectiveBudget = scaleBudgetByConfidence(state.base_budget, opts.confidence);

  if (state.used >= effectiveBudget) {
    return { allowed: false, reason: "VOICE_BUDGET_EXHAUSTED", effective_budget: effectiveBudget };
  }

  state.used += 1;
  return { allowed: true, effective_budget: effectiveBudget };
}
