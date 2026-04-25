import fs from "node:fs";
import path from "node:path";

export type RequalificationStateName = "ACTIVE" | "SUSPENDED" | "PROBATION" | "ELIGIBLE";

export type RequalificationState = {
  fingerprint: string;
  state: RequalificationStateName;
  cause: string;
  since: string;
  cooldown_until: string | null;
  activated_at?: string;
  decayed_at?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
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

function statePath(fingerprint: string) {
  return path.join(process.cwd(), "runs", "requalification", "state", `${safeFilePart(fingerprint)}.json`);
}

function eventsDir() {
  return path.join(process.cwd(), "runs", "requalification", "events");
}

export type AutonomyStateTransition = {
  fingerprint: string;
  from: RequalificationStateName;
  to: RequalificationStateName;
  reason: string;
  timestamp: string;
};

export function isRequalificationEnabled(): boolean {
  return process.env.REQUALIFICATION_ENABLED === "1";
}

export function readRequalificationState(fingerprint: string): RequalificationState | null {
  const raw = readJsonFile<unknown>(statePath(fingerprint));
  if (!isRecord(raw)) return null;
  const state = String((raw as any).state ?? "");
  if (state !== "ACTIVE" && state !== "SUSPENDED" && state !== "PROBATION" && state !== "ELIGIBLE") {
    return null;
  }
  const cause = typeof (raw as any).cause === "string" ? (raw as any).cause : "UNKNOWN";
  const since = typeof (raw as any).since === "string" ? (raw as any).since : "";
  const cooldown_until =
    typeof (raw as any).cooldown_until === "string" ? (raw as any).cooldown_until : null;
  const activated_at = typeof (raw as any).activated_at === "string" ? (raw as any).activated_at : undefined;
  const decayed_at = typeof (raw as any).decayed_at === "string" ? (raw as any).decayed_at : undefined;
  return {
    fingerprint,
    state: state as RequalificationStateName,
    cause,
    since,
    cooldown_until,
    activated_at,
    decayed_at,
  };
}

export function writeRequalificationState(state: RequalificationState) {
  writeJsonFile(statePath(state.fingerprint), state);
}

export function writeRequalificationEvent(input: {
  fingerprint: string;
  at_iso: string;
  event: string;
  details?: Record<string, unknown>;
}) {
  ensureDir(eventsDir());
  const ts = new Date(input.at_iso).getTime();
  const safeTs = Number.isFinite(ts) ? ts : Date.now();
  const file = path.join(eventsDir(), `${safeFilePart(input.fingerprint)}.${safeTs}.json`);
  writeJsonFile(file, {
    fingerprint: input.fingerprint,
    at: input.at_iso,
    event: input.event,
    details: input.details ?? null,
  });
}

function writeAutonomyStateTransitionEvent(input: AutonomyStateTransition) {
  ensureDir(eventsDir());
  const ts = new Date(input.timestamp).getTime();
  const safeTs = Number.isFinite(ts) ? ts : Date.now();
  const file = path.join(eventsDir(), `${safeFilePart(input.fingerprint)}.${safeTs}.json`);
  writeJsonFile(file, {
    fingerprint: input.fingerprint,
    from: input.from,
    to: input.to,
    reason: input.reason,
    timestamp: input.timestamp,
  });
}

// Tier-22.1: cooldown-driven watcher invoked at run start.
// No scheduler required; deterministic transitions only.
export function applyRequalificationCooldownWatcher(input: { now_iso: string }): AutonomyStateTransition[] {
  const states = listRequalificationStates();
  const out: AutonomyStateTransition[] = [];

  const nowMs = new Date(input.now_iso).getTime();
  if (!Number.isFinite(nowMs)) return out;

  for (const s of states) {
    if (s.state !== "SUSPENDED") continue;
    if (!s.cooldown_until) continue;
    const cooldownMs = new Date(s.cooldown_until).getTime();
    if (!Number.isFinite(cooldownMs)) continue;
    if (nowMs < cooldownMs) continue;

    const next: RequalificationState = {
      fingerprint: s.fingerprint,
      state: "PROBATION",
      cause: "COOLDOWN_ELAPSED",
      since: input.now_iso,
      cooldown_until: null,
    };
    writeRequalificationState(next);

    const transition: AutonomyStateTransition = {
      fingerprint: s.fingerprint,
      from: "SUSPENDED",
      to: "PROBATION",
      reason: "COOLDOWN_ELAPSED",
      timestamp: input.now_iso,
    };
    writeAutonomyStateTransitionEvent(transition);
    out.push(transition);
  }

  return out;
}

export function listRequalificationStates(): RequalificationState[] {
  const dir = path.join(process.cwd(), "runs", "requalification", "state");
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  const out: RequalificationState[] = [];
  for (const f of files) {
    const raw = readJsonFile<unknown>(path.join(dir, f));
    if (!isRecord(raw)) continue;
    const fp = typeof (raw as any).fingerprint === "string" ? (raw as any).fingerprint : null;
    if (!fp) continue;
    const parsed = readRequalificationState(fp);
    if (parsed) out.push(parsed);
  }
  out.sort((a, b) => a.fingerprint.localeCompare(b.fingerprint));
  return out;
}

export function requalifyScan(input: { now_iso: string }): {
  kind: "RequalificationScan";
  evaluated: number;
  eligible: string[];
  still_suspended: string[];
  entered_probation: string[];
  recommended: string[];
} {
  const states = listRequalificationStates();
  const eligible: string[] = [];
  const still_suspended: string[] = [];
  const entered_probation: string[] = [];
  const recommended: string[] = [];

  for (const s of states) {
    if (s.state === "SUSPENDED") {
      const cooldown = s.cooldown_until;
      if (cooldown && new Date(cooldown).getTime() <= new Date(input.now_iso).getTime()) {
        const next: RequalificationState = {
          ...s,
          state: "PROBATION",
          cause: s.cause,
          since: input.now_iso,
          cooldown_until: null,
        };
        writeRequalificationState(next);
        writeRequalificationEvent({
          fingerprint: s.fingerprint,
          at_iso: input.now_iso,
          event: "SUSPENDED_TO_PROBATION",
          details: { cause: s.cause },
        });
        entered_probation.push(s.fingerprint);
        continue;
      }
      still_suspended.push(s.fingerprint);
      continue;
    }

    if (s.state === "PROBATION") {
      continue;
    }

    if (s.state === "ELIGIBLE") {
      eligible.push(s.fingerprint);
      continue;
    }
  }

  return {
    kind: "RequalificationScan",
    evaluated: states.length,
    eligible,
    still_suspended,
    entered_probation,
    recommended,
  };
}

export function effectiveAutonomyModeForState(input: {
  autonomy_mode: string;
  state: RequalificationStateName;
}): string {
  if (input.autonomy_mode === "OFF") return "OFF";
  if (input.state === "PROBATION") return "READ_ONLY_AUTONOMY";
  return input.autonomy_mode;
}
