import fs from "node:fs";
import path from "node:path";

function todayKeyUTC(now = new Date()): string {
  return now.toISOString().slice(0, 10);
}

function parseOptionalNumberEnv(name: string): number | null {
  const raw = process.env[name];
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export type LlmBudgetConfig = {
  enabled: boolean;
  stateDir: string;
  maxCallsPerDay: number | null;
  maxCreditsPerDay: number | null;
  creditsPerCallEstimate: number;
  writeReceipts: boolean;
};

export type LlmBudgetState = {
  date_utc: string;
  calls: number;
  credits_used_estimated: number;
  credits_used_actual: number;
  updated_at: string;
};

export type LlmBudgetDecision =
  | {
      allowed: true;
      date_utc: string;
      state_before: LlmBudgetState;
      state_after_reservation: LlmBudgetState;
      config: Omit<LlmBudgetConfig, "enabled" | "stateDir">;
    }
  | {
      allowed: false;
      date_utc: string;
      code: "LLM_MAX_CALLS_PER_DAY_EXCEEDED" | "LLM_MAX_CREDITS_PER_DAY_EXCEEDED";
      reason: string;
      state: LlmBudgetState;
      config: Omit<LlmBudgetConfig, "enabled" | "stateDir">;
    };

export function readLlmBudgetConfig(env: NodeJS.ProcessEnv = process.env): LlmBudgetConfig {
  const enabled = String(env.LLM_BUDGET_ENABLED ?? "").trim() === "1";
  const stateDir = String(env.LLM_BUDGET_STATE_DIR ?? "runs/llm-budget/state").trim() || "runs/llm-budget/state";

  const maxCallsPerDay = (() => {
    const raw = String(env.LLM_MAX_CALLS_PER_DAY ?? "").trim();
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? Math.max(0, n) : null;
  })();

  const maxCreditsPerDay = (() => {
    const raw = String(env.LLM_MAX_CREDITS_PER_DAY ?? "").trim();
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? Math.max(0, n) : null;
  })();

  const creditsPerCallEstimate = Math.max(0, parseOptionalNumberEnv("LLM_CREDITS_PER_CALL_ESTIMATE") ?? 0);
  const writeReceipts = String(env.LLM_BUDGET_RECEIPTS ?? "").trim() === "1";

  return {
    enabled,
    stateDir,
    maxCallsPerDay,
    maxCreditsPerDay,
    creditsPerCallEstimate,
    writeReceipts,
  };
}

function statePath(stateDir: string, dateUtc: string) {
  return path.join(process.cwd(), stateDir, `llm-${dateUtc}.json`);
}

export function readLlmBudgetState(opts: { stateDir: string; now?: Date }): LlmBudgetState {
  const date_utc = todayKeyUTC(opts.now);
  const file = statePath(opts.stateDir, date_utc);

  const initial: LlmBudgetState = {
    date_utc,
    calls: 0,
    credits_used_estimated: 0,
    credits_used_actual: 0,
    updated_at: new Date().toISOString(),
  };

  if (!fs.existsSync(file)) return initial;

  try {
    const raw = JSON.parse(fs.readFileSync(file, "utf8"));
    if (!raw || typeof raw !== "object") return initial;

    const calls = Number((raw as any).calls);
    const est = Number((raw as any).credits_used_estimated);
    const act = Number((raw as any).credits_used_actual);

    return {
      date_utc,
      calls: Number.isFinite(calls) ? Math.max(0, calls) : 0,
      credits_used_estimated: Number.isFinite(est) ? Math.max(0, est) : 0,
      credits_used_actual: Number.isFinite(act) ? Math.max(0, act) : 0,
      updated_at: typeof (raw as any).updated_at === "string" ? (raw as any).updated_at : initial.updated_at,
    };
  } catch {
    return initial;
  }
}

function writeLlmBudgetState(opts: { stateDir: string; state: LlmBudgetState }) {
  const file = statePath(opts.stateDir, opts.state.date_utc);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(opts.state, null, 2), { encoding: "utf8" });
}

export function reserveLlmBudgetCall(opts: {
  config: LlmBudgetConfig;
  now?: Date;
}): LlmBudgetDecision {
  const cfg = opts.config;
  const date_utc = todayKeyUTC(opts.now);

  const state_before = readLlmBudgetState({ stateDir: cfg.stateDir, now: opts.now });
  const state = { ...state_before };

  const nextCalls = state.calls + 1;
  if (typeof cfg.maxCallsPerDay === "number" && nextCalls > cfg.maxCallsPerDay) {
    return {
      allowed: false,
      date_utc,
      code: "LLM_MAX_CALLS_PER_DAY_EXCEEDED",
      reason: `Max LLM calls/day reached (${state.calls}/${cfg.maxCallsPerDay})`,
      state,
      config: {
        maxCallsPerDay: cfg.maxCallsPerDay,
        maxCreditsPerDay: cfg.maxCreditsPerDay,
        creditsPerCallEstimate: cfg.creditsPerCallEstimate,
        writeReceipts: cfg.writeReceipts,
      },
    };
  }

  const nextEstimated = state.credits_used_estimated + cfg.creditsPerCallEstimate;
  if (typeof cfg.maxCreditsPerDay === "number" && nextEstimated > cfg.maxCreditsPerDay) {
    return {
      allowed: false,
      date_utc,
      code: "LLM_MAX_CREDITS_PER_DAY_EXCEEDED",
      reason: `Max LLM credits/day reached (estimated ${state.credits_used_estimated}/${cfg.maxCreditsPerDay})`,
      state,
      config: {
        maxCallsPerDay: cfg.maxCallsPerDay,
        maxCreditsPerDay: cfg.maxCreditsPerDay,
        creditsPerCallEstimate: cfg.creditsPerCallEstimate,
        writeReceipts: cfg.writeReceipts,
      },
    };
  }

  state.calls = nextCalls;
  state.credits_used_estimated = nextEstimated;
  state.updated_at = new Date().toISOString();

  writeLlmBudgetState({ stateDir: cfg.stateDir, state });

  return {
    allowed: true,
    date_utc,
    state_before,
    state_after_reservation: state,
    config: {
      maxCallsPerDay: cfg.maxCallsPerDay,
      maxCreditsPerDay: cfg.maxCreditsPerDay,
      creditsPerCallEstimate: cfg.creditsPerCallEstimate,
      writeReceipts: cfg.writeReceipts,
    },
  };
}

export function finalizeLlmBudgetCall(opts: {
  config: LlmBudgetConfig;
  date_utc: string;
  estimated_credits_charged: number;
  actual_credits: number | null;
  now?: Date;
}) {
  const cfg = opts.config;
  if (!cfg.enabled) return;

  if (opts.actual_credits === null) return;

  const state_before = readLlmBudgetState({ stateDir: cfg.stateDir, now: opts.now });
  if (state_before.date_utc !== opts.date_utc) {
    // If the day rolled over between reserve and finalize, skip adjustment.
    return;
  }

  const delta = opts.actual_credits - Math.max(0, opts.estimated_credits_charged);
  if (!Number.isFinite(delta) || delta === 0) return;

  const state = { ...state_before };
  state.credits_used_actual = Math.max(0, state.credits_used_actual + opts.actual_credits);
  state.updated_at = new Date().toISOString();

  // If the estimate was 0, keep estimated in sync with actual.
  if (opts.estimated_credits_charged === 0) {
    state.credits_used_estimated = Math.max(0, state.credits_used_estimated + opts.actual_credits);
  } else {
    state.credits_used_estimated = Math.max(0, state.credits_used_estimated + delta);
  }

  writeLlmBudgetState({ stateDir: cfg.stateDir, state });
}
