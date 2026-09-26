# A2A Filesystem Locking Assessment

## Tested result

C7 uses `fcntl.flock` on a companion `.lock` file, fsyncs each JSONL append, and assigns monotonic sequence numbers while holding the lock. The local Linux filesystem test produced 40 concurrent audit writes with sequence values 1–40 and passed strict integrity validation.

**Local single-host result:** PASS.

## Safe deployment boundary

The locking design is appropriate for:

- local Linux disk
- a properly mounted Docker volume used by processes on one host
- one designated writer host with local process concurrency

The design is **not certified** for:

- NFS
- SMB
- network-mounted shared filesystems
- multi-host concurrent writers
- storage systems with nonstandard or advisory-lock semantics

`fcntl` locking is host/filesystem dependent. A shared multi-host deployment should move audit, approval, and outbox state to a transactional database or a single-writer service rather than assuming JSONL locks provide distributed coordination.

## Evidence

- C7 concurrent-writer test: 40 records, no interleaving/corruption.
- Sequence integrity: `1..40`.
- Approval and outbox integrity checks passed.
- Final partial-line recovery remains limited to the final line; strict integrity checks reject malformed historical lines and sequence gaps.

## Production requirement

Before production certification, document the actual mount type and prove concurrent behavior on that topology. If the deployment spans hosts or uses shared network storage, do not enable external actions until the stores are migrated to a distributed-safe persistence layer.
