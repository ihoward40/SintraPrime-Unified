import fs from "node:fs";
import path from "node:path";

type ProbationCounterFile = {
  fingerprint: string;
  window_hours: number;
  successes: Array<{ execution_id: string; timestamp: string }>;
};

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
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
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", { encoding: "utf8" });
}

function parseIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

function pruneToWindow(successes: Array<{ execution_id: string; timestamp: string }>, nowIso: string, windowHours: number) {
  const nowMs = new Date(nowIso).getTime();
  if (!Number.isFinite(nowMs)) return successes;
  const windowMs = Math.max(0, windowHours) * 60 * 60 * 1000;
  return successes.filter((s) => {
    const t = new Date(s.timestamp).getTime();
    if (!Number.isFinite(t)) return false;
    return nowMs - t <= windowMs;
  });
}

export function writeProbationCounter(input: {
  fingerprint: string;
  execution_id: string;
  timestamp: string;
}): { file: string; data: ProbationCounterFile } {
  const dir = path.join(process.cwd(), "runs", "requalification", "probation");
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${safeFilePart(input.fingerprint)}.json`);
  const window_hours = Math.max(1, parseIntEnv("PROBATION_WINDOW_HOURS", 24));

  let data: ProbationCounterFile = { fingerprint: input.fingerprint, window_hours, successes: [] };

  const existing = readJsonFile<unknown>(file);
  if (isRecord(existing)) {
    const fp = typeof (existing as any).fingerprint === "string" ? (existing as any).fingerprint : input.fingerprint;
    const wh = Number((existing as any).window_hours);
    const successes = Array.isArray((existing as any).successes) ? (existing as any).successes : [];
    data = {
      fingerprint: fp,
      window_hours: Number.isFinite(wh) ? wh : window_hours,
      successes: Array.isArray(successes)
        ? successes
            .filter((s: any) => isRecord(s) && typeof s.execution_id === "string" && typeof s.timestamp === "string")
            .map((s: any) => ({ execution_id: String(s.execution_id), timestamp: String(s.timestamp) }))
        : [],
    };
  }

  data.successes = pruneToWindow(data.successes, input.timestamp, data.window_hours);
  data.successes.push({ execution_id: input.execution_id, timestamp: input.timestamp });

  writeJsonFile(file, data);
  return { file, data };
}
