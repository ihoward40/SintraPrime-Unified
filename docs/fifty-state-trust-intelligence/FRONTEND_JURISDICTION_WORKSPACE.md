# Frontend Jurisdiction Workspace

Phase 2A adds a New Jersey jurisdiction workspace at:

```text
/jurisdictions/new-jersey
```

The route is registered in `web/src/App.tsx` and linked from the sidebar as `New Jersey Pilot`.

## Views

The workspace includes:

- coverage overview;
- rule explorer with domain, effective-date, verification, human-review, and text filters;
- authority viewer with source classification, citation, effective date, linked rules, source limitations, and source link;
- gated review queue panel for pending rules, conflicts, stale authorities, and challenges.

## Warning

The page displays:

```text
Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.
```

## Accessibility and Responsiveness

The workspace uses semantic headings, labeled filters, keyboard-focus styles, text labels in addition to color-coded status badges, responsive grids, empty states, and explicit error/fallback state messaging.

## API Behavior

The page attempts to read Phase 2A jurisdiction endpoints. If the API is unavailable in a frontend-only session, it displays static pilot fallback data with the same warnings and non-production posture.
