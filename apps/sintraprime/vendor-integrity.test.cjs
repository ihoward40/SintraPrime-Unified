// Ensure npm installs the same reviewed bytes that are visible in the repository.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { gunzipSync } = require('node:zlib');
const { createHash } = require('node:crypto');

test('vendored get-uri archive matches reviewed package files and lock integrity', () => {
  const root = __dirname;
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json')));
  const spec = manifest.overrides['pac-proxy-agent']['get-uri']['.'];
  assert.match(spec, /^file:vendor\/get-uri[^/]*\.tgz$/);
  const archive = fs.readFileSync(path.join(root, spec.slice(5)));
  const tar = gunzipSync(archive);
  const files = new Map();
  for (let offset = 0; offset + 512 <= tar.length;) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every(byte => byte === 0)) break;
    const field = (start, end) => header.subarray(start, end).toString('utf8').replace(/\0.*$/s, '');
    const prefix = field(345, 500);
    const name = (prefix ? prefix + '/' : '') + field(0, 100);
    const sizeText = field(124, 136).trim();
    assert.match(sizeText, /^[0-7]+$/);
    const size = parseInt(sizeText, 8);
    const type = field(156, 157);
    assert.ok(type === '' || type === '0' || type === '5', `Unexpected tar type ${type}: ${name}`);
    assert.ok(name.startsWith('package/') && !name.split('/').some(p => p === '..' || p === '.'), `Unexpected path: ${name}`);
    assert.ok(offset + 512 + size <= tar.length, 'Truncated archive');
    if (type !== '5') {
      const relative = name.slice('package/'.length);
      assert.ok(!files.has(relative), `Duplicate file: ${relative}`);
      files.set(relative, tar.subarray(offset + 512, offset + 512 + size));
    }
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  const source = path.join(root, 'vendor', 'get-uri');
  const expected = ['package.json', 'LICENSE', 'README.md'];
  function collect(dir, relative) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      assert.ok(!entry.isSymbolicLink(), 'Source must not contain symlinks');
      const next = relative + '/' + entry.name;
      if (entry.isDirectory()) collect(path.join(dir, entry.name), next);
      else { assert.ok(entry.isFile()); expected.push(next); }
    }
  }
  collect(path.join(source, 'dist'), 'dist');
  assert.deepEqual([...files.keys()].sort(), expected.sort());
  for (const [relative, bytes] of files) {
    assert.ok(fs.lstatSync(path.join(source, relative)).isFile(), 'Package sources must be regular files');
    assert.deepEqual(bytes, fs.readFileSync(path.join(source, relative)), `Source/archive drift: ${relative}`);
  }
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json')));
  const entries = Object.entries(lock.packages).filter(([name]) => /(^|\/)node_modules\/get-uri$/.test(name));
  assert.equal(entries.length, 1, 'Exactly one installed get-uri artifact expected');
  const entry = entries[0][1];
  assert.equal(entry.resolved.replace(/^file:/, ''), spec.slice(5));
  assert.equal(entry.integrity, 'sha512-' + createHash('sha512').update(archive).digest('base64'));
});
