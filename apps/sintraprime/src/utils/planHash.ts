import crypto from "node:crypto";

function stableNormalize(value: unknown): unknown {
  if (value === null) return null;
  if (value === undefined) return null;
  if (typeof value !== "object") return value;

  if (Array.isArray(value)) {
    return value.map(stableNormalize);
  }

  const obj = value as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(obj).sort()) {
    const v = obj[key];
    if (v === undefined) continue;
    out[key] = stableNormalize(v);
  }
  return out;
}

export function computePlanHash(plan: unknown): string {
  const normalized = stableNormalize(plan);
  const payload = JSON.stringify(normalized);
  return crypto.createHash("sha256").update(payload).digest("hex");
}
