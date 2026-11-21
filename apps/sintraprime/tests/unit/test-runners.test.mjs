import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

for (const runner of ['run-unit-tests.mjs', 'run-integration-tests.mjs']) {
  test(`${runner} rejects empty suites and propagates failing tests`, () => {
    const dir = mkdtempSync(join(tmpdir(), 'test-runner-'));
    try {
      const script = resolve('scripts', runner);
      const invoke = () => spawnSync(process.execPath, [script, dir], { encoding: 'utf8' });
      const missing = spawnSync(process.execPath, [script, join(dir, 'missing')], { encoding: 'utf8' });
      assert.notEqual(missing.status, 0);
      assert.match(missing.stderr, /cannot discover tests/i);
      const empty = invoke();
      assert.notEqual(empty.status, 0);
      assert.match(empty.stderr, /no test files/i);
      writeFileSync(join(dir, 'failure.test.mjs'), "import { test } from 'node:test'; test('deliberate failure', () => { throw new Error('fixture failure'); });\n");
      const failed = invoke();
      assert.notEqual(failed.status, 0);
      assert.match(failed.stdout + failed.stderr, /fixture failure/);
      writeFileSync(join(dir, 'failure.test.mjs'), "import { test } from 'node:test'; test('fixture passes', () => {});\n");
      assert.equal(invoke().status, 0);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
}
