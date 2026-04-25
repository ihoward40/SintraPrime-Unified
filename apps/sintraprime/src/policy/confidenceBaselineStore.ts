import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export type ConfidenceBaselineRecord = {
  fingerprint: string;
  command: string;
  policy_version: string;
  autonomy_mode: string;
  capability_set: string[];
  score: number;
  band: string;
  action: string;
  captured_at: string;
};

export function normalizeCommand(command: string): string {
  return String(command ?? "")
    .trim()
    .replace(/\s+/g, " ");
}

export function normalizePolicyVersion(policyVersion: string | undefined): string {
  const v = String(policyVersion ?? "").trim();
  return v || "unversioned";
}

export function normalizeAutonomyMode(mode: string | undefined): string {
  const v = String(mode ?? "").trim();
  return v || "OFF";
}

export function normalizeCapabilitySet(caps: string[]): string[] {
  const uniq = new Set<string>();
  for (const c of caps ?? []) {
    const v = String(c ?? "").trim();
    if (v) uniq.add(v);
  }
  return Array.from(uniq).sort((a, b) => a.localeCompare(b));
}

export function computeConfidenceFingerprint(args: {
  command: string;
  policy_version: string;
  autonomy_mode: string;
  capability_set: string[];
}): string {
  const normalized_command = normalizeCommand(args.command);
  const policy_version = normalizePolicyVersion(args.policy_version);
  const autonomy_mode = normalizeAutonomyMode(args.autonomy_mode);
  const capability_set = normalizeCapabilitySet(args.capability_set);

  const payload = JSON.stringify(
    {
      normalized_command,
      policy_version,
      autonomy_mode,
      capability_set,
    },
    null,
    0
  );

  const hash = crypto.createHash("sha256").update(payload, "utf8").digest("hex");
  return `conf_${hash}`;
}

function ensureDir(relDir: string) {
  const full = path.resolve(process.cwd(), relDir);
  fs.mkdirSync(full, { recursive: true });
  return full;
}

function readJsonIfExists(filePath: string): any | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

export function listBaselineCandidates(fingerprint: string): string[] {
  const dir = ensureDir(path.join("runs", "confidence-baseline"));
  const files = fs.readdirSync(dir).filter((f) => f.startsWith(fingerprint) && f.endsWith(".json"));
  return files
    .map((f) => path.join(dir, f))
    .sort((a, b) => a.localeCompare(b));
}

export function readLatestBaseline(fingerprint: string): ConfidenceBaselineRecord | null {
  const candidates = listBaselineCandidates(fingerprint);
  if (!candidates.length) return null;

  // Prefer captured_at ordering if present; fallback to filename ordering.
  const parsed = candidates
    .map((p) => ({ p, json: readJsonIfExists(p) }))
    .filter((x) => x.json && typeof x.json === "object")
    .map((x) => {
      const capturedAt = typeof x.json.captured_at === "string" ? x.json.captured_at : "";
      const t = new Date(capturedAt).getTime();
      return { p: x.p, json: x.json as ConfidenceBaselineRecord, t: Number.isFinite(t) ? t : -1 };
    });

  if (!parsed.length) return null;

  parsed.sort((a, b) => {
    if (a.t !== b.t) return a.t - b.t;
    return a.p.localeCompare(b.p);
  });

  return parsed.slice(-1)[0]!.json;
}

export function writeBaselineRecord(args: {
  record: ConfidenceBaselineRecord;
  override: boolean;
}): { path: string; wrote: boolean } {
  const dir = ensureDir(path.join("runs", "confidence-baseline"));
  const canonical = path.join(dir, `${args.record.fingerprint}.json`);

  if (!args.override) {
    if (fs.existsSync(canonical)) {
      return { path: canonical, wrote: false };
    }
    fs.writeFileSync(canonical, JSON.stringify(args.record, null, 2) + "\n", "utf8");
    return { path: canonical, wrote: true };
  }

  const ts = args.record.captured_at.replace(/[:.]/g, "-");
  const overridePath = path.join(dir, `${args.record.fingerprint}.${ts}.json`);
  fs.writeFileSync(overridePath, JSON.stringify(args.record, null, 2) + "\n", "utf8");
  return { path: overridePath, wrote: true };
}

export function writeConfidenceCheck(args: {
  execution_id: string;
  payload: unknown;
}): string {
  const dir = ensureDir(path.join("runs", "confidence-checks"));
  const filePath = path.join(dir, `${args.execution_id}.json`);
  fs.writeFileSync(filePath, JSON.stringify(args.payload, null, 2) + "\n", "utf8");
  return filePath;
}

export function writeConfidenceAck(args: {
  fingerprint: string;
  acknowledged_at: string;
  payload: unknown;
}): string {
  const dir = ensureDir(path.join("runs", "confidence-acks"));
  const ts = args.acknowledged_at.replace(/[:.]/g, "-");
  const filePath = path.join(dir, `${args.fingerprint}.${ts}.json`);
  fs.writeFileSync(filePath, JSON.stringify(args.payload, null, 2) + "\n", "utf8");
  return filePath;
}
