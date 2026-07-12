# Generated Artifact Policy

Synthetic fixtures may be tracked when they contain no real client, court, payment, or webhook data.

Generated local client artifacts and production court artifacts must remain out of Git unless they are explicitly redacted, synthetic, and approved for fixture use.

The monetization start-case workflow writes transient state under `.case_runs/`; that directory is runtime state and must not be committed. Ledger provenance records under `ledger/logs/` are evidence records and must not be ignored.
