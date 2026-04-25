#!/usr/bin/env tsx
/**
 * Credit Monitoring CLI
 * Command-line interface for the SintraPrime Credit Monitoring System
 * 
 * Usage:
 *   tsx src/cli/run-monitoring.ts log --run-id RUN-123 --credits 2400 --scenario BINDER_v2
 *   tsx src/cli/run-monitoring.ts weekly-review
 *   tsx src/cli/run-monitoring.ts update-baselines
 *   tsx src/cli/run-monitoring.ts classify --fixture tests/monitoring/fixtures/high-credit-spike.json
 */

import fs from "node:fs";
import path from "node:path";
import { classifyRun, generateRiskSummary } from "../monitoring/severity-classifier.js";
import { logRun } from "../monitoring/run-logger.js";
import { createCase } from "../monitoring/case-manager.js";
import { formatAlert, sendSlackAlert } from "../monitoring/slack-alert-formatter.js";
import { generateWeeklyReport } from "../monitoring/credit-aggregator.js";
import { updateAllBaselines, getBaseline } from "../monitoring/baseline-calculator.js";
import type { RunRecordLegacy as RunRecord, PolicyConfig, JobType, RunStatus } from "../monitoring/types.js";
import { JobType as JobTypeEnum, RunStatus as RunStatusEnum, SeverityLevel, MisconfigLikelihood } from "../monitoring/types.js";

// Load policy configuration
function loadPolicy(): PolicyConfig {
  const policyPath = path.join(process.cwd(), "config", "sintraprime-policy.json");
  const content = fs.readFileSync(policyPath, "utf-8");
  return JSON.parse(content) as PolicyConfig;
}

// Parse command-line arguments
function parseArgs(): { command: string; args: Record<string, string> } {
  const args = process.argv.slice(2);
  const command = args[0] || "help";
  
  const parsedArgs: Record<string, string> = {};
  for (let i = 1; i < args.length; i++) {
    const a = args[i];
    if (typeof a === "string" && a.startsWith("--")) {
      const key = a.slice(2);
      const value = args[i + 1] ?? "";
      parsedArgs[key] = value;
      i++;
    }
  }
  
  return { command, args: parsedArgs };
}

function normalizeRunRecord(raw: any): RunRecord {
  if (raw && typeof raw === "object" && typeof raw.Run_ID === "string") {
    return raw as RunRecord;
  }

  const nowIso = new Date().toISOString();
  const baseline =
    (typeof raw?.Baseline_Expected_Credits === "number" && raw.Baseline_Expected_Credits) ||
    (typeof raw?.baseline_expected_credits === "number" && raw.baseline_expected_credits) ||
    0;

  return {
    Run_ID: String(raw?.run_id ?? raw?.Run_ID ?? "UNKNOWN"),
    Timestamp: String(raw?.timestamp ?? raw?.Timestamp ?? nowIso),
    Scenario_Name: String(
      raw?.scenario_name ??
        raw?.Scenario_Name ??
        raw?.scenario_id ??
        raw?.Scenario_ID ??
        "UNKNOWN"
    ),
    Scenario_ID: raw?.scenario_id ?? raw?.Scenario_ID,
    Job_Type: (raw?.job_type ?? raw?.Job_Type ?? JobTypeEnum.OTHER) as JobType,
    Status: (raw?.status ?? raw?.Status ?? RunStatusEnum.Success) as RunStatus,
    Credits_Total: Number(raw?.credits_total ?? raw?.Credits_Total ?? 0),
    Credits_In: raw?.credits_in ?? raw?.Credits_In,
    Credits_Out: raw?.credits_out ?? raw?.Credits_Out,
    Model: raw?.model ?? raw?.Model,
    Input_Tokens: raw?.input_tokens ?? raw?.Input_Tokens,
    Output_Tokens: raw?.output_tokens ?? raw?.Output_Tokens,
    Artifacts_Link: raw?.artifacts_link ?? raw?.Artifacts_Link,
    Severity: (raw?.severity ?? raw?.Severity ?? SeverityLevel.SEV4) as any,
    Risk_Flags: raw?.risk_flags ?? raw?.Risk_Flags,
    Risk_Summary: raw?.risk_summary ?? raw?.Risk_Summary,
    Misconfig_Likelihood: (raw?.misconfig_likelihood ?? raw?.Misconfig_Likelihood ?? MisconfigLikelihood.Low) as any,
    Baseline_Expected_Credits: baseline,
    Variance_Multiplier: Number(raw?.variance_multiplier ?? raw?.Variance_Multiplier ?? 0),

    retry_count: raw?.retry_count,
    has_max_items_config: raw?.has_max_items_config,
    has_idempotency_key: raw?.has_idempotency_key,
    prompt_version: raw?.prompt_version,
    deployment_timestamp: raw?.deployment_timestamp,
    is_batch_job: raw?.is_batch_job,
    is_backfill: raw?.is_backfill,
    input_item_count: raw?.input_item_count,
  };
}

// Command: log
async function cmdLog(args: Record<string, string>): Promise<void> {
  const runId = args["run-id"];
  const credits = parseFloat(args["credits"] || "0");
  const scenarioId = args["scenario"] || args["scenario-id"] || "UNKNOWN";
  const scenarioName = args["scenario-name"] || scenarioId;
  const jobType = (args["job-type"] || "OTHER") as JobType;
  const status = (args["status"] || "Success") as RunStatus;

  if (!runId) {
    console.error("Error: --run-id is required");
    process.exit(1);
  }

  if (credits <= 0) {
    console.error("Error: --credits must be > 0");
    process.exit(1);
  }

  // Get baseline
  const baseline = getBaseline(scenarioId);
  
  // Create run record
  const runRecord: RunRecord = {
    Run_ID: runId,
    Timestamp: new Date().toISOString(),
    Scenario_Name: scenarioName,
    Scenario_ID: scenarioId,
    Job_Type: jobType,
    Status: status,
    Credits_Total: credits,
    Severity: SeverityLevel.SEV4, // Will be updated by classifier
    Misconfig_Likelihood: MisconfigLikelihood.Low,
    Variance_Multiplier: 0,
    Baseline_Expected_Credits: baseline,
  };

  // Load policy and classify
  const policy = loadPolicy();
  const classification = classifyRun(runRecord, baseline, policy);

  // Update run record with classification
  runRecord.Severity = classification.severity;
  runRecord.Misconfig_Likelihood = classification.misconfigLikelihood;
  runRecord.Variance_Multiplier = classification.varianceMultiplier;
  runRecord.Risk_Flags = classification.riskFlags;
  runRecord.Risk_Summary = generateRiskSummary(classification);

  // Log the run
  await logRun(runRecord);

  console.log(`\n✓ Run logged successfully`);
  console.log(`  Severity: ${classification.severity}`);
  console.log(`  Variance: ${classification.varianceMultiplier.toFixed(2)}×`);
  console.log(`  Misconfig Likelihood: ${classification.misconfigLikelihood}`);

  // Create case if needed
  if (classification.actions.includes("create_case") || classification.actions.includes("slack_alert")) {
    console.log(`\n⚠ Creating case for ${classification.severity} incident...`);
    const caseRecord = await createCase(runRecord, classification.severity, classification.riskFlags);
    console.log(`  Case ID: ${caseRecord.Case_ID}`);

    // Send Slack alert
    const defaultWebhook = process.env.SLACK_WEBHOOK_URL_DEFAULT;
    if (defaultWebhook) {
      const alert = formatAlert(
        runRecord,
        classification,
        caseRecord.notion_url || "https://notion.so",
        `https://notion.so/run-${runId}`
      );
      await sendSlackAlert(alert, defaultWebhook);
      console.log(`  Slack alert sent`);
    }
  }
}

// Command: weekly-review
async function cmdWeeklyReview(): Promise<void> {
  console.log("Generating weekly credit review...\n");
  await generateWeeklyReport();
  console.log("\n✓ Weekly review complete");
}

// Command: update-baselines
async function cmdUpdateBaselines(): Promise<void> {
  console.log("Updating credit baselines for all scenarios...\n");
  await updateAllBaselines();
  console.log("\n✓ Baselines updated");
}

// Command: classify
async function cmdClassify(args: Record<string, string>): Promise<void> {
  const fixturePath = args["fixture"];
  
  if (!fixturePath) {
    console.error("Error: --fixture is required");
    process.exit(1);
  }

  // Load fixture
  const content = fs.readFileSync(fixturePath, "utf-8");
  const runRecord = normalizeRunRecord(JSON.parse(content));

  // Get baseline
  const baseline = runRecord.Baseline_Expected_Credits || 0;

  // Load policy and classify
  const policy = loadPolicy();
  const classification = classifyRun(runRecord, baseline, policy);

  // Print results
  console.log(`\n=== Classification Results ===`);
  console.log(`Run ID: ${runRecord.Run_ID}`);
  console.log(`Scenario: ${runRecord.Scenario_Name}`);
  console.log(`Credits: ${runRecord.Credits_Total} (Baseline: ${baseline})`);
  console.log(`\nSeverity: ${classification.severity}`);
  console.log(`Variance Multiplier: ${classification.varianceMultiplier.toFixed(2)}×`);
  console.log(`Misconfig Likelihood: ${classification.misconfigLikelihood}`);
  console.log(`Misconfig Score: ${classification.misconfigScore}`);
  console.log(`Legit Score: ${classification.legitScore}`);
  console.log(`\nRisk Flags: ${classification.riskFlags.join(", ") || "None"}`);
  console.log(`\nPolicy Actions:`);
  classification.actions.forEach(action => console.log(`  - ${action}`));
  console.log(`\nRisk Summary: ${generateRiskSummary(classification)}`);
}

// Command: help
function cmdHelp(): void {
  console.log(`
SintraPrime Credit Monitoring CLI

Usage:
  tsx src/cli/run-monitoring.ts <command> [options]

Commands:
  log                    Log a new run
    --run-id <id>        Run identifier (required)
    --credits <n>        Total credits consumed (required)
    --scenario <id>      Scenario ID (required)
    --scenario-name <n>  Scenario name (optional)
    --job-type <type>    Job type: BINDER_EXPORT|RECONCILE_BACKFILL|ANALYSIS|OTHER
    --status <status>    Status: Success|Failed|Quarantined|Escalated

  weekly-review          Generate weekly credit review report

  update-baselines       Update credit baselines for all scenarios

  classify               Classify a run from a fixture file
    --fixture <path>     Path to JSON fixture file (required)

  help                   Show this help message

Examples:
  # Log a run
  tsx src/cli/run-monitoring.ts log --run-id RUN-123 --credits 2400 --scenario BINDER_v2

  # Generate weekly review
  tsx src/cli/run-monitoring.ts weekly-review

  # Update baselines
  tsx src/cli/run-monitoring.ts update-baselines

  # Test classifier with fixture
  tsx src/cli/run-monitoring.ts classify --fixture tests/monitoring/fixtures/high-credit-spike.json
`);
}

// Main
async function main(): Promise<void> {
  const { command, args } = parseArgs();

  try {
    switch (command) {
      case "log":
        await cmdLog(args);
        break;
      case "weekly-review":
        await cmdWeeklyReview();
        break;
      case "update-baselines":
        await cmdUpdateBaselines();
        break;
      case "classify":
        await cmdClassify(args);
        break;
      case "help":
        cmdHelp();
        break;
      default:
        console.error(`Unknown command: ${command}`);
        cmdHelp();
        process.exit(1);
    }
  } catch (error) {
    console.error(`Error: ${error}`);
    process.exit(1);
  }
}

main();
