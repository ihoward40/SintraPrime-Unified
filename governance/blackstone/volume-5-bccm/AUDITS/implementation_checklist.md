# Audit Checklist — Implementation

## Purpose

Standardized checklist for auditing a Blackstone-conforming implementation.

## Derived From

BCCM § 4.

## Checklist

### Evidence Engine

- [ ] Evidence intake accepts required metadata.
- [ ] Provenance records are created.
- [ ] Integrity hashes are computed for fixed-format evidence.
- [ ] AI-generated evidence is flagged and requires verification.
- [ ] Duplicate EIDs are rejected.

### Authority Engine

- [ ] Authorities are registered with type and jurisdiction.
- [ ] Temporal validity is tracked.
- [ ] Stale authority is flagged.
- [ ] Jurisdiction mismatch is detected.

### Reasoning Engine

- [ ] Reasoning chain is preserved stage by stage.
- [ ] Alternatives are recorded.
- [ ] Assumptions are declared.
- [ ] Confidence is derived from evidence.

### Decision Engine

- [ ] Decision records are append-only.
- [ ] Supersession links are preserved.
- [ ] Reviewer identity is recorded.

### Audit Engine

- [ ] Access and modifications are logged.
- [ ] Audit log is tamper-evident.
- [ ] Compliance scorecards can be generated.

### Security

- [ ] Least-privilege access is enforced.
- [ ] Confidential information is protected.
- [ ] Logs include access events.

## Audit Output

The auditor MUST produce:

- Completed checklist
- Findings with severity
- Remediation plan
- Certification recommendation
