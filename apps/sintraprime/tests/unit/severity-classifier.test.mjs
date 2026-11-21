import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { classifyRun } = require('../../src/monitoring/severity-classifier.ts');

const policy = { version: 'test', severity_policy: {
  sev0: { multiplier: 1, action: ['quarantine'] }, sev1: { multiplier: 5, action: ['slack_escalate'] },
  sev2: { multiplier: 3, action: ['slack_alert'] }, sev3: { multiplier: 2, action: ['weekly_review'] },
  sev4: { multiplier: 0, action: ['ledger_only'] },
}, risk_flags: { retry_loop: { misconfig_weight: 6 }, batch_job: { legit_weight: 2 } } };
const run = { Run_ID: 'one', Timestamp: '2026-01-01T00:00:00Z', Scenario_Name: 'example', Job_Type: 'OTHER', Status: 'Success', Credits_Total: 100, Severity: 'SEV4', Misconfig_Likelihood: 'Low', Variance_Multiplier: 1 };

test('classifies threshold boundaries and returns policy actions', () => {
  for (const [credits, severity, action] of [[100, 'SEV4', 'ledger_only'], [200, 'SEV3', 'weekly_review'], [300, 'SEV2', 'slack_alert'], [500, 'SEV1', 'slack_escalate']]) {
    const result = classifyRun({ ...run, Credits_Total: credits }, 100, policy);
    assert.equal(result.severity, severity);
    assert.deepEqual(result.actions, [action]);
  }
});

test('PII spike overrides severity and risk signals affect likelihood', () => {
  const result = classifyRun({ ...run, Credits_Total: 200, Risk_Flags: ['pii_exposure'], retry_count: 6, is_batch_job: true }, 100, policy);
  assert.equal(result.severity, 'SEV0');
  assert.deepEqual(result.actions, ['quarantine']);
  assert.equal(result.misconfigLikelihood, 'Medium');
  assert.equal(result.misconfigScore, 4);
  assert.equal(result.legitScore, 2);
});
