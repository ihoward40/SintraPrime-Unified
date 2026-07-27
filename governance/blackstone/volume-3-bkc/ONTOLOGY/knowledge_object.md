# Ontology — Knowledge Object

## Definition

A Knowledge Object is any entity in the Blackstone ecosystem that carries meaning and can be governed, versioned, reviewed, and archived.

## Subtypes

- Claim
- Evidence
- Authority
- Source
- Decision
- Objection
- Counter-Evidence
- Interpretation
- Assumption
- Risk

## Invariants

1. Every Knowledge Object MUST have a unique identifier.
2. Every Knowledge Object MUST have a version.
3. Every Knowledge Object MUST have a lifecycle stage.
4. Every Knowledge Object MUST have a status.
5. Every Knowledge Object SHOULD have an audit trail.

## Relationships

| Subject | Predicate | Object |
|---------|-----------|--------|
| Knowledge Object | hasVersion | Version |
| Knowledge Object | hasStage | Lifecycle Stage |
| Knowledge Object | hasStatus | Status |
| Knowledge Object | hasProvenance | Provenance Record |
| Knowledge Object | reviewedBy | Review |
| Knowledge Object | supersededBy | Knowledge Object |
| Knowledge Object | archivedAs | Archive Record |
