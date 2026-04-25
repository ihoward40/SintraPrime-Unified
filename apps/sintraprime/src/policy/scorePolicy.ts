import type { ScoreFeatures } from "./extractScoreFeatures.js";

type Reason = { code: string; weight: number; detail: string };

export function scorePolicy(input: {
  target: string;
  evaluated_at: string;
  policy_simulation: { would_run: boolean; decision: string; reasons?: any[] };
  features: ScoreFeatures;
  obs?: { planner_retry?: boolean; schema_tolerance_used?: boolean };
}) {
  const reasons: Reason[] = [];
  const decision = String(input.policy_simulation?.decision ?? "");

  // Hard blocks
  if (decision === "DENIED") {
    return finalize(
      0,
      "LOW",
      "BLOCK",
      [{ code: "POLICY_DENIED", weight: -999, detail: "Policy simulation denied execution" }],
      input
    );
  }

  const unresolved = Array.isArray(input.features.unresolved_capabilities)
    ? input.features.unresolved_capabilities
    : [];
  if (unresolved.length) {
    return finalize(
      0,
      "LOW",
      "BLOCK",
      [
        {
          code: "UNRESOLVED_CAPABILITY",
          weight: -999,
          detail: `No agent provides: ${unresolved.join(",")}`,
        },
      ],
      input
    );
  }

  if (input.features.domains.includes("invalid")) {
    return finalize(
      0,
      "LOW",
      "BLOCK",
      [{ code: "UNKNOWN_DOMAIN", weight: -999, detail: "At least one step URL could not be parsed" }],
      input
    );
  }

  // Baseline
  let score = 50;

  // Read-only vs writes
  if (input.features.writes === 0) {
    score += 25;
    reasons.push({ code: "READ_ONLY", weight: 25, detail: "All steps read_only=true" });
  } else {
    score -= 20;
    reasons.push({
      code: "WRITE_PRESENT",
      weight: -20,
      detail: "Contains write steps (approval-gated or denied by autonomy)",
    });
    if (input.features.approval_required) {
      score += 10;
      reasons.push({ code: "APPROVAL_GATED_WRITE", weight: 10, detail: "Write is behind approval boundary" });
      score -= 10;
      reasons.push({
        code: "PRESTATE_REQUIRED",
        weight: -10,
        detail: "Prestate capture required before approval to avoid stale plan",
      });
    }
  }

  // Domains sanity
  score += 10;
  reasons.push({
    code: "DOMAIN_ALLOWLIST_MATCH",
    weight: 10,
    detail: "Domains parse cleanly (further allowlist check is in policy)",
  });

  // Step count
  if (input.features.steps <= 5) {
    score += 5;
    reasons.push({ code: "LOW_STEP_COUNT", weight: 5, detail: `steps=${input.features.steps} <= 5` });
  }

  // Timeouts capped
  if (input.features.timeouts_capped === true) {
    score += 5;
    reasons.push({ code: "TIMEOUTS_CAPPED", weight: 5, detail: "All timeouts <= policy cap" });
  }

  // Agent versions pinned
  if (input.features.agent_versions_pinned === true) {
    score += 5;
    reasons.push({ code: "AGENT_VERSION_PINNED", weight: 5, detail: "agent_versions pinned" });
  }

  // Capabilities resolved
  if (input.features.capabilities.length && input.features.capabilities_resolved === true) {
    score += 5;
    reasons.push({ code: "CAPABILITIES_RESOLVED", weight: 5, detail: "All required_capabilities have providers" });
  }

  // Observability penalties
  if (input.obs?.planner_retry) {
    score -= 8;
    reasons.push({ code: "RETRY_OCCURRED", weight: -8, detail: "Planner retry occurred (variance detected)" });
  }
  if (input.obs?.schema_tolerance_used) {
    score -= 6;
    reasons.push({ code: "SCHEMA_TOLERANCE_USED", weight: -6, detail: "Non-strict parsing tolerance used" });
  }

  // Clamp
  score = Math.max(0, Math.min(100, score));

  const band = score >= 80 ? "HIGH" : score >= 55 ? "MEDIUM" : "LOW";

  let action: "AUTO_RUN" | "PROPOSE_FOR_APPROVAL" | "HUMAN_REVIEW_REQUIRED" | "BLOCK" =
    band === "HIGH" && input.features.writes === 0
      ? "AUTO_RUN"
      : input.features.writes > 0 && band !== "LOW"
        ? "PROPOSE_FOR_APPROVAL"
        : "HUMAN_REVIEW_REQUIRED";

  // If the sim indicates approval required, prefer proposing.
  if (decision === "APPROVAL_REQUIRED") {
    action = "PROPOSE_FOR_APPROVAL";
  }

  return finalize(score, band, action, reasons, input);
}

export type ConfidenceScoreOutput = ReturnType<typeof scorePolicy>;

function finalize(
  score: number,
  band: "LOW" | "MEDIUM" | "HIGH",
  action: "AUTO_RUN" | "PROPOSE_FOR_APPROVAL" | "HUMAN_REVIEW_REQUIRED" | "BLOCK",
  reasons: Reason[],
  input: any
) {
  return {
    kind: "ConfidenceScore",
    evaluated_at: input.evaluated_at,
    target: input.target,
    policy_simulation: input.policy_simulation,
    confidence: { score, band, action, reasons },
    features: input.features,
  };
}
