export type RedactionLevel = "normal" | "strict" | "paranoid";

export function redactionLevelForConfidence(confidence?: number): RedactionLevel {
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    return "normal";
  }

  const c = confidence > 1 ? Math.min(1, confidence / 100) : Math.max(0, Math.min(1, confidence));

  if (c >= 0.75) return "normal";
  if (c >= 0.45) return "strict";
  return "paranoid";
}
