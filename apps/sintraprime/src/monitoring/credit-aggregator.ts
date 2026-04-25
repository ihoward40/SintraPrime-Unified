/**
 * Credit Aggregator
 * Performs weekly forensics - generates reports on credit spend by scenario
 * 
 * Responsibilities:
 * - Pull runs from last N days
 * - Group by scenario
 * - Calculate totals, averages, P95
 * - Identify top spenders and variance leaders
 * - Generate weekly report artifacts
 */

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import type {
  RunRecordLegacy as RunRecord,
  CreditReport,
  ScenarioSummary,
  SeverityLevel,
} from "./types.js";
import { readRunsFromLedger } from "./run-logger.js";

/**
 * Aggregate credits over the last N days
 */
export async function aggregateCredits(daysBack = 7): Promise<CreditReport> {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - daysBack);

  // Read runs from ledger
  const runs = readRunsFromLedger(startDate, endDate);

  // Group by scenario
  const scenarioMap = new Map<string, RunRecord[]>();
  for (const run of runs) {
    const scenarioId = run.Scenario_ID || run.Scenario_Name;
    if (!scenarioMap.has(scenarioId)) {
      scenarioMap.set(scenarioId, []);
    }
    scenarioMap.get(scenarioId)!.push(run);
  }

  // Calculate scenario summaries
  const scenarios: ScenarioSummary[] = [];
  for (const [scenarioId, scenarioRuns] of scenarioMap.entries()) {
    const totalCredits = scenarioRuns.reduce((sum, r) => sum + r.Credits_Total, 0);
    const avgCredits = totalCredits / scenarioRuns.length;
    
    // Calculate P95
    const sortedCredits = scenarioRuns.map(r => r.Credits_Total).sort((a, b) => a - b);
    const p95Index = Math.floor(sortedCredits.length * 0.95);
    const p95Credits = sortedCredits[p95Index] ?? 0;
    const maxCredits = sortedCredits[sortedCredits.length - 1] ?? 0;

    // Get baseline (average from runs)
    const baseline = scenarioRuns[0]?.Baseline_Expected_Credits ?? avgCredits;
    const varianceMultiplier = baseline > 0 ? avgCredits / baseline : 1;

    scenarios.push({
      scenario_id: scenarioId,
      total_credits: totalCredits,
      run_count: scenarioRuns.length,
      avg_credits: avgCredits,
      baseline,
      variance_multiplier: varianceMultiplier,
      p95_credits: p95Credits,
      max_credits: maxCredits,
    });
  }

  // Sort by total credits (descending)
  scenarios.sort((a, b) => b.total_credits - a.total_credits);

  // Find top spike runs
  const topSpikeRuns = runs
    .filter(r => r.Variance_Multiplier > 2)
    .sort((a, b) => b.Variance_Multiplier - a.Variance_Multiplier)
    .slice(0, 5);

  // Find baseline candidates (stable scenarios)
  const baselineCandidates = scenarios.filter(
    s => s.variance_multiplier < 1.2 && s.run_count >= 10
  );

  // Find policy violations
  const policyViolations = runs
    .filter(r => r.Severity === "SEV0" || r.Severity === "SEV1")
    .map(r => ({
      run_id: r.Run_ID,
      violation_type: r.Risk_Summary || "Credit spike",
      severity: r.Severity,
    }));

  // Calculate summary stats
  const totalCredits = runs.reduce((sum, r) => sum + r.Credits_Total, 0);
  const sev0Count = runs.filter(r => r.Severity === "SEV0").length;
  const sev1Count = runs.filter(r => r.Severity === "SEV1").length;
  const sev2Count = runs.filter(r => r.Severity === "SEV2").length;

  const report: CreditReport = {
    report_id: `CREDIT_REVIEW_${endDate.toISOString().split("T")[0]}`,
    period_start: startDate.toISOString(),
    period_end: endDate.toISOString(),
    top_scenarios_by_total: scenarios.slice(0, 5),
    top_spike_runs: topSpikeRuns,
    baseline_candidates: baselineCandidates.slice(0, 5),
    policy_violations: policyViolations,
    summary_stats: {
      total_credits: totalCredits,
      total_runs: runs.length,
      avg_credits_per_run: runs.length > 0 ? totalCredits / runs.length : 0,
      sev0_count: sev0Count,
      sev1_count: sev1Count,
      sev2_count: sev2Count,
    },
  };

  return report;
}

/**
 * Generate weekly credit review report
 */
export async function generateWeeklyReport(): Promise<void> {
  console.log("[credit-aggregator] Generating weekly credit review...");

  const report = await aggregateCredits(7);

  // Create directory structure
  const reviewsDir = path.join(process.cwd(), "runs", "CREDIT_REVIEWS");
  fs.mkdirSync(reviewsDir, { recursive: true });

  // Write report JSON
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const reportFile = path.join(reviewsDir, `weekly_${timestamp}.json`);
  const reportJson = JSON.stringify(report, null, 2);
  fs.writeFileSync(reportFile, reportJson, "utf-8");

  // Generate .sha256 sidecar
  const sha256 = crypto.createHash("sha256").update(reportJson).digest("hex");
  const sha256File = `${reportFile}.sha256`;
  fs.writeFileSync(sha256File, sha256, "utf-8");

  console.log(`[credit-aggregator] Report written to ${reportFile}`);
  console.log(`[credit-aggregator] SHA-256: ${sha256}`);

  // Print summary
  console.log("\n=== Weekly Credit Review Summary ===");
  console.log(`Period: ${report.period_start} to ${report.period_end}`);
  console.log(`Total Credits: ${report.summary_stats.total_credits.toLocaleString()}`);
  console.log(`Total Runs: ${report.summary_stats.total_runs}`);
  console.log(`SEV0: ${report.summary_stats.sev0_count}, SEV1: ${report.summary_stats.sev1_count}, SEV2: ${report.summary_stats.sev2_count}`);
  console.log("\nTop 5 Scenarios by Credit Spend:");
  report.top_scenarios_by_total.forEach((s, i) => {
    console.log(`  ${i + 1}. ${s.scenario_id}: ${s.total_credits.toLocaleString()} credits (${s.variance_multiplier.toFixed(2)}× baseline)`);
  });

  // Optional: Create Notion page and send Slack summary
  if (process.env.NOTION_API_TOKEN) {
    console.log("[credit-aggregator] Would create Notion review page");
  }

  if (process.env.SLACK_WEBHOOK_URL_DEFAULT) {
    console.log("[credit-aggregator] Would send Slack summary");
  }
}
