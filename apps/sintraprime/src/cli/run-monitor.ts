#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { classifyRun } from "../monitoring/severity-classifier.js";
import { formatAlert } from "../monitoring/slack-alert-formatter.js";
import { summarizeCreditRuns } from "../monitoring/credit-aggregator.js";
import { JobType, RunStatus, SeverityLevel } from "../monitoring/types.js";
import type { RunRecordLegacy, PolicyConfig, SlackMessage } from "../monitoring/types.js";

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected a JSON object");
  return value as Record<string, unknown>;
}
function text(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} is required`);
  return value;
}
function number(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error(`${label} must be a finite nonnegative number`);
  return value;
}
function normalizeRun(value: unknown, preclassified = false): RunRecordLegacy {
  const raw = object(value);
  const timestamp = text(raw.Timestamp ?? raw.timestamp, "timestamp");
  if (!Number.isFinite(Date.parse(timestamp))) throw new Error("timestamp must be a valid date");
  const credits = number(raw.Credits_Total ?? raw.credits_total, "credits_total");
  const base = raw.Baseline_Expected_Credits ?? raw.baseline_expected_credits;
  const baseline = base === undefined ? undefined : number(base, "baseline_expected_credits");
  const severity = raw.Severity ?? raw.severity ?? (preclassified ? undefined : SeverityLevel.SEV4);
  if (!Object.values(SeverityLevel).includes(severity as SeverityLevel)) throw new Error("Invalid or missing severity");
  const job = raw.Job_Type ?? raw.job_type ?? JobType.OTHER;
  const status = raw.Status ?? raw.status ?? RunStatus.Success;
  if (!Object.values(JobType).includes(job as JobType) || !Object.values(RunStatus).includes(status as RunStatus)) throw new Error("Invalid job_type or status");
  const likelihood = raw.Misconfig_Likelihood ?? raw.misconfig_likelihood ?? "Low";
  if (!["Low", "Medium", "High"].includes(String(likelihood))) throw new Error("Invalid misconfig_likelihood");
  const variance = raw.Variance_Multiplier ?? raw.variance_multiplier;
  if (preclassified && variance === undefined) throw new Error("Report records require variance_multiplier");
  const flags = raw.Risk_Flags ?? raw.risk_flags;
  const knownFlags = new Set(["retry_loop", "unbounded_iterator", "missing_idempotency", "sudden_prompt_growth", "deployment_correlation", "batch_job", "backfill_mode", "linear_scaling", "pii_exposure", "regulatory_data"]);
  if (flags !== undefined && (!Array.isArray(flags) || !flags.every(flag => typeof flag === "string" && knownFlags.has(flag)))) throw new Error("Invalid risk_flags");
  const optionalNumber = (key: string) => raw[key] === undefined ? undefined : number(raw[key], key);
  const optionalBoolean = (key: string) => {
    if (raw[key] !== undefined && typeof raw[key] !== "boolean") throw new Error(`${key} must be boolean`);
    return raw[key] as boolean | undefined;
  };
  return {
    Run_ID: text(raw.Run_ID ?? raw.run_id, "run_id"), Timestamp: timestamp,
    Scenario_Name: text(raw.Scenario_Name ?? raw.scenario_name, "scenario_name"),
    Scenario_ID: typeof (raw.Scenario_ID ?? raw.scenario_id) === "string" ? String(raw.Scenario_ID ?? raw.scenario_id) : undefined,
    Job_Type: job as JobType, Status: status as RunStatus, Credits_Total: credits,
    Severity: severity as SeverityLevel, Misconfig_Likelihood: likelihood as RunRecordLegacy["Misconfig_Likelihood"],
    Baseline_Expected_Credits: baseline,
    Variance_Multiplier: variance === undefined ? (baseline ? credits / baseline : 0) : number(variance, "variance_multiplier"),
    Risk_Flags: flags as RunRecordLegacy["Risk_Flags"],
    Risk_Summary: typeof (raw.Risk_Summary ?? raw.risk_summary) === "string" ? String(raw.Risk_Summary ?? raw.risk_summary) : undefined,
    Artifacts_Link: typeof (raw.Artifacts_Link ?? raw.artifacts_link) === "string" ? String(raw.Artifacts_Link ?? raw.artifacts_link) : undefined,
    retry_count: optionalNumber("retry_count"), input_item_count: optionalNumber("input_item_count"),
    has_max_items_config: optionalBoolean("has_max_items_config"), has_idempotency_key: optionalBoolean("has_idempotency_key"),
    is_batch_job: optionalBoolean("is_batch_job"), is_backfill: optionalBoolean("is_backfill"),
    prompt_version: typeof raw.prompt_version === "string" ? raw.prompt_version : undefined,
    deployment_timestamp: typeof raw.deployment_timestamp === "string" ? raw.deployment_timestamp : undefined,
  };
}
function loadPolicy(): PolicyConfig {
  const preferred = path.join("config", "monitoring-policy.v1.json");
  const file = fs.existsSync(preferred) ? preferred : path.join("config", "sintraprime-policy.json");
  const policy = object(JSON.parse(fs.readFileSync(file, "utf8")));
  const severities = object(policy.severity_policy);
  for (const name of ["sev0", "sev1", "sev2", "sev3", "sev4"]) {
    const severity = object(severities[name]);
    number(severity.multiplier, `${name}.multiplier`);
    if (!Array.isArray(severity.action) || !severity.action.every(action => typeof action === "string")) throw new Error(`Invalid ${name}.action`);
  }
  object(policy.risk_flags);
  return policy as unknown as PolicyConfig;
}
function markdown(message: SlackMessage): string {
  const lines: string[] = [];
  for (const block of message.blocks) {
    if (block.type === "header") lines.push(block.text.text);
    else if (block.type === "section") {
      if (block.text) lines.push(block.text.text);
      for (const field of block.fields ?? []) lines.push(field.text);
    } else if (block.type === "context") {
      for (const item of block.elements) if (item.text) lines.push(item.text);
    } else if (block.type === "actions") {
      for (const item of block.elements) if (item.url) lines.push(`[${item.text.text}](${item.url})`);
    } else lines.push("---");
  }
  return lines.join("\n");
}
try {
  const [command, file] = process.argv.slice(2);
  if (!command || !["classify", "alert", "report"].includes(command)) throw new Error("Usage: run-monitor.ts [classify|alert|report] <input_file>");
  const inputFile = file ?? (command === "report" ? "runs/all_runs.json" : undefined);
  if (!inputFile) throw new Error("Run data path is required");
  const input: unknown = JSON.parse(fs.readFileSync(inputFile, "utf8"));
  if (command === "report") {
    if (!Array.isArray(input)) throw new Error("Report input must be an array of run records");
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 7);
    const runs = input.map(raw => normalizeRun(raw, true)).filter(run => Date.parse(run.Timestamp) >= +start && Date.parse(run.Timestamp) <= +end);
    console.log(JSON.stringify(summarizeCreditRuns(runs, start, end), null, 2));
  } else {
    const run = normalizeRun(input);
    const baseline = run.Baseline_Expected_Credits;
    if (baseline === undefined || baseline <= 0) throw new Error("A positive baseline_expected_credits is required");
    const classification = classifyRun(run, baseline, loadPolicy());
    if (command === "classify") console.log(JSON.stringify(classification, null, 2));
    else console.log(markdown(formatAlert(run, classification, "https://notion.so", "https://notion.so")));
  }
} catch (error) {
  console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
