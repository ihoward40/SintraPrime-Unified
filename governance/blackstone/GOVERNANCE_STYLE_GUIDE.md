# Blackstone Governance Library — Style Guide

## Normative Language

Use the following keywords consistently. Definitions are derived from RFC 2119.

| Keyword | Meaning |
|---------|---------|
| MUST | An absolute requirement |
| MUST NOT | An absolute prohibition |
| SHALL | Synonym for MUST (used in formal provisions) |
| SHALL NOT | Synonym for MUST NOT |
| SHOULD | Strongly recommended; deviations require justification |
| SHOULD NOT | Strongly discouraged |
| MAY | Permitted but not required |
| RECOMMENDED | Synonym for SHOULD |
| OPTIONAL | Synonym for MAY |

## Document Structure

Every volume MUST contain:

- A top-level file named after the volume abbreviation (e.g., `BKGC.md`).
- A `CHANGELOG.md`.
- A clear dependency statement in the preamble.
- Version number in `MAJOR.MINOR.PATCH` format.
- Effective date.

## Article Numbering

- Use decimal section numbering: `1`, `1.1`, `1.1.1`.
- Use `§` for cross-references: `§ 3.2`.
- Preserve numbering across revisions. Deleted sections are marked `[reserved]`.

## Cross-References

When a downstream document relies on an upstream document, cite it explicitly:

```text
Derived from: BKGC Article III § 3.2
Governed by: BGS 4.1
Implements: BKC Knowledge Object 2.1
Certified by: BCCM Test Case 7.3
```

## Citation Conventions

- Cite sources by stable identifier when available.
- Include retrieval date for online sources.
- Mark AI-generated summaries as derivative works requiring independent verification.
- Do not fabricate citations, page numbers, or quotations.

## Metadata Fields

Every normative file SHOULD include this header:

```yaml
---
version: 1.0.0
effective_date: YYYY-MM-DD
status: active | draft | deprecated
supersedes: []
derived_from: []
---
```

## Terminology

- Define technical terms on first use in each volume, or reference the Blackstone Knowledge Registry.
- Use the same term consistently across volumes. Do not introduce synonyms without a CDR.

## Diagrams

- Prefer plain-text diagrams using ASCII or Mermaid.
- Store diagram source in `DIAGRAMS/` and render output alongside it.
- Diagrams MUST be versioned with the document they illustrate.

## Glossary Rules

- Terms defined in `volume-6-bkr/GLOSSARY/` take precedence.
- A local volume glossary may exist but must reference the master glossary.
- Definitions are normative; changing a definition requires a CDR.

## Change Logging

- `CHANGELOG.md` records every revision.
- Entries include: version, date, author, summary, CDR reference if applicable.
- Major changes require a CDR; minor changes require a changelog entry only.

## Prose Style

- Use declarative sentences.
- Avoid marketing language.
- Avoid unnecessary adjectives.
- Prefer "the ecosystem" or "the system" over anthropomorphized agent names in normative text.
- Use active voice in requirements; passive voice is permitted in definitions.
