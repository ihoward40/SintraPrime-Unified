# Federal Authority Model

Federal authority types are explicit in `legal_authority/constants.py`: `US_CONSTITUTION`, `FEDERAL_STATUTE`, `FEDERAL_REGULATION`, `BINDING_FEDERAL_APPELLATE_DECISION`, `FEDERAL_RULE_OF_CIVIL_PROCEDURE`, and `FEDERAL_RULE_OF_EVIDENCE`, alongside official guidance and secondary or locator classifications.

Authority weight never replaces authority type. Statutes, regulations, court rules, and guidance remain distinguishable in API and dataset records. Federal rules reference one or more federal authority IDs; citation-free rules are rejected by the existing Pydantic model.

State inheritance is documented as a future resolution concern: applicable federal authority, state constitution, state statute, state regulation, state administrative guidance, then local rule, subject to preemption, conflict, effective-date, and factual analysis. Phase 2C-1 does not implement inheritance resolution.