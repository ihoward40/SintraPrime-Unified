# SintraPrime Visual System (DESIGN.md)

> **Durable design truth for the SintraPrime web app.** This document is the
> single source of visual truth. When an AI agent generates or edits UI, it must
> follow this file first and improvise last. If the UI drifts from this file,
> fix the UI — not the file — unless the owner approves a change.
>
> Structural pattern inspired by
> [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0):
> durable design-truth docs + codified tokens + deterministic quality rules for
> AI-generated frontends. See the Attribution footer at the end.

**Status:** v1.0 · 2026-10-06 · applies to `web/` (Vite + React 18 + Tailwind CSS 3)

---

## 1. Product posture

SintraPrime is a legal/financial automation command center. The UI must feel
like a **mission-control console**: dark, precise, calm under pressure. Every
screen answers three questions in order:

1. *What is the current state?* (status, health, balances)
2. *What needs my decision?* (approvals, alerts, blocked items)
3. *What did the system do?* (evidence, receipts, audit trail)

The `mc-*` component classes in `web/src/index.css` (mission-control masthead,
statusbar, metrics, systems rows) are the canonical layout language for
operational surfaces. New operational pages follow the same shell.

## 2. Design principles

1. **Dark is the default.** The app is dark-first and dark-only. Never ship a
   light-mode variant unless the owner approves it.
2. **Gold means authority.** The gold accent (`#D4AF37`) is reserved for primary
   actions, active navigation, verified state, and brand moments. Do not use it
   decoratively on every element — restraint is what makes it read as premium.
3. **One screen, one job.** A page does one thing. Related detail goes in
   sub-navigation (`mc-subnav`) or drill-down routes, not in a second column of
   unrelated widgets.
4. **State before chrome.** Status indicators, timestamps, and provenance
   ("verified", "unknown", source system) outrank decorative flourishes.
5. **Deterministic over clever.** Prefer the token values below and the existing
   component classes. Novel one-off styling is a bug, not creativity.
6. **Professional-review framing.** This is a legal/financial platform whose
   outputs are **for professional review** — never present AI output as
   licensed professional advice (see `web/PRODUCT.md`).

## 3. Color tokens

| Token | Value | Usage |
|---|---|---|
| `gold.DEFAULT` | `#D4AF37` | Primary accent, active nav, verified highlights, CTAs |
| `gold.light` | `#F5D87A` | Gradient highlight end, hover states |
| `navy.DEFAULT` | `#0F172A` | App background, card base |
| `navy.600` | `#1E3A5F` | Secondary surfaces, gradient end |
| `navy.950` | `#020617` | Deepest background (page chrome) |
| `signal.success` | `#34D399` | Healthy / verified / connected |
| `signal.danger` | `#FB7185` | Errors / offline / destructive |
| `signal.warning` | `#FBBF24` | Degraded / pending / caution |
| `signal.info` | `#60A5FA` | Informational / neutral-highlight |
| `ink.primary` | `#F8FAFC` (slate-50-ish) | Primary text |
| `ink.secondary` | `#94A3B8` (slate-400) | Secondary text |
| `ink.muted` | `#64748B` (slate-500) | Muted text, timestamps |

Full gold and navy ramps (50–950) live in `tailwind.config.ts`; the table above
lists the semantic anchors. **Rules:**

- Never hardcode a hex color in a component. Use the tokens (`bg-gold`,
  `text-gold`, `signal.*`) or the CSS variables (`--gold`, `--navy`) defined in
  `index.css`.
- Status color is never the only signal: pair every color-coded state with an
  icon and/or text label (see Accessibility, §8).
- Destructive actions use `signal.danger` and require explicit confirmation.

## 4. Typography

| Role | Token | Stack |
|---|---|---|
| UI text | `font-sans` | Inter, system-ui, -apple-system, sans-serif |
| Data / code | `font-mono` | "JetBrains Mono", "Fira Code", monospace |
| Brand display | `font-serif` | "Playfair Display", Georgia, serif |

**Scale (Tailwind defaults + display):**

- Page title: `text-3xl md:text-4xl font-black tracking-tight` (`mc-masthead h1`)
- Section title: `text-xl font-bold`
- Eyebrow label: `text-[10px] font-bold tracking-[0.22em] uppercase text-gold` (`mc-eyebrow`)
- Body: `text-sm` slate-300/400; captions: `text-xs` slate-500
- Numeric data: `font-variant-numeric: tabular-nums` (`mc-shell`)

**Rules:**

- Eyebrow labels are the wayfinding device: uppercase, letterspaced, gold.
- Numbers that users compare (balances, counts, metrics) always use tabular
  numerals.
- Never use more than two font families on one screen.

## 5. Spacing & layout

- Base unit: `4px` (Tailwind default scale). Page gutters: `p-5 md:p-6`.
- Section rhythm: `space-y-5` / `space-y-6` on the page shell (`mc-shell`).
- Cards: `rounded-2xl` (`1rem`), padding `p-4`–`p-6`.
- Status bars and command strips: `border border-slate-800` on navy surfaces.
- Max content width for reading surfaces: `max-w-5xl`; dashboards are full-bleed
  with gutters.
- Touch targets: minimum `44px` (`min-h-11`) for interactive controls.

## 6. Component rules

Canonical classes live in `web/src/index.css` (`@layer components`). Reuse them;
do not re-implement.

| Component | Class | Notes |
|---|---|---|
| Card | `.glass-card` / `.glass-card-gold` | Glassmorphism, gold variant for featured |
| Primary button | `.btn-gold` | Gold gradient, dark text, `active:scale-95` |
| Secondary button | `.btn-outline` | Gold border, transparent |
| Input | `.input-dark` | Dark field, gold focus ring |
| Badge | `.badge-*` | gold / green / red / blue / amber variants |
| Table | `.table-dark` | Uppercase small header, hover rows |
| Nav item | `.nav-item` (+ `.active`) | Sidebar; active = gold tint + gold left border |
| Page shell | `.mc-shell` | Page spacing + tabular numbers |
| Masthead | `.mc-masthead` | Title + description + eyebrow |
| Status bar | `.mc-statusbar` | System health strip with `.live`/`.degraded`/`.offline` |
| Metrics grid | `.mc-metrics` / `.mc-metric` | Stat tiles with `.mc-source` provenance |
| Empty state | `.mc-empty-state` | Dashed border, centered, icon + heading + help |

**Rules:**

- New components follow the existing naming pattern (`glass-*`, `btn-*`,
  `badge-*`, `mc-*`).
- Buttons always have a visible label; icon-only buttons get `aria-label`.
- Loading states use `.shimmer`, never layout-shifting spinners on first paint
  where avoidable.
- Motion: `transition-all duration-200` standard; keyframes `pulse-gold`,
  `shimmer`, `float`, `slide-in`, `fade-up` exist in the config. Respect
  `prefers-reduced-motion` (already enforced globally in `index.css`).

## 7. Imagery & iconography

- Icons: `lucide-react` only. One icon set, one stroke style.
- No emoji as UI icons.
- Decorative backgrounds: `.bg-grid` / `.bg-dots` utilities or the
  `glow-gold` radial. Never a photographic hero on operational screens.

## 8. Accessibility baseline

- Contrast: body text on navy must meet WCAG AA (4.5:1). Gold `#D4AF37` on
  `#0F172A` passes for large/bold text; use `gold.light` or white for small
  body text on dark surfaces where in doubt.
- Every `<img>` has a meaningful `alt`; decorative images use `alt=""`.
- Focus is always visible: `focus-visible:ring-2 focus-visible:ring-gold`.
- Status is never color-only: pair with icon + text (e.g. `.mc-source.verified`
  shows a check icon and the word "verified").
- Keyboard: all interactive elements reachable and operable; dialogs trap focus
  (Radix primitives handle this — use them).
- Motion: `prefers-reduced-motion` disables animation globally (see
  `index.css`).

## 9. Quality gates

- `npm run design:audit` (see `web/scripts/design-audit.mjs`) runs the
  deterministic UI checks: no hardcoded hex outside tokens, no missing `alt`,
  no inline `style=` in components. It must pass before a UI change is
  considered done.
- `web/src/design/CHECKLIST.md` is the per-component review checklist.

---

## Attribution

Design-truth pattern (durable `DESIGN.md`/`PRODUCT.md` + design tokens +
deterministic quality rules for AI-generated frontends) adapted from
[pbakaus/impeccable](https://github.com/pbakaus/impeccable), © the impeccable
authors, licensed under the Apache License 2.0. This file's content is original
to SintraPrime; only the pattern is adapted.
