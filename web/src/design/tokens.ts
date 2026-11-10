/**
 * SintraPrime design tokens — code mirror of web/DESIGN.md §3–§5.
 *
 * Use these values (or the Tailwind classes they map to) instead of
 * hardcoding colors, fonts, or radii in components. `design-audit.mjs`
 * treats hex literals outside this set as violations.
 *
 * Pattern (design tokens as a codified, auditable source of truth) inspired
 * by pbakaus/impeccable (Apache-2.0). Values are original to SintraPrime.
 */

export const tokens = {
  color: {
    gold: {
      50: '#fefce8',
      100: '#fef9c3',
      200: '#fef08a',
      300: '#fde047',
      400: '#facc15',
      500: '#D4AF37',
      600: '#b8860b',
      700: '#92670a',
      800: '#713f12',
      900: '#422006',
      DEFAULT: '#D4AF37',
    },
    goldLight: '#F5D87A',
    navy: {
      50: '#f0f4ff',
      100: '#e0e9ff',
      200: '#c7d7fe',
      300: '#a5b8fc',
      400: '#818cf8',
      500: '#6366f1',
      600: '#1e3a5f',
      700: '#162c4a',
      800: '#0F172A',
      900: '#0a1628',
      950: '#020617',
      DEFAULT: '#0F172A',
    },
    /** Semantic signal colors — status is never color-only; pair with icon + label. */
    signal: {
      success: '#34D399',
      danger: '#FB7185',
      warning: '#FBBF24',
      info: '#60A5FA',
    },
    ink: {
      primary: '#F8FAFC',
      secondary: '#94A3B8',
      muted: '#64748B',
    },
  },
  font: {
    sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
    mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
    serif: ['Playfair Display', 'Georgia', 'serif'],
  },
  radius: {
    xl: '1rem',
    '2xl': '1.5rem',
    '3xl': '2rem',
  },
  /** Tailwind class names for the canonical component classes in index.css. */
  component: {
    card: 'glass-card',
    cardGold: 'glass-card-gold',
    btnPrimary: 'btn-gold',
    btnSecondary: 'btn-outline',
    input: 'input-dark',
    table: 'table-dark',
    navItem: 'nav-item',
    badge: {
      base: 'badge',
      gold: 'badge-gold',
      success: 'badge-green',
      danger: 'badge-red',
      info: 'badge-blue',
      warning: 'badge-amber',
    },
  },
  /** Minimum interactive target size (px). */
  minTouchTarget: 44,
} as const;

export type Tokens = typeof tokens;
