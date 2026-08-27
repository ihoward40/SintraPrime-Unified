# Freeze-and-stop procedure

## Preconditions

A future freeze is valid only after separately authorized implementation, account connection, live certification, independent review, and terminal exact-head CI. This design package itself cannot be certified as a connector.

## Freeze record

Record:

- exact commit and tree;
- parent commit;
- adapter and authority-contract hashes;
- exact OAuth scope and account-binding digest;
- evidence-chain root and schema hash;
- certification workflow names, run IDs, conclusions, and head SHA;
- approved host/path/method/field boundary;
- negative-test matrix and results;
- residual blockers and cleanup state;
- confirmation that Gate 4D-B remains frozen at `457f69be6714797f2332e20dfc6a245c817099e5`.

## Post-freeze verification

1. Recompute every recorded hash.
2. Confirm no tracked or untracked secret-bearing artifact.
3. Confirm credential leases expired and test tokens/accounts were revoked or retained only under explicit Principal policy.
4. Confirm no pending provider attempt or unreconciled timeout.
5. Confirm all exact-head workflows are terminal `SUCCESS`.
6. Confirm PR state and that merge remains separately authorized.

## Non-expansion rules

Certification, if later granted, applies only to:

```text
adapter = provider.google-drive-metadata-read-v1
scope   = drive.metadata.readonly
method  = GET
host    = www.googleapis.com
paths   = /drive/v3/files and /drive/v3/files/{fileId}
fields  = frozen metadata allowlist
account = exact approved account-binding digest
```

It does not authorize Drive content, export/download, Docs/Sheets/Slides bodies, writes, permissions, comments, broader accounts, domain-wide delegation, GitHub expansion, merge, release, or deployment.

## Stop conditions

Immediately stop and classify `FAIL` or `INCOMPLETE` on candidate/head drift, scope drift, account drift, token leakage, content bytes, write attempt, destination drift, evidence tampering, unresolved timeout, missing exact-head workflow, or any Gate 4D-B modification.

After a valid freeze, stop for Principal review. No capability automatically advances to another ladder.
