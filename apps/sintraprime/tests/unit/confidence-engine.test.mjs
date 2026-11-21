import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { readConfidence, updateConfidence } = require('../../src/confidence/updateConfidence.ts');
const { shouldDecayConfidence } = require('../../src/confidence/evaluateConfidenceDecay.ts');
const cwd = process.cwd();
function fixture(t) { const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'confidence-')); process.chdir(dir); t.after(() => { process.chdir(cwd); fs.rmSync(dir, { recursive: true, force: true }); }); return dir; }
function write(file, value) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value)); }
function policy() { write('config/confidence-policy.json', { initial_score: 0.9, penalties: { THROTTLE: 0.1, ROLLBACK: 0.3, POLICY_DENIAL: 0.2 } }); }
function state(fp, score) { const key = createHash('sha256').update(fp).digest('hex'); write(`runs/confidence/fingerprint/${key}.json`, { fingerprint: fp, confidence: score }); }
test('policy and state fail closed, updates are persistent and isolated', t => { fixture(t); state('a/b', 0.9); assert.equal(readConfidence('a/b').confidence, 0); policy(); assert.equal(readConfidence('missing').confidence, 0); assert.equal(readConfidence('a/b').confidence, 0.9); assert.ok(Math.abs(updateConfidence({ fingerprint:'a/b', signal:'ROLLBACK' }).confidence - 0.6) < 1e-12); assert.ok(Math.abs(readConfidence('a/b').confidence - 0.6) < 1e-12); state('a_b', 0.8); assert.equal(readConfidence('a_b').confidence, 0.8); assert.ok(Math.abs(updateConfidence({fingerprint:'a/b', signal:'THROTTLE'}).confidence - 0.5) < 1e-12); policy(); assert.ok(Math.abs(readConfidence('a/b').confidence - 0.5) < 1e-12); state('bad', 2); assert.equal(readConfidence('bad').confidence, 0); write('config/confidence-policy.json', {initial_score: 1, penalties:{}}); assert.equal(readConfidence('a/b').confidence, 0); });
test('decay requires fresh attributable success at inclusive horizon', t => { fixture(t); const check = () => shouldDecayConfidence({fingerprint:'abc', now_iso:'2026-01-04T00:00:00.000Z'}); assert.equal(check().decay,true); write('runs/requalification/probation/abc.json',{ fingerprint:'abc', state:'PROBATION', success_count:3, required_successes:3, last_success_at:'2026-01-01T00:00:00.000Z', notes:[] }); assert.equal(check().decay,false); process.env.CONFIDENCE_MIN_SUCCESS='2'; t.after(() => delete process.env.CONFIDENCE_MIN_SUCCESS); assert.equal(check().decay,true); delete process.env.CONFIDENCE_MIN_SUCCESS; write('runs/requalification/probation/abc.json',{ fingerprint:'abc', state:'PROBATION', success_count:1, required_successes:3, last_success_at:'2026-01-04T00:00:01.000Z' }); assert.equal(check().decay,true); });

test('concurrent processes retain every penalty and unconfigured signals remain quarantined', async t => {
  fixture(t); policy(); state('parallel', 0.9);
  const { spawn } = await import('node:child_process');
  const modulePath = path.join(cwd, 'src/confidence/updateConfidence.ts');
  const loader = path.join(cwd, 'node_modules/tsx/dist/cjs/index.cjs');
  const code = `const {updateConfidence}=require(${JSON.stringify(modulePath)}); updateConfidence({fingerprint:'parallel',signal:'THROTTLE'});`;
  await Promise.all(Array.from({length: 5}, () => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['--require', loader, '-e', code], {cwd: process.cwd(), stdio:'pipe'});
    let error = ''; child.stderr.on('data', chunk => { error += chunk; }); child.on('error', reject); child.on('close', status => status === 0 ? resolve() : reject(new Error(error)));
  })));
  assert.equal(readConfidence('parallel').confidence, 0.4);
  fs.rmSync('config/confidence-policy.json');
  updateConfidence({fingerprint:'parallel',signal:'ROLLBACK'});
  policy();
  assert.equal(readConfidence('parallel').confidence, 0);
  assert.equal(readConfidence('parallel').reason, 'INVALID_EVENT_LEDGER');
});


test('high precision caps and penalties never round confidence upward', t => {
  fixture(t);
  const cap = 0.5000000000006;
  write('config/confidence-policy.json', { initial_score: cap, penalties: { THROTTLE: 0.0000000000002, ROLLBACK: 0, POLICY_DENIAL: 0 } });
  state('precise', 0.9);
  assert.equal(readConfidence('precise').confidence, cap);
  const after = updateConfidence({ fingerprint: 'precise', signal: 'THROTTLE' }).confidence;
  assert.equal(after, cap - 0.0000000000002);
  assert.ok(after <= cap);
  assert.equal(updateConfidence({ fingerprint: 'precise', signal: 'ROLLBACK' }).confidence, after);
});
