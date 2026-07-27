# Appendix D — Knowledge Provenance Specification (Normative)

## Derived From

BKGC Article IX.

## Provenance Fields

Every evidence item SHOULD record:

- Evidence ID
- Source ID
- Collection date
- Collection method
- Hash (when applicable)
- Version
- Chain of custody
- Validation history
- Related claims
- Jurisdiction
- Classification
- Integrity status
- Archive status

## Chain of Custody

For formal or legal evidence, the chain of custody MUST record each transfer of possession, including date, actor, and purpose.

## Downstream Use

BGS `METADATA/provenance_schema.md` defines the operational schema. BRA implements provenance tracking in the Provenance Engine.
