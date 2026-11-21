import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const hook = require.resolve('tsx/cjs');
const cli = fileURLToPath(new URL('../../src/cli/run-monitor.ts', import.meta.url));
const policy = { version: 'test', severity_policy: {
  sev0: { multiplier: 1, action: ['quarantine'] }, sev1: { multiplier: 3, action: ['slack_escalate'] },
  sev2: { multiplier: 2, action: ['slack_alert'] }, sev3: { multiplier: 1.5, action: ['weekly_review'] },
  sev4: { multiplier: 0, action: ['ledger_only'] },
}, risk_flags: {} };

function fixture(run) {
  const dir = mkdtempSync(join(tmpdir(), 'monitor-cli-'));
  mkdirSync(join(dir, 'config'));
  writeFileSync(join(dir, 'config', 'monitoring-policy.v1.json'), JSON.stringify(policy));
  const write = (name, value) => { const path = join(dir, name); writeFileSync(path, JSON.stringify(value)); return path; };
  const invoke = (...args) => spawnSync(process.execPath, ['--require', hook, '-e', 'require(process.argv[1])', cli, ...args], { cwd: dir, encoding: 'utf8', timeout: 15000 });
  try { run({ dir, write, invoke }); } finally { rmSync(dir, { recursive: true, force: true }); }
}
const snake = () => ({ run_id: 'R1', timestamp: new Date().toISOString(), scenario_name: 'Example', scenario_id: 'example', job_type: 'OTHER', status: 'Success', credits_total: 400, baseline_expected_credits: 100, severity: 'SEV1', variance_multiplier: 4, misconfig_likelihood: 'Low' });

test('legacy classify uses real function API for snake and Pascal records', () => fixture(({ write, invoke, dir }) => {
  const pascal = { Run_ID: 'P1', Timestamp: new Date().toISOString(), Scenario_Name: 'Example', Credits_Total: 400, Baseline_Expected_Credits: 100 };
  for (const data of [snake(), pascal]) {
    const result = invoke('classify', write('run.json', data));
    assert.equal(result.status, 0, result.stderr);
    const out = JSON.parse(result.stdout);
    assert.equal(out.severity, 'SEV1');
    assert.equal(out.varianceMultiplier, 4);
    assert.deepEqual(out.actions, ['slack_escalate']);
  }
  assert.equal(existsSync(join(dir, 'runs')), false);
}));

test('legacy alert renders actual Slack blocks as Markdown without sending', () => fixture(({ write, invoke, dir }) => {
  const result = invoke('alert', write('run.json', snake()));
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SEV1/);
  assert.match(result.stdout, /Credit Spike/);
  assert.match(result.stdout, /R1/);
  assert.equal(existsSync(join(dir, 'runs')), false);
}));

test('legacy report summarizes supplied recent records without ledger writes', () => fixture(({ write, invoke, dir }) => {
  const second = { ...snake(), run_id: 'R2', credits_total: 100, severity: 'SEV4', variance_multiplier: 1 };
  const old = { ...snake(), run_id: 'old', timestamp: '2000-01-01T00:00:00Z', credits_total: 99999 };
  const result = invoke('report', write('runs.json', [snake(), second, old]));
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.summary_stats.total_runs, 2);
  assert.equal(report.summary_stats.total_credits, 500);
  assert.equal(report.top_scenarios_by_total[0].avg_credits, 250);
  assert.deepEqual(report.top_spike_runs.map(r => r.Run_ID), ['R1']);
  assert.equal(existsSync(join(dir, 'runs')), false);
}));

test('legacy CLI rejects unsupported commands and invalid data explicitly', () => fixture(({ write, invoke, dir }) => {
  assert.notEqual(invoke('unknown').status, 0);
  assert.notEqual(invoke('classify').status, 0);
  assert.notEqual(invoke('classify', join(dir, 'missing.json')).status, 0);
  assert.notEqual(invoke('classify', write('bad.json', { ...snake(), credits_total: 'not-a-number' })).status, 0);
  assert.notEqual(invoke('classify', write('zero.json', { ...snake(), baseline_expected_credits: 0 })).status, 0);
  assert.notEqual(invoke('report', write('object.json', snake())).status, 0);
}));
