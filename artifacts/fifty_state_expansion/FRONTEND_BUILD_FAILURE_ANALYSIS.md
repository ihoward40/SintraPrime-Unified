# Frontend Build Failure Analysis

Date: 2026-08-03
Scope: Phase 2B frontend dependency repair before adding new jurisdiction pages.

## Symptom

`npm run build` in `web/` failed during Vite production bundling while resolving Babel runtime helpers imported through `react-transition-group`:

```text
[vite]: Rollup failed to resolve import "@babel/runtime/helpers/esm/objectWithoutPropertiesLoose"
```

After adding `@babel/runtime@7.29.7`, the next missing import was:

```text
@babel/runtime/helpers/esm/extends
```

## Package Graph

Observed package graph before repair:

```text
sintraprime-unified-web@1.0.0
`-- recharts@2.15.4
  `-- react-smooth@4.0.4
    `-- react-transition-group@4.4.5
      +-- @babel/runtime@7.29.7
      `-- dom-helpers@5.2.1
        `-- @babel/runtime@7.29.7 deduped
```

`react-transition-group@4.4.5` declares `@babel/runtime` as a dependency and its ESM build imports helpers from `@babel/runtime/helpers/esm/*`.

## Root Cause

The installed/locked runtime version did not provide the legacy `helpers/esm` directory on disk even though `react-transition-group` imports that layout. The failure was not caused by React, Vite, or the UI framework. It was a dependency-resolution/content-layout mismatch in the transitive `@babel/runtime` package used by `react-transition-group`.

Observed checks:

| Check | Result |
|---|---|
| `react-transition-group` version | `4.4.5` |
| Declared dependency | `@babel/runtime: ^7.5.5` |
| Initial resolved runtime | `7.29.7` |
| `web/node_modules/@babel/runtime/helpers/esm/objectWithoutPropertiesLoose.js` at `7.29.7` | missing |
| `web/node_modules/@babel/runtime/helpers/esm/extends.js` at `7.29.7` | missing |

## Commands Attempted

| Command | Result |
|---|---|
| `npm ls @babel/runtime react-transition-group` | Confirmed chain through `recharts -> react-smooth -> react-transition-group` and runtime `7.29.7` |
| `npm install @babel/runtime@7.29.7 --save` | Added direct dependency but helper files remained absent |
| `npm install @babel/runtime@7.29.7 --save --force` | Re-extracted package, helper files remained absent |
| `npm install @babel/runtime@7.24.8 --save-exact` | Restored `helpers/esm` files required by `react-transition-group` |
| `npm run type-check` | PASS |
| `npm run build` | PASS |

## Minimal Repair

Added a narrow direct dependency in `web/package.json`:

```json
"@babel/runtime": "7.24.8"
```

This pins the runtime helper layout used by `react-transition-group@4.4.5` without upgrading React, Vite, Recharts, or the UI framework.

## Regression Risk

Low to moderate. The pin is narrow and compatible with `react-transition-group`'s declared `^7.5.5` runtime range. It avoids bundler externalization and preserves production bundling. The main risk is that future dependency upgrades may remove the need for this pin; at that point it can be revisited with a normal frontend dependency update.

## Final Build Result

- `npm run type-check`: PASS (`tsc --noEmit`)
- `npm run build`: PASS (`2934 modules transformed`, Vite built `dist/` successfully)
