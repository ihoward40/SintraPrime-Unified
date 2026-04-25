function isNumber(x: unknown): x is number {
  return typeof x === "number" && Number.isFinite(x);
}

const WARN_THRESHOLD = 0.6;

export function renderConfidenceSpeech(prev: any, curr: any): string {
  const p = prev?.confidence_score ?? prev?.confidence;
  const c = curr?.confidence_score ?? curr?.confidence;

  if (!isNumber(c)) return "";

  if (isNumber(p)) {
    if (p >= WARN_THRESHOLD && c < WARN_THRESHOLD) {
      return "Confidence dropped below safe threshold.";
    }
    if (p < WARN_THRESHOLD && c >= WARN_THRESHOLD) {
      return "Confidence recovered above safe threshold.";
    }
    return "";
  }

  // First observation
  if (c < WARN_THRESHOLD) {
    return "Confidence is low.";
  }

  return "";
}
