# get-uri local patch provenance

Upstream: get-uri 6.0.5, MIT licensed, from https://github.com/TooTallNate/proxy-agents/tree/main/packages/get-uri . The preserved LICENSE identifies the upstream copyright holder. The distributed CommonJS JavaScript is kept reviewable under get-uri/dist; this is the upstream npm distribution, not a claim to reproduce its TypeScript build.

Registry artifact: https://registry.npmjs.org/get-uri/-/get-uri-6.0.5.tgz

Upstream integrity: `sha512-b1O07XYq8eRuVzBNgJLstU6FYc1tS6wnMtF1I1D9lE8LxZSOGZ7LhxN54yPP6mGw5f2CkXY2BQUL9Fx41qvcIg==` (recorded by PR 401's lockfile).

Deliberate local changes:
- dist/file.js retains FileHandle ownership via createReadStream and closes on cache/setup failures.
- Its stale source map and sourceMappingURL are removed rather than misrepresenting generated locations.
- package.json identifies 6.0.5-sintraprime.1 and pins basic-ftp exactly 6.2.6. Other protocol implementations remain unchanged.

The adjacent get-uri-6.0.5-sintraprime.1.tgz is the app's scoped override. It installs with npm ci --ignore-scripts; no lifecycle patch or runtime monkeypatch is used.

Reproduce from the app directory with `npm pack ./vendor/get-uri --pack-destination ./vendor --ignore-scripts`. Check `node --test vendor-integrity.test.cjs`, then regenerate the app lockfile with npm 9 and validate npm 9 and 11 clean installs. The integrity test checks exact source/package equality and lock SHA-512, not byte determinism across npm pack versions. Commit source, tar and lockfile together. vendor/.gitattributes preserves package source bytes across operating systems.
