// Exercise the consumers affected by the targeted dependency overrides.
// No external services, real credentials, or deployment commands are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const { test } = require('node:test');

const root = path.resolve(__dirname, '../../..');
const webRequire = createRequire(path.join(root, 'web/package.json'));

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return `http://127.0.0.1:${server.address().port}`;
}

async function close(server) {
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}

for (const crossRealm of [false, true]) {
  test(`redirect removes synthetic credential: ${crossRealm ? 'cross-realm' : 'same-realm'} array`, async () => {
    const axiosRequire = createRequire(webRequire.resolve('axios'));
    const follow = axiosRequire('follow-redirects');
    let received;
    const target = http.createServer((request, response) => {
      received = request.headers;
      response.end('ok');
    });
    const targetURL = await listen(target);
    const origin = http.createServer((_request, response) => {
      response.writeHead(302, { Location: `${targetURL}/destination` });
      response.end();
    });
    try {
      const originURL = await listen(origin);
      const sensitiveHeaders = crossRealm
        ? vm.runInNewContext("['x-api-key']")
        : ['x-api-key'];
      const status = await new Promise((resolve, reject) => {
        const request = follow.http.get(originURL, {
          headers: { 'X-API-Key': 'synthetic-test-value', 'X-Harmless': 'retained' },
          sensitiveHeaders,
        }, (response) => {
          response.resume();
          response.on('end', () => resolve(response.statusCode));
          response.on('error', reject);
        });
        request.on('error', reject);
        request.setTimeout(5000, () => request.destroy(new Error('loopback test timeout')));
      });
      assert.equal(status, 200);
      assert.ok(received, 'redirect target must actually receive the request');
      assert.equal(received['x-api-key'], undefined);
      assert.equal(received['x-harmless'], 'retained');
    } finally {
      await close(origin);
      await close(target);
    }
  });
}

test('TypeScript ESLint resolves a real typed project after the minimatch override', () => {
  const parser = webRequire('@typescript-eslint/parser');
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'sp-dependency-ts-'));
  try {
    fs.mkdirSync(path.join(temp, 'src'));
    const code = 'export const count: number = 1;';
    const filename = path.join(temp, 'src/example.ts');
    fs.writeFileSync(filename, code);
    fs.writeFileSync(path.join(temp, 'tsconfig.json'), JSON.stringify({
      compilerOptions: { strict: true, target: 'ES2020' },
      include: ['src/**/*.ts'],
    }));
    const result = parser.parseForESLint(code, {
      filePath: filename,
      project: ['./tsconfig.json'],
      tsconfigRootDir: temp,
      sourceType: 'module',
    });
    assert.ok(result.services.program.getSourceFile(filename));
    assert.equal(result.ast.body[0].type, 'ExportNamedDeclaration');
    const parserRequire = createRequire(webRequire.resolve('@typescript-eslint/parser'));
    const estreeRequire = createRequire(parserRequire.resolve('@typescript-eslint/typescript-estree'));
    const { minimatch } = estreeRequire('minimatch');
    assert.equal(minimatch('src/example.ts', 'src/**/*.ts'), true);
    assert.equal(minimatch('assets/example.png', 'src/**/*.ts'), false);
  } finally {
    parser.clearCaches();
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

test('Tailwind and PostCSS still generate utilities using the patched selector parser', async () => {
  const postcss = webRequire('postcss');
  const tailwind = webRequire('tailwindcss');
  const result = await postcss([tailwind({
    content: [{ raw: '<div class="p-4 hover:bg-blue-500">test</div>' }],
    corePlugins: { preflight: false },
  })]).process('@tailwind utilities;', { from: undefined });
  assert.match(result.css, /\.p-4\s*\{\s*padding:\s*1rem/);
  assert.match(result.css, /:hover/);
  assert.match(result.css, /background-color:/);
});
