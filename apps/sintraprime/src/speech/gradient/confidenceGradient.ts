export type SpeechSeverity = "calm" | "warning" | "urgent";
export type SpeechCadence = "slow" | "normal" | "fast";

function normalizeConfidence(c: number): number {
  if (!Number.isFinite(c)) return 1;
  if (c > 1) return Math.max(0, Math.min(1, c / 100));
  return Math.max(0, Math.min(1, c));
}

export function mapConfidenceToSpeech(confidenceRaw: number): {
  confidence: number;
  severity: SpeechSeverity;
  cadence: SpeechCadence;
  prefix: string;
} {
  const confidence = normalizeConfidence(confidenceRaw);

  if (confidence >= 0.75) {
    return { confidence, severity: "calm", cadence: "normal", prefix: "[CALM]" };
  }

  if (confidence >= 0.45) {
    return { confidence, severity: "warning", cadence: "normal", prefix: "[WARN]" };
  }

  return { confidence, severity: "urgent", cadence: "fast", prefix: "[URGENT]" };
}
