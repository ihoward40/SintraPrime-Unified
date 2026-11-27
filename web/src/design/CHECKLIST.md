# Component Checklist

> Per-component review checklist. Run through this list before shipping a new
> or changed UI component. Companion to `web/DESIGN.md` (system rules) and
> `web/scripts/design-audit.mjs` (automated checks — the automatable items
> below are marked `[auto]`).

## Tokens & styling

- [ ] [auto] No hardcoded hex colors — all color comes from Tailwind theme
      tokens (`bg-gold`, `text-gold`, `signal.*`) or `web/src/design/tokens.ts`.
- [ ] [auto] No inline `style={...}` / `style="..."` in components (exception:
      dynamic values that cannot be expressed in Tailwind, documented inline).
- [ ] No new one-off CSS classes when an existing `index.css` component class
      (`.glass-card`, `.btn-gold`, `.input-dark`, `.badge-*`, `.mc-*`) applies.
- [ ] New classes follow the naming pattern (`glass-*`, `btn-*`, `badge-*`,
      `mc-*`) and live in `@layer components` in `index.css`.

## Layout & hierarchy

- [ ] One screen, one job — the page answers state → decision → evidence, in
      that order.
- [ ] Operational pages use the mission-control shell (`.mc-shell`,
      `.mc-masthead`, eyebrow label) or justify the deviation.
- [ ] Spacing follows the 4px base scale; page gutters `p-5 md:p-6`.
- [ ] Interactive targets are at least 44px (`min-h-11`).

## Typography & copy

- [ ] At most two font families on the screen (`font-sans` UI, `font-mono`
      data/code, `font-serif` brand display only).
- [ ] Comparable numbers use tabular numerals (`mc-shell`).
- [ ] Copy follows `PRODUCT.md` voice: direct, evidence-first, no certainty
      manufactured. Unknowns labeled unknown.
- [ ] Buttons name their consequence ("Approve $75 payment", not "Submit").
- [ ] AI-generated content is labeled as draft / for professional review —
      never presented as licensed professional advice.

## State & feedback

- [ ] Every async flow has loading (`.shimmer`), success, and error states.
- [ ] Status is never color-only — icon + text label alongside the color.
- [ ] Errors explain and offer a next step ("Sync failed — retry").
- [ ] Destructive actions use `signal.danger` and require explicit confirmation.

## Accessibility

- [ ] [auto] Every `<img>` has a meaningful `alt` (decorative → `alt=""`).
- [ ] Focus is visible (`focus-visible:ring-2 focus-visible:ring-gold`).
- [ ] Icon-only buttons have `aria-label`.
- [ ] Contrast meets WCAG AA (4.5:1) for body text on dark surfaces.
- [ ] Keyboard operable; dialogs trap focus (prefer Radix primitives).
- [ ] Respects `prefers-reduced-motion` (no unguarded animation).

## Evidence & safety (PRODUCT.md hard constraints)

- [ ] No external action (payment, filing, submission, outbound message)
      executes without an explicit operator approval step.
- [ ] AI content shows provenance (model, inputs, generation time).
- [ ] No secrets, keys, or credential values rendered or logged.
- [ ] No dark patterns: no pre-checked consent, no disguised upsells, no
      manufactured urgency on approvals.
