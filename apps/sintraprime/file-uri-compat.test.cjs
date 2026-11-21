const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { createRequire } = require('node:module');
const { mkdtemp, writeFile, rm } = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const getUri = createRequire(require.resolve('pac-proxy-agent'))('get-uri').getUri;
test('file stream retains its handle through garbage collection', () => {
 const child = spawnSync(process.execPath, ['--expose-gc', '-e', `
 const { createRequire } = require('node:module');
 const { pathToFileURL } = require('node:url');
 const fs = require('node:fs'); const os = require('node:os'); const path = require('node:path');
 (async () => { const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'uri-gc-'));
 try { const file = path.join(dir, 'file'); fs.writeFileSync(file, 'expected');
 const get = createRequire(require.resolve('pac-proxy-agent'))('get-uri').getUri;
 const stream = await get(pathToFileURL(file).href);
 for (let i = 0; i < 20; i++) { global.gc(); await new Promise(r => setImmediate(r)); }
 let data = ''; for await (const chunk of stream) data += chunk;
 if (data !== 'expected') throw Error('unexpected file data');
 for (let i = 0; i < 10; i++) { global.gc(); await new Promise(r => setImmediate(r)); }
 } finally { fs.rmSync(dir, { recursive: true, force: true }); }
 })().catch(e => { console.error(e); process.exitCode = 1; });
 `], { encoding: 'utf8', timeout: 15000 });
 assert.equal(child.status, 0, child.stderr || child.error?.message);
 assert.doesNotMatch(child.stderr, /Closing file descriptor|DEP0137/);
});
test('file cache, missing files and explicit stream closure', async () => {
 const dir = await mkdtemp(path.join(os.tmpdir(), 'uri-test-'));
 try { const file = path.join(dir, 'file'); await writeFile(file, 'first');
 const uri = pathToFileURL(file).href; const stream = await getUri(uri);
 let data = ''; for await (const chunk of stream) data += chunk;
 assert.equal(data, 'first');
 await assert.rejects(getUri(uri, { cache: stream }), { code: 'ENOTMODIFIED' });
 await assert.rejects(getUri(pathToFileURL(path.join(dir, 'missing')).href), { code: 'ENOTFOUND' });
 const early = await getUri(uri); early.destroy(); await new Promise(resolve => early.once('close', resolve));
 } finally { await rm(dir, { recursive: true, force: true }); }
});


test('PAC file consumer loads, caches and reloads changed files', async () => {
 const { PacProxyAgent } = require('pac-proxy-agent');
 const { utimes } = require('node:fs/promises');
 const dir = await mkdtemp(path.join(os.tmpdir(), 'pac-file-'));
 const file = path.join(dir, 'proxy.pac');
 try {
  await writeFile(file, 'function FindProxyForURL() { return "DIRECT"; }');
  const agent = new PacProxyAgent(`pac+${pathToFileURL(file).href}`);
  assert.match(await agent.loadPacFile(), /DIRECT/);
  await assert.rejects(agent.loadPacFile(), { code: 'ENOTMODIFIED' });
  await writeFile(file, 'function FindProxyForURL() { return "PROXY localhost:1"; }');
  const later = new Date(Date.now() + 5000); await utimes(file, later, later);
  assert.match(await agent.loadPacFile(), /PROXY/);
  agent.destroy();
 } finally { await rm(dir, { recursive: true, force: true }); }
});

test('stat and stream construction failures close the opened handle', async () => {
 const fs = require('node:fs'); const original = fs.promises.open;
 try {
  for (const failure of ['stat', 'stream']) {
   let closed = false;
   fs.promises.open = async () => ({
    async stat() { if (failure === 'stat') throw Error('injected stat'); return {}; },
    createReadStream() { throw Error('injected stream'); },
    async close() { closed = true; }
   });
   await assert.rejects(getUri(pathToFileURL(path.resolve('test')).href), new RegExp(`injected ${failure}`));
   assert.equal(closed, true);
  }
 } finally { fs.promises.open = original; }
});

test('autoClose false permits explicit caller closure', async () => {
 const dir = await mkdtemp(path.join(os.tmpdir(), 'uri-close-'));
 try {
  const file = path.join(dir, 'file'); await writeFile(file, 'text');
  const fs = require('node:fs'); const original = fs.promises.open;
  let handle, stream;
  try {
   fs.promises.open = async (...args) => { handle = await original(...args); return handle; };
   stream = await getUri(pathToFileURL(file).href, { autoClose: false });
  } finally { fs.promises.open = original; }
  stream.resume(); await new Promise((resolve, reject) => { stream.once('end', resolve); stream.once('error', reject); });
  assert.equal(stream.closed, false);
  assert.ok(handle.fd >= 0, 'Caller still owns the open handle before explicit close');
  await new Promise((resolve, reject) => { stream.once('close', resolve); stream.once('error', reject); stream.close(); });
  assert.equal(stream.closed, true);
  assert.equal(handle.fd, -1, 'Explicit stream closure closes its owning FileHandle');
 } finally { await rm(dir, { recursive: true, force: true }); }
});
