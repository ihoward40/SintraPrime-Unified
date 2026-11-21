// Guard the CommonJS PAC consumer boundary and patched FTP resolution.
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { createRequire } = require('node:module');
const { PacProxyAgent } = require('pac-proxy-agent');
const pacRequire = createRequire(require.resolve('pac-proxy-agent'));
const uriRequire = createRequire(pacRequire.resolve('get-uri'));

test('PAC URI consumer retains the patched FTP dependency', () => {
  assert.equal(uriRequire('basic-ftp/package.json').version, '6.2.6');
});

test('CommonJS PAC consumer fetches an HTTP PAC and routes an HTTP request', async () => {
  const server = http.createServer((req, res) => {
    res.end(req.url === '/proxy.pac'
      ? 'function FindProxyForURL() { return "DIRECT"; }'
      : 'PAC-COMPAT-PASS');
  });
  let agent;
  try {
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
    const base = `http://127.0.0.1:${server.address().port}`;
    agent = new PacProxyAgent(`pac+${base}/proxy.pac`);
    const result = await new Promise((resolve, reject) => {
      const req = http.get(`${base}/payload`, { agent }, async res => {
        try {
          let body = '';
          for await (const chunk of res) body += chunk;
          resolve({ status: res.statusCode, body });
        } catch (error) { reject(error); }
      });
      req.on('error', reject);
      req.setTimeout(5000, () => req.destroy(new Error('PAC request timed out')));
    });
    assert.deepEqual(result, { status: 200, body: 'PAC-COMPAT-PASS' });
  } finally {
    agent?.destroy();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});
