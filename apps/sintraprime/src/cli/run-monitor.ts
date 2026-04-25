#!/usr/bin/env node
import fs from 'node:fs';
import { SeverityClassifier } from '../monitoring/severityClassifier.js';
import { RunLogger } from '../monitoring/runLogger.js';
import { CaseManager } from '../monitoring/caseManager.js';
import { SlackAlertFormatter } from '../monitoring/slackAlertFormatter.js';
import { CreditAggregator } from '../monitoring/creditAggregator.js';
import type { MonitoringPolicy, RunRecord } from '../monitoring/types.js';

const command = process.argv[2];

const policyPath = 'config/monitoring-policy.v1.json';
const policy: MonitoringPolicy = JSON.parse(fs.readFileSync(policyPath, 'utf-8'));

const classifier = new SeverityClassifier(policy);
const logger = new RunLogger();
const caseManager = new CaseManager();
const alertFormatter = new SlackAlertFormatter();
const aggregator = new CreditAggregator();

if (command === 'classify') {
  // Example: classify a run
  const runDataPath = process.argv[3];
  if (!runDataPath) {
    console.error('Error: Run data path is required');
    process.exit(1);
  }
  const runData = JSON.parse(fs.readFileSync(runDataPath, 'utf-8'));

  const classification = classifier.classify(runData);
  console.log(JSON.stringify(classification, null, 2));
} else if (command === 'alert') {
  // Example: generate Slack alert
  const runDataPath = process.argv[3];
  if (!runDataPath) {
    console.error('Error: Run data path is required');
    process.exit(1);
  }
  const runData: RunRecord = JSON.parse(fs.readFileSync(runDataPath, 'utf-8'));

  const alert = alertFormatter.format(runData);
  console.log(alertFormatter.renderMarkdown(alert));
} else if (command === 'report') {
  // Example: generate weekly report
  const runsDataPath = process.argv[3] || 'runs/all_runs.json';
  const allRuns: RunRecord[] = JSON.parse(fs.readFileSync(runsDataPath, 'utf-8'));

  const report = aggregator.generateWeeklyReport(allRuns, 7);
  console.log(JSON.stringify(report, null, 2));
} else {
  console.error('Usage: run-monitor.ts [classify|alert|report] <input_file>');
  process.exit(1);
}
