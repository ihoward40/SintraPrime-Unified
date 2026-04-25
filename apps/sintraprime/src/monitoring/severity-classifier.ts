/**
 * Severity Classifier
 * Assigns severity level and misconfig likelihood to each automation run
 * 
 * Key responsibilities:
 * - Calculate credit variance multiplier
 * - Score misconfig vs legit signals
 * - Assign severity (SEV0-4) based on policy
 * - Identify risk flags
 */

import {
  type RunRecordLegacy as RunRecord,
  type Classification,
  type MisconfigAssessment,
  type PolicyAction,
  type PolicyConfig,
  type RiskFlag,
  SeverityLevel,
  MisconfigLikelihood,
} from "./types.js";

/**
 * Classify a run based on credits, baseline, and policy configuration
 */
export function classifyRun(
  runData: RunRecord,
  baseline: number,
  policyConfig: PolicyConfig
): Classification {
  // Calculate variance multiplier
  const varianceMultiplier = baseline > 0 
    ? runData.Credits_Total / baseline 
    : 0;

  // Identify risk flags
  const riskFlags: RiskFlag[] = [];
  
  // Misconfig signals
  if ((runData.retry_count ?? 0) > 5) {
    riskFlags.push("retry_loop");
  }
  
  if (runData.has_max_items_config === false) {
    riskFlags.push("unbounded_iterator");
  }
  
  if (runData.has_idempotency_key === false) {
    riskFlags.push("missing_idempotency");
  }
  
  if (runData.prompt_version && varianceMultiplier > 2) {
    // Sudden prompt expansion without proper testing
    riskFlags.push("sudden_prompt_growth");
  }
  
  if (runData.deployment_timestamp) {
    // Deployment correlation - spike after recent deployment
    riskFlags.push("deployment_correlation");
  }
  
  // Legit signals
  if (runData.is_batch_job === true) {
    riskFlags.push("batch_job");
  }
  
  if (runData.is_backfill === true) {
    riskFlags.push("backfill_mode");
  }
  
  if (runData.input_item_count && runData.input_item_count > 0) {
    // Check for linear scaling
    const creditsPerItem = runData.Credits_Total / runData.input_item_count;
    const baselinePerItem = baseline / (runData.input_item_count || 1);
    if (Math.abs(creditsPerItem - baselinePerItem) < baselinePerItem * 0.2) {
      riskFlags.push("linear_scaling");
    }
  }
  
  // PII/Regulatory flags (would come from external metadata)
  // These are placeholder checks - in production would integrate with data classification
  if (runData.Risk_Flags?.includes("pii_exposure")) {
    riskFlags.push("pii_exposure");
  }
  
  if (runData.Risk_Flags?.includes("regulatory_data")) {
    riskFlags.push("regulatory_data");
  }

  // Calculate misconfig assessment
  const assessment = assessMisconfig(riskFlags, policyConfig);

  // Determine severity
  const severity = determineSeverity(
    varianceMultiplier,
    riskFlags,
    policyConfig
  );

  // Get policy actions for this severity
  const actions = getPolicyActions(severity, policyConfig);

  return {
    severity,
    misconfigLikelihood: assessment.likelihood,
    riskFlags,
    varianceMultiplier,
    misconfigScore: assessment.score,
    legitScore: calculateLegitScore(riskFlags, policyConfig),
    actions,
  };
}

/**
 * Assess likelihood of misconfiguration
 */
function assessMisconfig(
  riskFlags: RiskFlag[],
  policyConfig: PolicyConfig
): MisconfigAssessment {
  let misconfigScore = 0;
  let legitScore = 0;
  
  const misconfigSignals: Array<{ flag: RiskFlag; weight: number }> = [];
  const legitSignals: Array<{ flag: RiskFlag; weight: number }> = [];

  for (const flag of riskFlags) {
    const config = policyConfig.risk_flags[flag];
    if (!config) continue;

    if (config.misconfig_weight !== undefined && config.misconfig_weight > 0) {
      misconfigScore += config.misconfig_weight;
      misconfigSignals.push({ flag, weight: config.misconfig_weight });
    }

    if (config.legit_weight !== undefined && config.legit_weight > 0) {
      legitScore += config.legit_weight;
      legitSignals.push({ flag, weight: config.legit_weight });
    }
  }

  // Net score (misconfig - legit)
  const netScore = misconfigScore - legitScore;

  // Determine likelihood
  let likelihood: MisconfigLikelihood;
  if (netScore >= 6) {
    likelihood = MisconfigLikelihood.High;
  } else if (netScore >= 3) {
    likelihood = MisconfigLikelihood.Medium;
  } else {
    likelihood = MisconfigLikelihood.Low;
  }

  return {
    likelihood,
    score: netScore,
    signals: {
      misconfig: misconfigSignals,
      legit: legitSignals,
    },
  };
}

/**
 * Calculate legit score (opposite of misconfig)
 */
function calculateLegitScore(
  riskFlags: RiskFlag[],
  policyConfig: PolicyConfig
): number {
  let score = 0;
  for (const flag of riskFlags) {
    const config = policyConfig.risk_flags[flag];
    if (config?.legit_weight) {
      score += config.legit_weight;
    }
  }
  return score;
}

/**
 * Determine severity level based on variance and risk flags
 */
function determineSeverity(
  varianceMultiplier: number,
  riskFlags: RiskFlag[],
  policyConfig: PolicyConfig
): SeverityLevel {
  const hasPII = riskFlags.includes("pii_exposure");
  const hasRegulatory = riskFlags.includes("regulatory_data");

  // SEV0: Critical - PII/Regulatory exposure with any spike
  if ((hasPII || hasRegulatory) && varianceMultiplier >= policyConfig.severity_policy.sev0.multiplier) {
    return SeverityLevel.SEV0;
  }

  // SEV1: High - Significant spike
  if (varianceMultiplier >= policyConfig.severity_policy.sev1.multiplier) {
    return SeverityLevel.SEV1;
  }

  // SEV2: Medium - Moderate variance
  if (varianceMultiplier >= policyConfig.severity_policy.sev2.multiplier) {
    return SeverityLevel.SEV2;
  }

  // SEV3: Low - Minor variance
  if (varianceMultiplier >= policyConfig.severity_policy.sev3.multiplier) {
    return SeverityLevel.SEV3;
  }

  // SEV4: Info - Normal operation
  return SeverityLevel.SEV4;
}

/**
 * Get policy actions for a severity level
 */
function getPolicyActions(
  severity: SeverityLevel,
  policyConfig: PolicyConfig
): PolicyAction[] {
  const key = severity.toLowerCase() as keyof PolicyConfig["severity_policy"];
  return policyConfig.severity_policy[key]?.action ?? [];
}

/**
 * Generate risk summary text
 */
export function generateRiskSummary(classification: Classification): string {
  const parts: string[] = [];

  parts.push(`Variance: ${classification.varianceMultiplier.toFixed(2)}×`);
  parts.push(`Misconfig likelihood: ${classification.misconfigLikelihood}`);

  if (classification.riskFlags.length > 0) {
    const misconfigFlags = classification.riskFlags.filter(f => 
      !["batch_job", "backfill_mode", "linear_scaling"].includes(f)
    );
    const legitFlags = classification.riskFlags.filter(f => 
      ["batch_job", "backfill_mode", "linear_scaling"].includes(f)
    );

    if (misconfigFlags.length > 0) {
      parts.push(`Misconfig signals: ${misconfigFlags.join(", ")}`);
    }
    if (legitFlags.length > 0) {
      parts.push(`Legit signals: ${legitFlags.join(", ")}`);
    }
  }

  return parts.join(" | ");
}
