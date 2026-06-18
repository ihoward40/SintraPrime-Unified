# Audit Policy

Every certification decision must preserve:

- Exam identifier and SHA-256 hash
- Submission identifier and SHA-256 hash
- Answer-key identifier and SHA-256 hash
- Reviewer identity
- Review record and SHA-256 hash
- Raw category scores
- Hard-gate results
- Corrections and closure status
- Certification decision
- UTC timestamp
- Prior certification status
- New certification status

Audit records are append-only. A corrected submission creates a new version; it does not overwrite the original.
