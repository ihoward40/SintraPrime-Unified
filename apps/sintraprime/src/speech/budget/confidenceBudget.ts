export function scaleBudgetByConfidence(baseBudget: number, confidence?: number): number {
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    return baseBudget;
  }

  const c = confidence > 1 ? Math.min(1, confidence / 100) : Math.max(0, Math.min(1, confidence));

  let multiplier = 1.0;
  if (c < 0.4) multiplier = 0.25;
  else if (c < 0.6) multiplier = 0.5;
  else if (c < 0.8) multiplier = 0.75;

  const scaled = Math.floor(baseBudget * multiplier);
  return Math.max(1, scaled);
}
