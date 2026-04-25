import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export type RunGovernorDecision = {
  decision: "ALLOW" | "DENY" | "DELAY";
  reason: "TOKEN_EXHAUSTED" | "CIRCUIT_OPEN" | "MAX_CONCURRENT" | null;
  retry_after: string | null;
  fingerprint: string;
  autonomy_mode_effective: string;
};

type CounterState = {
  fingerprint: string;
  hour_start: string;
  tokens_remaining: number;
  concurrent: number;
  updated_at: string;
};

type CircuitBreakerState = {
  fingerprint: string;
  open_until: string;
  opened_at: string;
  reason: string;
  counts: {
    policy_denials: number;
    rollbacks: number;
    confidence_regressions: number;
  };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
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
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", { encoding: "utf8" });
}

function parseIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

export function isRunGovernorEnabled(): boolean {
  return process.env.RUN_GOVERNOR_ENABLED === "1";
}

export function deriveFingerprint(input: { command: string; domain_id?: string | null }): string {
  const cmd = String(input.command ?? "").trim();

  // Minimal semantic fingerprints (stable across minor DSL formatting).
  if (/^\/autonomy\s+requalify\b/i.test(cmd)) {
    return "autonomy.requalify";
  }
  if (/^\/notion\s+set\b/i.test(cmd) || /^\/template\s+run\b/i.test(cmd)) {
    return "notion.write.page";
  }
  if (/^\/notion\s+live\b/i.test(cmd)) {
    // Tier-22.2: probation success counters need a read-safe command to accrue
    // successes against the write-domain fingerprint.
    return "notion.write.page";
  }
  if (/^\/intake\b/i.test(cmd)) {
    return "intake.scan";
  }

  // Domain + raw command fallback.
  const domain = typeof input.domain_id === "string" ? input.domain_id : "";
  const payload = `${domain}|${cmd}`;
  return crypto.createHash("sha256").update(payload, "utf8").digest("hex");
}

function countersPath(fingerprint: string) {
  return path.join(process.cwd(), "runs", "governor", "counters", `${safeFilePart(fingerprint)}.json`);
}

function circuitBreakerPath(fingerprint: string) {
  return path.join(
    process.cwd(),
    "runs",
    "governor",
    "circuit-breakers",
    `${safeFilePart(fingerprint)}.json`
  );
}

function hourStartIso(nowIso: string): string {
  const d = new Date(nowIso);
  d.setUTCMinutes(0, 0, 0);
  return d.toISOString();
}

function addHoursIso(nowIso: string, hours: number): string {
  const d = new Date(nowIso);
  d.setUTCHours(d.getUTCHours() + hours);
  return d.toISOString();
}

function isIsoAfter(a: string, b: string): boolean {
  const ta = new Date(a).getTime();
  const tb = new Date(b).getTime();
  return Number.isFinite(ta) && Number.isFinite(tb) ? ta > tb : false;
}

function scanRollbackArtifactsForFingerprint(fingerprint: string): number {
  const dir = path.join(process.cwd(), "runs", "rollback");
  if (!fs.existsSync(dir)) return 0;
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  let count = 0;
  for (const f of files) {
    const full = path.join(dir, f);
    const raw = readJsonFile<unknown>(full);
    if (!isRecord(raw)) continue;
    const fp = typeof (raw as any).fingerprint === "string" ? String((raw as any).fingerprint) : null;
    if (fp && fp === fingerprint) count += 1;
  }
  return count;
}

export function runGovernor(input: {
  command: string;
  domain_id?: string | null;
  autonomy_mode: string;
  now_iso: string;
  simulate?: boolean;
}): RunGovernorDecision {
  const fingerprint = deriveFingerprint({ command: input.command, domain_id: input.domain_id });

  return runGovernorForFingerprint({
    fingerprint,
    autonomy_mode: input.autonomy_mode,
    now_iso: input.now_iso,
    simulate: input.simulate === true,
  });
}

function runGovernorForFingerprint(input: {
  fingerprint: string;
  autonomy_mode: string;
  now_iso: string;
  simulate?: boolean;
}): RunGovernorDecision {
  const fingerprint = input.fingerprint;

  const tokensPerHour = fingerprint === "autonomy.requalify"
    ? Math.max(0, parseIntEnv("REQUALIFY_TOKENS_PER_HOUR", 2))
    : fingerprint === "autonomy.activate"
      ? Math.max(0, parseIntEnv("ACTIVATE_TOKENS_PER_HOUR", 1))
      : Math.max(0, parseIntEnv("AUTONOMY_TOKENS_PER_HOUR", 10));
  const maxConcurrent = fingerprint === "autonomy.requalify"
    ? Math.max(0, parseIntEnv("REQUALIFY_MAX_CONCURRENT", 1))
    : fingerprint === "autonomy.activate"
      ? Math.max(0, parseIntEnv("ACTIVATE_MAX_CONCURRENT", 1))
      : Math.max(0, parseIntEnv("AUTONOMY_MAX_CONCURRENT", 1));
  const cbRollbacks = Math.max(0, parseIntEnv("AUTONOMY_CB_ROLLBACKS", 3));
  const cbOpenHours = Math.max(0, parseIntEnv("AUTONOMY_CB_OPEN_HOURS", 24));

  // Probation enforcement is handled by Tier-22. The governor only reports the effective mode.
  const autonomy_mode_effective = String(input.autonomy_mode || "OFF");

  // Circuit breaker: open if already open.
  {
    const breaker = readJsonFile<unknown>(circuitBreakerPath(fingerprint));
    if (isRecord(breaker)) {
      const openUntil = typeof (breaker as any).open_until === "string" ? (breaker as any).open_until : null;
      if (openUntil && isIsoAfter(openUntil, input.now_iso)) {
        return {
          decision: "DENY",
          reason: "CIRCUIT_OPEN",
          retry_after: openUntil,
          fingerprint,
          autonomy_mode_effective,
        };
      }
    }
  }

  // Circuit breaker: trip on rollback artifacts (seeded in smoke).
  if (cbRollbacks > 0) {
    const rollbacks = scanRollbackArtifactsForFingerprint(fingerprint);
    if (rollbacks >= cbRollbacks) {
      const opened_at = input.now_iso;
      const open_until = addHoursIso(opened_at, cbOpenHours);
      const breakerState: CircuitBreakerState = {
        fingerprint,
        opened_at,
        open_until,
        reason: "ROLLBACK_THRESHOLD",
        counts: {
          policy_denials: 0,
          rollbacks,
          confidence_regressions: 0,
        },
      };
      if (!input.simulate) {
        writeJsonFile(circuitBreakerPath(fingerprint), breakerState);
      }
      return {
        decision: "DENY",
        reason: "CIRCUIT_OPEN",
        retry_after: open_until,
        fingerprint,
        autonomy_mode_effective,
      };
    }
  }

  // Token bucket counters (refill at hour boundary).
  const nowHour = hourStartIso(input.now_iso);
  const counterFile = countersPath(fingerprint);
  const existing = readJsonFile<unknown>(counterFile);

  let state: CounterState;
  if (isRecord(existing)) {
    const hour_start = typeof (existing as any).hour_start === "string" ? (existing as any).hour_start : nowHour;
    const tokens_remaining = Number((existing as any).tokens_remaining);
    const concurrent = Number((existing as any).concurrent);
    const updated_at = typeof (existing as any).updated_at === "string" ? (existing as any).updated_at : input.now_iso;

    state = {
      fingerprint,
      hour_start,
      tokens_remaining: Number.isFinite(tokens_remaining) ? tokens_remaining : tokensPerHour,
      concurrent: Number.isFinite(concurrent) ? concurrent : 0,
      updated_at,
    };
  } else {
    state = {
      fingerprint,
      hour_start: nowHour,
      tokens_remaining: tokensPerHour,
      concurrent: 0,
      updated_at: input.now_iso,
    };
  }

  if (state.hour_start !== nowHour) {
    state.hour_start = nowHour;
    state.tokens_remaining = tokensPerHour;
    state.concurrent = 0;
  }

  if (maxConcurrent > 0 && state.concurrent >= maxConcurrent) {
    if (!input.simulate) {
      writeJsonFile(counterFile, state);
    }
    return {
      decision: "DELAY",
      reason: "MAX_CONCURRENT",
      retry_after: addHoursIso(input.now_iso, 0),
      fingerprint,
      autonomy_mode_effective,
    };
  }

  if (tokensPerHour > 0 && state.tokens_remaining <= 0) {
    // Retry at next hour boundary.
    const retry_after = addHoursIso(nowHour, 1);
    if (!input.simulate) {
      writeJsonFile(counterFile, state);
    }
    return {
      decision: "DELAY",
      reason: "TOKEN_EXHAUSTED",
      retry_after,
      fingerprint,
      autonomy_mode_effective,
    };
  }

  // Simulations must not consume tokens or write governor state.
  if (input.simulate) {
    return {
      decision: "ALLOW",
      reason: null,
      retry_after: null,
      fingerprint,
      autonomy_mode_effective,
    };
  }

  // Decrement token on run start (not success).
  if (tokensPerHour > 0) {
    state.tokens_remaining = Math.max(0, state.tokens_remaining - 1);
  }
  state.updated_at = input.now_iso;
  writeJsonFile(counterFile, state);

  return {
    decision: "ALLOW",
    reason: null,
    retry_after: null,
    fingerprint,
    autonomy_mode_effective,
  };
}

// Tier-∞.1: allow callers to run the governor for a fixed fingerprint.
export function checkGovernor(input: {
  fingerprint: string;
  autonomy_mode: string;
  now_iso: string;
  simulate?: boolean;
}): RunGovernorDecision {
  return runGovernorForFingerprint({
    fingerprint: input.fingerprint,
    autonomy_mode: input.autonomy_mode,
    now_iso: input.now_iso,
    simulate: input.simulate === true,
  });
}
