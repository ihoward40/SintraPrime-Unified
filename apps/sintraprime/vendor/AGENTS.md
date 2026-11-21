# Vendored PAC URI dependency

## Purpose

Own the reviewed CommonJS get-uri distribution used by the nested application's PAC consumer.

## Ownership

- `get-uri/` contains the auditable package source/distribution and upstream license/provenance.
- The adjacent versioned tarball is the locked install artifact; source and package contents must agree.

## Local Contracts

- Preserve Node >=20 CommonJS consumers and patched basic-ftp 6.2.6; do not widen the override to unrelated consumers.
- File streams retain one FileHandle owner. Close handles on cache hits and failures; preserve explicit caller-managed autoClose:false behavior.
- No lifecycle script or runtime monkeypatch may be required for the correction. Clean `npm ci --ignore-scripts` must install the reviewed artifact.
- Preserve upstream licensing and record origin, upstream integrity, local changes and package reproduction instructions.

## Work Guidance

- Keep the patch limited to descriptor ownership and error cleanup; do not silently change other protocol behavior.
- Update source, packaged artifact, manifest and lockfile together. Verify package/source equivalence before publishing.

## Verification

- `node --test pac-compat.test.cjs file-uri-compat.test.cjs vendor-integrity.test.cjs` exercises the installed PAC dependency, including a child process with exposed garbage collection.
- Run clean locked installation and compatibility tests on minimum Node 20 and Node 24. Preserve zero skips and the patched FTP resolution.

## Child DOX Index

None.
