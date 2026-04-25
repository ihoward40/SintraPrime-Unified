export type ConfidenceSnapshot = {
  score: number;
  band: string;
  action: string;
};

export type ConfidenceRegressionResult = {
  kind: "ConfidenceRegression";
  regressed: boolean;
  delta: number;
  previous: { score: number; band: string } | null;
  current: { score: number; band: string };
  severity: "NONE" | "MINOR" | "MAJOR";
  requires_ack: boolean;
  reasons: string[];
};

export function compareConfidence(args: {
  previous: ConfidenceSnapshot | null;
  current: ConfidenceSnapshot;
  tolerance: number;
}): ConfidenceRegressionResult {
  const previous = args.previous;
  const current = args.current;
  const tolerance = Number.isFinite(args.tolerance) ? args.tolerance : 5;

  const prevScore = previous ? previous.score : null;
  const delta = (prevScore === null ? current.score : current.score - prevScore) ?? 0;

  const reasons: string[] = [];

  if (!previous) {
    return {
      kind: "ConfidenceRegression",
      regressed: false,
      delta: 0,
      previous: null,
      current: { score: current.score, band: current.band },
      severity: "NONE",
      requires_ack: false,
      reasons: ["NO_BASELINE"],
    };
  }

  const scoreDrop = previous.score - current.score;
  const bandDrop = previous.band !== current.band;
  const actionDrop = previous.action !== current.action;

  const isBandDropHighToLow = previous.band === "HIGH" && current.band === "LOW";
  const isBandDropHighToMed = previous.band === "HIGH" && current.band === "MEDIUM";
  const isActionDropAutoToHuman = previous.action === "AUTO_RUN" && current.action === "HUMAN_REVIEW_REQUIRED";

  const hard = isBandDropHighToLow || isActionDropAutoToHuman || scoreDrop >= 20;
  const soft = (!hard && scoreDrop >= 10 && scoreDrop <= 19) || (!hard && isBandDropHighToMed);

  if (scoreDrop >= tolerance) reasons.push(`SCORE_DROP_${scoreDrop}`);
  if (bandDrop) reasons.push(`BAND_${previous.band}_TO_${current.band}`);
  if (actionDrop) reasons.push(`ACTION_${previous.action}_TO_${current.action}`);

  if (hard) {
    return {
      kind: "ConfidenceRegression",
      regressed: true,
      delta: -scoreDrop,
      previous: { score: previous.score, band: previous.band },
      current: { score: current.score, band: current.band },
      severity: "MAJOR",
      requires_ack: true,
      reasons: reasons.length ? reasons : ["HARD_REGRESSION"],
    };
  }

  if (soft) {
    return {
      kind: "ConfidenceRegression",
      regressed: true,
      delta: -scoreDrop,
      previous: { score: previous.score, band: previous.band },
      current: { score: current.score, band: current.band },
      severity: "MINOR",
      requires_ack: false,
      reasons: reasons.length ? reasons : ["SOFT_REGRESSION"],
    };
  }

  // No regression (including score increase)
  return {
    kind: "ConfidenceRegression",
    regressed: false,
    delta: -scoreDrop,
    previous: { score: previous.score, band: previous.band },
    current: { score: current.score, band: current.band },
    severity: "NONE",
    requires_ack: false,
    reasons: reasons.length ? reasons : ["NO_REGRESSION"],
  };
}
