import fs from "node:fs";
import path from "node:path";

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

function parseIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

function readJson(filePath: string): any | null {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function withinWindow(successes: Array<{ execution_id: string; timestamp: string }>, nowIso: string, windowHours: number) {
  const nowMs = new Date(nowIso).getTime();
  if (!Number.isFinite(nowMs)) return successes;
  const windowMs = Math.max(0, windowHours) * 60 * 60 * 1000;
  return successes.filter((s) => {
    const t = new Date(s.timestamp).getTime();
    if (!Number.isFinite(t)) return false;
    return nowMs - t <= windowMs;
  });
}

export function evaluateProbationEligibility(input: { fingerprint: string; now_iso: string }) {
  const counterFile = path.join(
    process.cwd(),
    "runs",
    "requalification",
    "probation",
    `${safeFilePart(input.fingerprint)}.json`
  );
  const raw = readJson(counterFile);
  if (!raw || typeof raw !== "object") return null;

  const window_hours = Number(raw.window_hours);
  const windowHours = Number.isFinite(window_hours) ? window_hours : Math.max(1, parseIntEnv("PROBATION_WINDOW_HOURS", 24));

  const required = Math.max(1, parseIntEnv("PROBATION_SUCCESS_REQUIRED", 3));
  const successes = Array.isArray(raw.successes)
    ? raw.successes
        .filter((s: any) => s && typeof s === "object" && typeof s.execution_id === "string" && typeof s.timestamp === "string")
        .map((s: any) => ({ execution_id: String(s.execution_id), timestamp: String(s.timestamp) }))
    : [];

  const inWindow = withinWindow(successes, input.now_iso, windowHours);

  if (inWindow.length >= required) {
    return {
      kind: "RequalificationRecommended" as const,
      fingerprint: input.fingerprint,
      recommendation: "ELIGIBLE" as const,
      successes: inWindow.length,
      required,
      window_hours: windowHours,
    };
  }

  return null;
}
