import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { logRun, readRunsFromLedger, verifyRunArtifact } = require('../../src/monitoring/run-logger.ts');
const { aggregateCredits } = require('../../src/monitoring/credit-aggregator.ts');

test('local ledger, integrity sidecar and credit report agree', async () => {
  const original = process.cwd();
  const notionId = process.env.NOTION_RUNS_LEDGER_DB_ID;
  delete process.env.NOTION_RUNS_LEDGER_DB_ID;
  const dir = mkdtempSync(join(tmpdir(), 'monitoring-'));
  try {
    process.chdir(dir);
    const now = new Date();
    const base = { Timestamp: now.toISOString(), Scenario_Name: 'Demo', Scenario_ID: 'demo', Job_Type: 'OTHER', Status: 'Success', Severity: 'SEV1', Misconfig_Likelihood: 'Low', Baseline_Expected_Credits: 100, Variance_Multiplier: 3 };
    await logRun({ ...base, Run_ID: 'a', Credits_Total: 300 });
    await logRun({ ...base, Run_ID: 'b', Credits_Total: 100, Severity: 'SEV4', Variance_Multiplier: 1 });
    assert.equal(readRunsFromLedger(new Date(now.getTime() - 1000), new Date(now.getTime() + 1000)).length, 2);
    const date = now.toISOString().slice(0, 10);
    assert.equal(verifyRunArtifact('a', date), true);
    const file = join(dir, 'runs', 'CREDIT_MONITORING', date, 'run_a.json');
    writeFileSync(file, readFileSync(file, 'utf8') + ' ');
    assert.equal(verifyRunArtifact('a', date), false);
    const report = await aggregateCredits(7);
    assert.equal(report.summary_stats.total_runs, 2);
    assert.equal(report.summary_stats.total_credits, 400);
    assert.equal(report.summary_stats.sev1_count, 1);
    assert.equal(report.top_scenarios_by_total[0].avg_credits, 200);
    assert.deepEqual(report.top_spike_runs.map(r => r.Run_ID), ['a']);
  } finally {
    if (notionId === undefined) delete process.env.NOTION_RUNS_LEDGER_DB_ID;
    else process.env.NOTION_RUNS_LEDGER_DB_ID = notionId;
    process.chdir(original); rmSync(dir, { recursive: true, force: true });
  }
});
