/**
 * Baseline Calculator
 * Calculates healthy baseline credit spend per scenario
 * 
 * Responsibilities:
 * - Calculate median credits for "healthy" runs
 * - Store baselines in config file
 * - Update baselines weekly for stable scenarios
 */

import fs from "node:fs";
import path from "node:path";
import type { BaselineData, RunStatus } from "./types.js";
import { getRunsByScenario, readRunsFromLedger } from "./run-logger.js";

/**
 * Calculate baseline credit spend for a scenario
 */
export async function calculateBaseline(
  scenarioId: string,
  daysBack = 30
): Promise<number> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - daysBack);

  // Get all runs for this scenario
  const allRuns = getRunsByScenario(scenarioId);
  
  // Filter to "healthy" runs within date range
  const healthyRuns = allRuns.filter(run => {
    const runDate = new Date(run.Timestamp);
    const isInRange = runDate >= startDate && runDate <= endDate;
    const isHealthy = run.Status === "Success" && (run.retry_count ?? 0) <= 1;
    return isInRange && isHealthy;
  });

  if (healthyRuns.length === 0) {
    console.log(`[baseline-calculator] No healthy runs found for ${scenarioId}`);
    return 0;
  }

  // Calculate median
  const credits = healthyRuns.map(r => r.Credits_Total).sort((a, b) => a - b);
  const medianIndex = Math.floor(credits.length / 2);
  const median = credits.length % 2 === 0
    ? (credits[medianIndex - 1]! + credits[medianIndex]!) / 2
    : credits[medianIndex]!;

  console.log(`[baseline-calculator] Calculated baseline for ${scenarioId}: ${median.toFixed(2)} (from ${healthyRuns.length} healthy runs)`);

  return median;
}

/**
 * Update all baselines for stable scenarios
 */
export async function updateAllBaselines(): Promise<void> {
  console.log("[baseline-calculator] Updating baselines for all scenarios...");

  // Get all runs from the last 30 days
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 30);
  const allRuns = readRunsFromLedger(startDate, endDate);

  // Group by scenario
  const scenarioIds = new Set(allRuns.map(r => r.Scenario_ID || r.Scenario_Name));

  // Load existing baselines
  const baselines = loadBaselines();
  const updates: BaselineData[] = [];

  for (const scenarioId of scenarioIds) {
    const median = await calculateBaseline(scenarioId, 30);
    
    if (median > 0) {
      const baselineData: BaselineData = {
        scenario_id: scenarioId,
        median_credits: median,
        calculated_at: new Date().toISOString(),
        sample_size: allRuns.filter(r => 
          (r.Scenario_ID || r.Scenario_Name) === scenarioId
        ).length,
        last_updated: new Date().toISOString(),
      };
      
      updates.push(baselineData);
      baselines.set(scenarioId, baselineData);
    }
  }

  // Save updated baselines
  saveBaselines(baselines);

  console.log(`[baseline-calculator] Updated ${updates.length} baselines`);
  updates.forEach(b => {
    console.log(`  - ${b.scenario_id}: ${b.median_credits.toFixed(2)} credits (n=${b.sample_size})`);
  });
}

/**
 * Get baseline for a scenario
 */
export function getBaseline(scenarioId: string): number {
  const baselines = loadBaselines();
  const baseline = baselines.get(scenarioId);
  return baseline?.median_credits ?? 0;
}

/**
 * Load baselines from config file
 */
function loadBaselines(): Map<string, BaselineData> {
  const baselinesPath = getBaselinesPath();
  
  if (!fs.existsSync(baselinesPath)) {
    return new Map();
  }

  try {
    const content = fs.readFileSync(baselinesPath, "utf-8");
    const data = JSON.parse(content) as { baselines: BaselineData[] };
    
    const map = new Map<string, BaselineData>();
    for (const baseline of data.baselines) {
      map.set(baseline.scenario_id, baseline);
    }
    
    return map;
  } catch (err) {
    console.error(`[baseline-calculator] Failed to load baselines: ${err}`);
    return new Map();
  }
}

/**
 * Save baselines to config file
 */
function saveBaselines(baselines: Map<string, BaselineData>): void {
  const baselinesPath = getBaselinesPath();
  
  // Ensure directory exists
  const dir = path.dirname(baselinesPath);
  fs.mkdirSync(dir, { recursive: true });

  const data = {
    version: "1.0.0",
    updated_at: new Date().toISOString(),
    baselines: Array.from(baselines.values()),
  };

  fs.writeFileSync(baselinesPath, JSON.stringify(data, null, 2), "utf-8");
  console.log(`[baseline-calculator] Saved baselines to ${baselinesPath}`);
}

/**
 * Get baselines file path
 */
function getBaselinesPath(): string {
  return process.env.CREDIT_BASELINES_PATH 
    || path.join(process.cwd(), "config", "credit-baselines.json");
}

/**
 * Check if a scenario is stable (eligible for baseline update)
 */
export function isScenarioStable(
  scenarioId: string,
  weeksBack = 2
): boolean {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - (weeksBack * 7));

  const runs = getRunsByScenario(scenarioId);
  const recentRuns = runs.filter(r => {
    const runDate = new Date(r.Timestamp);
    return runDate >= startDate && runDate <= endDate;
  });

  // Check if there are any SEV0/SEV1 incidents
  const hasIncidents = recentRuns.some(r => 
    r.Severity === "SEV0" || r.Severity === "SEV1"
  );

  // Check for consistent credit usage (low variance)
  const credits = recentRuns.map(r => r.Credits_Total);
  if (credits.length < 5) {
    return false; // Not enough data
  }

  const avg = credits.reduce((sum, c) => sum + c, 0) / credits.length;
  const variance = credits.reduce((sum, c) => sum + Math.pow(c - avg, 2), 0) / credits.length;
  const stdDev = Math.sqrt(variance);
  const coefficientOfVariation = stdDev / avg;

  return !hasIncidents && coefficientOfVariation < 0.3;
}
