# Legal Authority Model

The Phase 1 model preserves both source classification and authority type.

Core records:

- `LegalAuthority`: normalized source record with citation, issuing body, source URL/document ID, dates, verification state, authority type, authority weight, summary, limitations, tags, and hashes.
- `JurisdictionRule`: normalized rule with jurisdiction, domain, topic, rule logic, authority links, effective dates, conflict links, supersession links, confidence, status, and review gate.
- `ProfessionalReview`: review record for a rule or authority. No New Jersey rule has professional approval in Phase 1.
- `ConflictRecord`: unresolved competing authority/rule workflow.

Authority hierarchy is explicit in `legal_authority/constants.py`. A numerical weight is stored only alongside the controlling authority type and must match that type.

Allowed source classifications include `PRIMARY_LEGAL_AUTHORITY`, `OFFICIAL_FORM`, `OFFICIAL_GUIDANCE`, `COURT_DECISION`, `SECONDARY_LEGAL_SOURCE`, `PROFESSIONAL_STANDARD`, `CLIENT_DOCUMENT`, `EDUCATIONAL_MATERIAL`, `PRIVATE_TEMPLATE`, `UNVERIFIED_PRIVATE_LAW_CLAIM`, and `UNKNOWN`.
