# GOD-2A Effect Classification Matrix

| Effect class | Definition | Approval | Rollback | GOD-2A treatment |
|---|---|---|---|---|
| E0 | Read-only external observation with no remote mutation | Required for future admission | Not applicable; prove no mutation | Shadow-only candidates |
| E1 | Draft creation that is not sent, submitted, posted, published, or filed | Required | Delete/discard local draft where applicable | Shadow-only candidates |
| E2 | Narrow reversible low-risk mutation with a demonstrated inverse | Required | Mandatory pre-state, post-state, inverse, and rollback window | Closed |
| E3 | Irreversible external mutation | Required plus later mission | Must not be admitted in GOD-2 | Closed |
| E4 | Financial execution or money movement | Required plus later mission | Must not be admitted in GOD-2 | Closed |
| E5 | Legal or regulatory submission, filing, signature, attestation, or service | Required plus later mission | Must not be admitted in GOD-2 | Closed |
| E6 | Credential, authentication, access, or secret mutation | Required plus later mission | Must not be admitted in GOD-2 | Closed |
| E7 | Deployment or production infrastructure mutation | Required plus later mission | Must not be admitted in GOD-2 | Closed |
| E8 | Security privilege mutation or destructive/security-critical action | Required plus later mission | Must not be admitted in GOD-2 | Closed |

The static classification is a ceiling. A model, provider, swarm consensus, memory record, or tool self-description may increase caution but cannot lower the class. Resource scope, tenant scope, environment, mission authority, agent authority, preconditions, and approval must all pass independently.
