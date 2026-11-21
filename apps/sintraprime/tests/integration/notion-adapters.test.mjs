import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const tempBase = os.tmpdir();
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { notionLiveGet, notionLiveWhoAmI } = require('../../src/adapters/notionLiveRead.ts');
const { authorizeApprovedNotionWrites, getSuccessfulNotionReplay, notionLivePatchWithIdempotency } = require('../../src/adapters/notionLiveWrite.ts');
const { executePlan } = require('../../src/executor/executePlan.ts');
const { checkPolicyWithMeta } = require('../../src/policy/checkPolicy.ts');
const { computePlanHash } = require('../../src/utils/planHash.ts');
let savedEnv, savedFetch, savedCwd, tmp, calls;
beforeEach(() => {
  savedEnv = { ...process.env }; savedFetch = globalThis.fetch; savedCwd = process.cwd();
  for (const key of Object.keys(process.env)) delete process.env[key];
  Object.assign(process.env, { NOTION_TOKEN: 'private-test-token', AUTONOMY_MODE: 'OFF' });
  tmp = fs.mkdtempSync(path.join(tempBase, 'notion-adapter-')); process.chdir(tmp); calls = [];
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return new Response('{"ok":true}', { status: 200 }); };
});
afterEach(() => {
  process.chdir(savedCwd); globalThis.fetch = savedFetch;
  for (const key of Object.keys(process.env)) delete process.env[key];
  Object.assign(process.env, savedEnv);
  fs.rmSync(tmp, { recursive: true, force: true });
});
function plan(key = 'key') {
  const prestate = { object: 'page', properties: { Status: 'old' } };
  return { kind: 'ExecutionPlan', execution_id: 'execution', threadId: 'thread', dry_run: false, goal: 'Update page',
    agent_versions: { planner: 'test', validator: 'test' }, required_secrets: [],
    steps: [{ step_id: 'write', action: 'notion.live.write', adapter: 'NotionAdapter', method: 'PATCH', read_only: false,
      approval_scoped: true, approved_at: '2000-01-01', url: 'https://api.notion.com/v1/pages/abc', notion_path: '/v1/pages/abc',
      properties: { Status: { rich_text: [{ text: { content: 'new' } }] } }, prestate, prestate_fingerprint: computePlanHash(prestate),
      guards: [{ path: 'properties.Status', op: '==', value: 'old' }], expects: { http_status: [200] }, idempotency_key: key }]
  };
}
function approved(p) {
  const result = checkPolicyWithMeta(p, process.env, new Date(), { execution_id: p.execution_id, approved_execution_id: p.execution_id });
  assert.equal(result.allowed, true);
  return authorizeApprovedNotionWrites(p, result, p.execution_id);
}
const runApproved = p => executePlan(p, { notionWriteApproval: approved(p) });
const patch = (p, cap = approved(p)) => notionLivePatchWithIdempotency(p.steps[0].notion_path, { properties: p.steps[0].properties }, p.steps[0].idempotency_key, cap, p.execution_id, p.steps[0].step_id);

test('read is bounded, uses established headers, and redacts configured secrets anywhere', async () => {
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return new Response(JSON.stringify({ code: 'object_not_found', message: 'private-test-token', 'private-test-token': 'value', authorization: 'different-secret' }), { status: 404 }); };
  const result = await notionLiveGet('/v1/pages/abc');
  assert.equal(result.http_status, 404); assert.equal(result.redacted.code, 'object_not_found');
  assert.equal(JSON.stringify(result).includes('private-test-token'), false); assert.equal(JSON.stringify(result).includes('different-secret'), false);
  const { url, options } = calls[0]; assert.equal(url, 'https://api.notion.com/v1/pages/abc');
  assert.equal(options.method, 'GET'); assert.equal(options.redirect, 'error'); assert.ok(options.signal instanceof AbortSignal);
  assert.equal(options.headers.Authorization, 'Bearer private-test-token'); assert.equal(options.headers['Notion-Version'], '2022-06-28');
  assert.equal((await notionLiveWhoAmI()).ok, false);
});

test('missing token, unsafe origin/path, and transport errors fail closed without token disclosure', async () => {
  for (const p of ['https://evil.test/v1/pages/abc', '/v1/pages/../users/me', '/v1/pages/%2e%2e', '/v1/pages/abc?x=1', '/v1/pages/abc#x', '/v1/pages/abc/']) await assert.rejects(notionLiveGet(p));
  process.env.NOTION_API_BASE = 'https://evil.test'; await assert.rejects(notionLiveGet('/v1/pages/abc')); delete process.env.NOTION_API_BASE;
  delete process.env.NOTION_TOKEN; await assert.rejects(notionLiveGet('/v1/pages/abc')); assert.equal(calls.length, 0);
  process.env.NOTION_TOKEN = 'private-test-token'; globalThis.fetch = async () => { throw new Error('private-test-token'); };
  await assert.rejects(notionLiveGet('/v1/pages/abc'), e => e.message === 'Notion read request failed');
  globalThis.fetch = async () => ({ text: async () => { throw new Error('private-test-token'); } });
  await assert.rejects(notionLiveGet('/v1/pages/abc'), e => !e.message.includes('private-test-token'));
});

test('real policy requires approval; denied policy and forged serialized contexts cannot write', async () => {
  const p = plan(); const policy = checkPolicyWithMeta(p, process.env, new Date());
  assert.equal(policy.requireApproval, true);
  assert.throws(() => authorizeApprovedNotionWrites(p, policy, p.execution_id), /approval/);
  assert.throws(() => authorizeApprovedNotionWrites(p, { allowed: true }, 'other'), /approval/);
  assert.equal((await executePlan(p)).status, 'failed');
  assert.equal((await executePlan(p, { notionWriteApproval: { execution_id: p.execution_id, approved_at: 'now' } })).status, 'failed');
  process.env.ALLOWED_DOMAINS = 'example.com';
  const denied = checkPolicyWithMeta(p, process.env, new Date(), { execution_id: p.execution_id, approved_execution_id: p.execution_id });
  assert.equal(denied.allowed, false); assert.throws(() => authorizeApprovedNotionWrites(p, denied, p.execution_id));
  assert.throws(() => authorizeApprovedNotionWrites(p, { allowed: true }, p.execution_id), /policy denied/);
  assert.equal(calls.length, 0);
});

test('approved executor sends exactly once and replays only bound success', async () => {
  const p = plan();
  assert.equal((await runApproved(p)).status, 'success'); assert.equal((await runApproved(p)).status, 'success');
  assert.equal(calls.length, 1); assert.equal(calls[0].options.method, 'PATCH');
  assert.deepEqual(JSON.parse(calls[0].options.body), { properties: p.steps[0].properties });
  assert.equal(calls[0].options.headers['Idempotency-Key'], undefined);
  assert.equal(getSuccessfulNotionReplay(p.execution_id, p.steps[0]).http_status, 200);
});

test('capability rejects altered execution, body, key, step, and credentials before dispatch', async () => {
  const p = plan(), cap = approved(p);
  for (const mutate of [q => q.execution_id = 'other', q => q.steps[0].step_id = 'other', q => q.steps[0].properties = {}, q => q.steps[0].idempotency_key = 'other']) {
    const q = structuredClone(p); mutate(q); await assert.rejects(patch(q, cap), /approval/);
  }
  process.env.NOTION_TOKEN = 'another-token'; await assert.rejects(patch(p, cap), /approval/); assert.equal(calls.length, 0);
});

test('existing success is bound to body, destination, execution, credential scope, and API version', async () => {
  const p = plan(); await patch(p);
  for (const mutate of [q => q.execution_id = 'other', q => q.steps[0].properties = {}, q => { q.steps[0].notion_path = '/v1/pages/other'; q.steps[0].url = 'https://api.notion.com/v1/pages/other'; }]) {
    const q = structuredClone(p); mutate(q); await assert.rejects(patch(q), /mismatch/); assert.throws(() => getSuccessfulNotionReplay(q.execution_id, q.steps[0]), /mismatch/);
  }
  process.env.NOTION_TOKEN = 'other-token'; await assert.rejects(patch(p), /mismatch/); assert.throws(() => getSuccessfulNotionReplay(p.execution_id, p.steps[0]), /mismatch/);
  process.env.NOTION_TOKEN = 'private-test-token'; process.env.NOTION_API_VERSION = '2025-09-03'; await assert.rejects(patch(p), /mismatch/);
  assert.equal(calls.length, 1);
});

test('failed and unknown outcomes never automatically resend or become replay successes', async () => {
  for (const status of [302, 400, 500]) {
    const p = plan('failed-' + status);
    globalThis.fetch = async () => { calls.push(status); return new Response('{}', { status }); };
    assert.equal((await patch(p)).http_status, status);
    await assert.rejects(patch(p), /reconciliation/); assert.throws(() => getSuccessfulNotionReplay(p.execution_id, p.steps[0]), /reconciliation/);
  }
  const p = plan('unknown'); globalThis.fetch = async () => { calls.push('unknown'); throw new Error('private-test-token'); };
  await assert.rejects(patch(p), /reconciliation/); await assert.rejects(patch(p), /reconciliation/);
  assert.equal(calls.length, 4);
});

test('atomic reservation prevents concurrent duplicate dispatch', async () => {
  const p = plan(), cap = approved(p); let release;
  globalThis.fetch = async () => { calls.push('pending'); return new Promise(resolve => { release = resolve; }); };
  const first = patch(p, cap);
  await assert.rejects(patch(p, cap), /reconciliation/); assert.equal(calls.length, 1);
  release(new Response('{}', { status: 200 })); await first;
  assert.equal((await patch(p, cap)).http_status, 200); assert.equal(calls.length, 1);
});

test('malformed records and path traversal keys fail closed', async () => {
  const p = plan(); await patch(p); const file = fs.readdirSync('runs/notion-idempotency')[0];
  fs.writeFileSync(path.join('runs/notion-idempotency', file), '{');
  await assert.rejects(patch(p), /reconciliation/);
  p.steps[0].idempotency_key = '../../outside'; assert.throws(() => approved(p), /idempotency key/);
  assert.equal(calls.length, 1);
});

test('invalid adapter/method/flags, destination, properties, prestate, and guards cannot gain authority', async () => {
  const mutations = [s => s.adapter = 'WebhookAdapter', s => s.method = 'GET', s => s.read_only = true, s => s.approval_scoped = false,
    s => s.url = 'https://evil.test/v1/pages/abc', s => s.url = 'https://api.notion.com:443/v1/pages/abc', s => s.url += '?x=1',
    s => s.notion_path = '/v1/pages/other', s => s.notion_path_prestate = '/v1/pages/other', s => s.properties = null,
    s => s.properties = [], s => s.prestate = null, s => s.prestate_fingerprint = 'forged', s => s.guards[0].value = 'different'];
  for (const mutate of mutations) { const p = plan(); mutate(p.steps[0]); assert.throws(() => authorizeApprovedNotionWrites(p, { allowed: true }, p.execution_id)); }
  assert.equal(calls.length, 0);
});

test('executor preserves dry-run, live read and mock Notion routes', async () => {
  const p = plan(); p.dry_run = true; assert.equal((await executePlan(p)).status, 'success'); assert.equal(calls.length, 0);
  const read = plan(); Object.assign(read.steps[0], { action: 'notion.live.read', method: 'GET', read_only: true });
  assert.equal((await executePlan(read)).status, 'success'); assert.equal(calls[0].options.method, 'GET');
  const mock = plan(); Object.assign(mock.steps[0], { action: 'notion.write.page_property', url: 'http://127.0.0.1/notion/page/abc', payload: { properties: { x: 1 } } });
  assert.equal((await executePlan(mock)).status, 'success'); assert.equal(calls[1].url, 'http://127.0.0.1/notion/page/abc');
});

test('executor evidence redacts configured token in properties and API bodies', async () => {
  const p = plan(); p.steps[0].properties = { text: 'private-test-token' };
  globalThis.fetch = async () => new Response('{"message":"private-test-token"}', { status: 200 });
  const log = await runApproved(p); assert.equal(log.status, 'success'); assert.equal(JSON.stringify(log).includes('private-test-token'), false);
  const evidence = fs.readFileSync('runs/notion-live-write/execution.write.json', 'utf8'); assert.equal(evidence.includes('private-test-token'), false);
});

test('unbound legacy success requires reconciliation without replay or dispatch', async () => {
  const p = plan(); fs.mkdirSync('runs/idempotency', { recursive: true });
  fs.writeFileSync('runs/idempotency/key.json', JSON.stringify({ status: 'executed', action: 'notion.live.write', http_status: 200, response: { forged: true } }));
  assert.throws(() => getSuccessfulNotionReplay(p.execution_id, p.steps[0]), /Legacy.*reconciliation/);
  await assert.rejects(patch(p), /Legacy.*reconciliation/);
  const log = await runApproved(p); assert.equal(log.status, 'failed');
  assert.match(log.steps[0].error, /Legacy.*reconciliation/); assert.equal(calls.length, 0);
});
test('successful reads reject malformed and non-object payloads without disclosing tokens', async () => {
  for (const body of ['{', 'null', '[]', '42', '"private-test-token"']) {
    globalThis.fetch = async () => new Response(body, { status: 200 });
    await assert.rejects(notionLiveGet('/v1/pages/abc'), e => !e.message.includes('private-test-token'));
  }
});
