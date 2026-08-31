# Rule Engine

`RuleEvaluationEngine` selects rules by jurisdiction, domain, topic, and `as_of_date`.

Required behavior implemented:

- Future-effective rules are ignored before their effective date.
- Rules with `effective_to` are unavailable after that date but remain historically queryable.
- Superseded rules are unavailable once the superseding rule is active.
- Missing effective dates return `HUMAN_REVIEW_REQUIRED` without selecting a conclusion.
- Overlapping active rules return `CONFLICTING_AUTHORITY`; the engine does not average outcomes.
- Responses include selected rule, candidate rule IDs, authorities, limitations, verification status, human-review state, and explanation.

The engine is read-only in Phase 1 and backed by JSON under `data/jurisdictions/`.
