import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export type GovernorDecision =
  | { allowed: true; fingerprint: string }
  | {
      allowed: false;
      fingerprint: string;
      kind: "Throttled";
      code: "TOKEN_BUCKET_EMPTY" | "CIRCUIT_BREAKER_OPEN";
      reason: string;
      retry_at: string | null;
    };

type CounterState = {
  fingerprint: string;
  tokens: number;
  updated_at_ms: number;
};

type CircuitBreakerState = {
  fingerprint: string;
  open_until_ms: number;
  opened_at_ms: number;
  reason?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function parseNumberEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJsonFile<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function writeJsonFile(filePath: string, data: unknown) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), { encoding: "utf8" });
}

export function isGovernorEnabled(): boolean {
  return process.env.RUN_GOVERNOR_ENABLED === "1";
}

export function computeGovernorFingerprint(input: { command: string; domain_id?: string | null }): string {
  const domain = typeof input.domain_id === "string" ? input.domain_id : "";
  const payload = `${domain}|${String(input.command ?? "")}`;
  return crypto.createHash("sha256").update(payload, "utf8").digest("hex");
}

function countersPath(fingerprint: string) {
  return path.join(process.cwd(), "runs", "governor", "counters", `${fingerprint}.json`);
}

function circuitBreakerPath(fingerprint: string) {
  return path.join(
    process.cwd(),
    "runs",
    "governor",
    "circuit-breakers",
    `${fingerprint}.json`
  );
}

export function checkGovernor(input: { fingerprint: string; now_ms: number }): GovernorDecision {
  const capacity = Math.max(0, parseNumberEnv("GOVERNOR_BUCKET_CAPACITY", 10));
  const refillPerMinute = Math.max(0, parseNumberEnv("GOVERNOR_REFILL_TOKENS_PER_MINUTE", 1));
  const costPerRun = Math.max(0, parseNumberEnv("GOVERNOR_COST_PER_RUN", 1));

  // Circuit breaker short-circuit.
  {
    const breakerRaw = readJsonFile<unknown>(circuitBreakerPath(input.fingerprint));
    if (isRecord(breakerRaw)) {
      const openUntilMs = Number((breakerRaw as any).open_until_ms);
      if (Number.isFinite(openUntilMs) && openUntilMs > input.now_ms) {
        return {
          allowed: false,
          fingerprint: input.fingerprint,
          kind: "Throttled",
          code: "CIRCUIT_BREAKER_OPEN",
          reason: "circuit breaker is open",
          retry_at: new Date(openUntilMs).toISOString(),
        };
      }
    }
  }

  // Token bucket.
  const refillPerMs = refillPerMinute / 60_000;
  const counterFile = countersPath(input.fingerprint);
  const existing = readJsonFile<unknown>(counterFile);

  let state: CounterState;
  if (isRecord(existing)) {
    const tokens = Number((existing as any).tokens);
    const updatedAtMs = Number((existing as any).updated_at_ms);
    state = {
      fingerprint: input.fingerprint,
      tokens: Number.isFinite(tokens) ? tokens : capacity,
      updated_at_ms: Number.isFinite(updatedAtMs) ? updatedAtMs : input.now_ms,
    };
  } else {
    state = {
      fingerprint: input.fingerprint,
      tokens: capacity,
      updated_at_ms: input.now_ms,
    };
  }

  if (state.updated_at_ms < input.now_ms && refillPerMs > 0) {
    const delta = input.now_ms - state.updated_at_ms;
    const refilled = state.tokens + delta * refillPerMs;
    state.tokens = Math.min(capacity, refilled);
    state.updated_at_ms = input.now_ms;
  } else if (state.updated_at_ms > input.now_ms) {
    // Guard against clock going backwards.
    state.updated_at_ms = input.now_ms;
  }

  if (costPerRun === 0) {
    writeJsonFile(counterFile, state);
    return { allowed: true, fingerprint: input.fingerprint };
  }

  if (state.tokens >= costPerRun) {
    state.tokens = state.tokens - costPerRun;
    state.updated_at_ms = input.now_ms;
    writeJsonFile(counterFile, state);
    return { allowed: true, fingerprint: input.fingerprint };
  }

  // Not enough tokens.
  let retryAt: string | null = null;
  if (refillPerMs > 0) {
    const needed = costPerRun - state.tokens;
    const ms = Math.ceil(needed / refillPerMs);
    retryAt = new Date(input.now_ms + ms).toISOString();
  }

  writeJsonFile(counterFile, state);
  return {
    allowed: false,
    fingerprint: input.fingerprint,
    kind: "Throttled",
    code: "TOKEN_BUCKET_EMPTY",
    reason: "token bucket exhausted",
    retry_at: retryAt,
  };
}

export function writeCircuitBreakerOpen(input: {
  fingerprint: string;
  now_ms: number;
  open_for_ms: number;
  reason?: string;
}) {
  const state: CircuitBreakerState = {
    fingerprint: input.fingerprint,
    open_until_ms: input.now_ms + Math.max(0, input.open_for_ms),
    opened_at_ms: input.now_ms,
    reason: input.reason,
  };
  writeJsonFile(circuitBreakerPath(input.fingerprint), state);
}
