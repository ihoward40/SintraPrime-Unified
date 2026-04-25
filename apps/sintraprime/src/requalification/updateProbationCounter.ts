import fs from "node:fs";
import path from "node:path";

import { readRequalificationState } from "./requalification.js";

export type ProbationCounterArtifact = {
  fingerprint: string;
  state: "PROBATION";
  success_count: number;
  required_successes: number;
  last_success_at: string;
  notes: string[];
};

export type ProbationRunResult = {
  // Minimal shape: this module is intentionally decoupled from the full receipt schema.
  status: string;
  now_iso: string;

  governor_decision: "ALLOW" | "DENY" | "DELAY";

  // Friction flags
  policy_denied: boolean;
  throttled: boolean;
  rollback_recorded: boolean;
  approval_required: boolean;

  autonomy_mode: string;
  autonomy_mode_effective: string;

  steps: Array<{ read_only?: boolean }>;
};

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

function clampNonNegativeInt(n: unknown, fallback: number): number {
  const v = typeof n === "number" ? n : Number(n);
  if (!Number.isFinite(v)) return fallback;
  return Math.max(0, Math.floor(v));
}

function parseIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJsonSafe(filePath: string): any | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function writeJsonFile(filePath: string, data: unknown) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", { encoding: "utf8" });
}

function probationDir() {
  return path.join(process.cwd(), "runs", "requalification", "probation");
}

function probationPath(fingerprint: string) {
  return path.join(probationDir(), `${safeFilePart(fingerprint)}.json`);
}

function modeRank(mode: string): number {
  const m = String(mode ?? "OFF");
  if (m === "OFF") return 0;
  if (m === "READ_ONLY_AUTONOMY") return 1;
  if (m === "PROPOSE_ONLY_AUTONOMY") return 2;
  if (m === "APPROVAL_GATED_AUTONOMY") return 3;
  // Unknown modes are treated as most permissive.
  return 99;
}

function qualifiesAsSuccess(runResult: ProbationRunResult): { ok: boolean; notes: string[] } {
  const notes = ["All runs were read-only", "No policy denials", "No throttles"];

  if (runResult.status !== "success") return { ok: false, notes };
  if (runResult.governor_decision !== "ALLOW") return { ok: false, notes };

  if (runResult.policy_denied) return { ok: false, notes };
  if (runResult.throttled) return { ok: false, notes };
  if (runResult.rollback_recorded) return { ok: false, notes };
  if (runResult.approval_required) return { ok: false, notes };

  const escalated = modeRank(runResult.autonomy_mode_effective) > modeRank(runResult.autonomy_mode);
  if (escalated) return { ok: false, notes };

  const steps = Array.isArray(runResult.steps) ? runResult.steps : [];
  const allReadOnly = steps.every((s: any) => s?.read_only === true);
  if (!allReadOnly) return { ok: false, notes };

  return { ok: true, notes };
}

export function updateProbationCounter(input: {
  fingerprint: string;
  runResult: ProbationRunResult;
}): { success_count: number; required_successes: number } | null {
  const rq = readRequalificationState(input.fingerprint);
  if (rq?.state !== "PROBATION") return null;

  const required_successes = Math.max(1, parseIntEnv("PROBATION_SUCCESS_REQUIRED", 5));
  const file = probationPath(input.fingerprint);

  const existing = readJsonSafe(file);
  const current: ProbationCounterArtifact = {
    fingerprint: input.fingerprint,
    state: "PROBATION",
    success_count: clampNonNegativeInt(existing?.success_count, 0),
    required_successes: clampNonNegativeInt(existing?.required_successes, required_successes),
    last_success_at:
      typeof existing?.last_success_at === "string" && existing.last_success_at.trim()
        ? String(existing.last_success_at)
        : "1970-01-01T00:00:00Z",
    notes: Array.isArray(existing?.notes) ? existing.notes.map((n: any) => String(n)) : [],
  };

  const q = qualifiesAsSuccess(input.runResult);
  const next: ProbationCounterArtifact = {
    ...current,
    required_successes,
    notes: q.notes,
  };

  if (q.ok) {
    next.success_count = current.success_count + 1;
    next.last_success_at = input.runResult.now_iso;
  }

  writeJsonFile(file, next);

  return { success_count: next.success_count, required_successes: next.required_successes };
}
