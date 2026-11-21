import fs from "node:fs";
import path from "node:path";
import { createHash, randomUUID } from "node:crypto";

type Signal = "THROTTLE" | "ROLLBACK" | "POLICY_DENIAL";
type Policy = { initial_score: number; penalties: Record<Signal, number> };
const validScore = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
function json(file: string): any { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; } }
function policy(): Policy | null {
  const p = json(path.join(process.cwd(), "config", "confidence-policy.json"));
  if (!p || !validScore(p.initial_score) || !p.penalties || !["THROTTLE", "ROLLBACK", "POLICY_DENIAL"].every(s => validScore(p.penalties[s]))) return null;
  return p;
}
function key(fingerprint: string): string { return createHash("sha256").update(fingerprint).digest("hex"); }
function statePath(fingerprint: string): string { return path.join(process.cwd(), "runs", "confidence", "fingerprint", `${key(fingerprint)}.json`); }
function eventDir(fingerprint: string): string { return path.join(process.cwd(), "runs", "confidence", "penalties", key(fingerprint)); }
// Interpret stored JSON numbers by their shortest decimal representation.
function decimal(value: number): [bigint, number] {
  const [mantissa = "0", exponent = "0"] = value.toString().split("e");
  const [whole, fraction = ""] = mantissa.split(".");
  const scale = fraction.length - Number(exponent);
  const digits = BigInt(whole + fraction);
  return scale < 0 ? [digits * 10n ** BigInt(-scale), 0] : [digits, scale];
}
function subtractPenalties(cap: number, penalties: number[]): number {
  const values = [cap, ...penalties].map(decimal);
  const scale = values.reduce((max, [, s]) => Math.max(max, s), 0);
  const scaled = values.map(([n, s]) => n * 10n ** BigInt(scale - s));
  const remaining = scaled.slice(1).reduce((n, p) => n - p, scaled[0]!);
  if (remaining <= 0n) return 0;
  let result = Number(`${remaining}e-${scale}`);
  const [rounded, roundedScale] = decimal(result);
  if (rounded * 10n ** BigInt(Math.max(0, scale - roundedScale)) > remaining * 10n ** BigInt(Math.max(0, roundedScale - scale))) {
    const bits = new DataView(new ArrayBuffer(8));
    bits.setFloat64(0, result);
    bits.setBigUint64(0, bits.getBigUint64(0) - 1n);
    result = bits.getFloat64(0);
  }
  return result;
}
export function readConfidence(fingerprint: string): { fingerprint: string; confidence: number; reason: string } {
  if (typeof fingerprint !== "string" || !fingerprint) return { fingerprint, confidence: 0, reason: "INVALID_FINGERPRINT" };
  const p = policy();
  if (!p) return { fingerprint, confidence: 0, reason: "INVALID_OR_MISSING_POLICY" };
  const state = json(statePath(fingerprint));
  if (!state || state.fingerprint !== fingerprint || !validScore(state.confidence)) return { fingerprint, confidence: 0, reason: "INVALID_OR_MISSING_STATE" };
  let entries: string[];
  try { entries = fs.readdirSync(eventDir(fingerprint)); } catch (e: any) { if (e?.code === "ENOENT") entries = []; else return { fingerprint, confidence: 0, reason: "INVALID_EVENT_LEDGER" }; }
  const penalties: number[] = [];
  for (const entry of entries) {
    const event = json(path.join(eventDir(fingerprint), entry));
    if (!event || event.fingerprint !== fingerprint || !["THROTTLE", "ROLLBACK", "POLICY_DENIAL"].includes(event.signal) || !validScore(event.penalty)) return { fingerprint, confidence: 0, reason: "INVALID_EVENT_LEDGER" };
    penalties.push(event.penalty);
  }
  return { fingerprint, confidence: subtractPenalties(Math.min(state.confidence, p.initial_score), penalties), reason: "VALID_STATE" };
}
export function updateConfidence(input: { fingerprint: string; signal: Signal }): { fingerprint: string; confidence: number; reason: string } {
  if (typeof input.fingerprint !== "string" || !input.fingerprint) return { fingerprint: input.fingerprint, confidence: 0, reason: "INVALID_FINGERPRINT" };
  const p = policy();
  const before = readConfidence(input.fingerprint);
  const valid = p && before.reason === "VALID_STATE" && Object.hasOwn(p.penalties, input.signal);
  const dir = eventDir(input.fingerprint);
  // The temporary file lives outside the ledger: readers only see completed events.
  const staging = path.join(process.cwd(), "runs", "confidence", "event-staging");
  fs.mkdirSync(dir, { recursive: true });
  fs.mkdirSync(staging, { recursive: true });
  const id = randomUUID();
  const temp = path.join(staging, `${id}.json`);
  const event = valid ? { fingerprint: input.fingerprint, signal: input.signal, penalty: p.penalties[input.signal] } : { fingerprint: input.fingerprint, reason: "UNCONFIGURED_OR_INVALID_UPDATE" };
  fs.writeFileSync(temp, JSON.stringify(event) + "\n", { encoding: "utf8", flag: "wx" });
  fs.renameSync(temp, path.join(dir, `${id}.json`));
  return readConfidence(input.fingerprint);
}
