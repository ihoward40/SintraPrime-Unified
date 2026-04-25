export type SpeechDecisionInput = {
  confidence: number; // 0–1
  severity: "low" | "medium" | "high";
  budgetRemaining: number;
  lastSpokenAt?: number;
  now: number;
};

export type SpeechDecision =
  | {
      allow: false;
      reason: "BUDGET_EXHAUSTED" | "LOW_CONFIDENCE";
      silenceUntil?: number;
    }
  | {
      allow: true;
      reason: "OK";
      redactionLevel: "low" | "medium" | "high";
    };

function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 1;
  return Math.max(0, Math.min(1, n));
}

export function decideSpeech(input: SpeechDecisionInput): SpeechDecision {
  const confidence = clamp01(input.confidence);

  // 1) Hard stop: no budget
  if (input.budgetRemaining <= 0) {
    return { allow: false, reason: "BUDGET_EXHAUSTED" };
  }

  // 2) Confidence-based silence window
  if (confidence < 0.4) {
    return {
      allow: false,
      reason: "LOW_CONFIDENCE",
      silenceUntil: input.now + 60_000,
    };
  }

  // 3) Escalating redaction
  const redactionLevel = confidence < 0.6 ? "high" : confidence < 0.8 ? "medium" : "low";

  // 4) Allow exactly one speak
  return {
    allow: true,
    reason: "OK",
    redactionLevel,
  };
}
