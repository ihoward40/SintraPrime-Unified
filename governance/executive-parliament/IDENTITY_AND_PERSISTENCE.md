# Identity & Persistence Governance

Do not store the Principal's private identity profile in this public repository.

Runtime identity activation, if supported by the deployment environment, is limited to an approved local/private schema and must be verified before writing. OS groups, crypto state, permissions and inferred authority are not identity fields unless the runtime schema explicitly requires them.

Persistence validation requires actual same-session, new-session, restart, exact-name, absent-memory and conflict-handling tests. Same-session visibility is not proof of persistence.

No automatic memory injection, encryption initialization, key generation, permission expansion or confidential-data persistence without separate approval.

Historical validation receipts are immutable; corrections are supplemental.
