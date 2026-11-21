import fs from "node:fs";
import path from "node:path";
function positiveInteger(name: string, fallback: number): number | null {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}
export function shouldDecayConfidence(input: { fingerprint: string; now_iso: string }): { decay: boolean; reason: string; successes_in_window: number; required_successes: number; horizon_hours: number } {
  const horizon = positiveInteger("CONFIDENCE_DECAY_HOURS", 72);
  const required = positiveInteger("CONFIDENCE_MIN_SUCCESS", 1);
  const result = { decay: true, reason: "INVALID_OR_MISSING_EVIDENCE", successes_in_window: 0, required_successes: required ?? 0, horizon_hours: horizon ?? 0 };
  const now = Date.parse(input.now_iso);
  if (!horizon || !required || !Number.isFinite(now) || typeof input.fingerprint !== "string" || !input.fingerprint) return result;
  const safe = input.fingerprint.replace(/[\\/<>:"|?*\x00-\x1F]/g, "_").slice(0, 120);
  let data: any;
  try { data = JSON.parse(fs.readFileSync(path.join(process.cwd(), "runs", "requalification", "probation", `${safe}.json`), "utf8")); } catch { return result; }
  if (!data || data.fingerprint !== input.fingerprint || data.state !== "PROBATION" || !Number.isSafeInteger(data.success_count) || data.success_count < 1 || !Number.isSafeInteger(data.required_successes) || data.required_successes < 1 || typeof data.last_success_at !== "string") return result;
  const last = Date.parse(data.last_success_at);
  if (!Number.isFinite(last) || last > now || now - last > horizon * 3600000) return result;
  result.successes_in_window = 1;
  result.decay = required > 1;
  result.reason = result.decay ? "INSUFFICIENT_SUCCESS_EVIDENCE" : "SUFFICIENT_SUCCESS_EVIDENCE";
  return result;
}
