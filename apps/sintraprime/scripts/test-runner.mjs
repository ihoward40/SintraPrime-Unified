import { readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';
export function runSuite(defaultDirectory) {
  const directory = resolve(process.argv[2] ?? defaultDirectory);
  const files = [];
  function discover(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) discover(path);
      else if (entry.isFile() && /\.test\.[cm]?js$/.test(entry.name)) files.push(path);
    }
  }
  try { discover(directory); } catch (error) {
    console.error(`Cannot discover tests in ${directory}: ${error.message}`);
    process.exitCode = 1; return;
  }
  if (!files.length) { console.error(`No test files found in ${directory}`); process.exitCode = 1; return; }
  files.sort();
  const env = { ...process.env };
  delete env.NODE_TEST_CONTEXT;
  // The CommonJS hook supports Node 20.0 without the later module registration API.
  const result = spawnSync(process.execPath, ['--test', '--require', 'tsx/cjs', ...files], { stdio: 'inherit', env });
  if (result.error) console.error(result.error);
  process.exitCode = result.status ?? 1;
}
