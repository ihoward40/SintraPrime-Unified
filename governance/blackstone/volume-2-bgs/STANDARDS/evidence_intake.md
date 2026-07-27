# Standard 1 — Evidence Intake

## Purpose

Define the minimum requirements for evidence entering the Blackstone ecosystem.

## Derived From

BGS 1, BKGC Article VII § 7.1.

## Requirements

1. Every intake MUST generate a unique Evidence ID (EID).
2. Intake MUST capture source identity, collection timestamp, and collector.
3. Evidence MUST be classified by type and source category before operational use.
4. Intake SHOULD calculate an initial metadata completeness score.
5. Evidence failing intake requirements MUST be rejected or quarantined.

## Metadata Schema

See `METADATA/evidence_schema.md`.

## Failure Mode

- Missing provenance → quarantine
- Unidentifiable source → reject
- Duplicate EID → reject and alert
