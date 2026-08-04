# Northeast Comparison

Phase 2B adds a comparison service and frontend workspace for New Jersey, New York, and Pennsylvania.

## Supported API

`GET /legal-rules/compare?jurisdictions=NJ,NY,PA&domain={domain}&topic={topic}` returns side-by-side rule rows with authority records, effective dates, exceptions, confidence, review status, conflict warnings, missing data, and source limitations.

The legacy single-jurisdiction compare mode remains available through `jurisdiction`, `domain`, and `topic` parameters.

## Required Warning

Every comparison response includes:

```text
Applicable law depends on governing-law rules, trust situs, administration, party contacts, asset location, public policy, and other facts. A favorable rule in another jurisdiction may not govern the matter.
```

## Boundaries

- The service does not rank states as better or safer.
- Missing rules are reported as missing rather than inferred from another jurisdiction.
- Human-review and source-limit warnings remain visible.
- Conflicting authority is not averaged.
