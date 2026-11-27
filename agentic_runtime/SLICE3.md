# Slice 3 — Runtime Certification + Concrete Rollback

Controlling rule: **agents may become more capable without becoming more authoritative.**

## Certification gates

1. Checkpoint records the exact repository ref and changed-file manifest.
2. Rollback requires existing authorization and verifies the restored ref.
3. Consolidated execution receipts are canonical JSON hashed with SHA-256 and may bind the existing execution-ledger hash.
4. Focused `agentic_runtime/tests` must pass.
5. The repository's canonical `scripts/certify.py` remains the broader regression authority.
6. A model is not VERIFIED from a model card, name, configured context, or marketing claim. Promotion requires runtime-observed context evidence plus benchmark evidence meeting the configured floor.

## Explicit non-authority

This slice does not grant shell, Git push/merge, deployment, payment, publication, destructive filesystem, or cloud-media authority. Concrete repository mutation remains behind injected executors and approval.
