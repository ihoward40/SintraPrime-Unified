export const Colors = {
  // Primary palette
  navy: {
    50: '#E8EBF0',
    100: '#C5CDD9',
    200: '#9EAEC0',
    300: '#778FA6',
    400: '#587893',
    500: '#3A607F',
    600: '#2C4D6B',
    700: '#1E3A56',
    800: '#152B43',
    900: '#0F172A',
    950: '#070D18',
  },
  gold: {
    50: '#FDF8E7',
    100: '#FAEFC3',
    200: '#F5E48E',
    300: '#EED659',
    400: '#E5C736',
    500: '#D4AF37',
    600: '#B8952A',
    700: '#9A7A1F',
    800: '#7C6017',
    900: '#5E4810',
  },

  // Semantic colors
  background: '#0F172A',
  backgroundSecondary: '#152B43',
  backgroundTertiary: '#1E3A56',
  surface: '#152B43',
  surfaceElevated: '#1E3A56',

  // Text
  textPrimary: '#FFFFFF',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  textGold: '#D4AF37',

  // Accents
  accent: '#D4AF37',
  accentLight: '#E5C736',
  accentDark: '#B8952A',

  // Status
  success: '#22C55E',
  successLight: '#86EFAC',
  warning: '#F59E0B',
  warningLight: '#FCD34D',
  error: '#EF4444',
  errorLight: '#FCA5A5',
  info: '#3B82F6',
  infoLight: '#93C5FD',

  // Borders
  border: '#1E3A56',
  borderLight: '#2C4D6B',

  // Overlays
  overlay: 'rgba(15, 23, 42, 0.8)',
  overlayLight: 'rgba(15, 23, 42, 0.5)',

  // Special
  cardGlow: 'rgba(212, 175, 55, 0.15)',
  goldGlow: 'rgba(212, 175, 55, 0.3)',

  // Gradients (as arrays for LinearGradient)
  gradientNavy: ['#0F172A', '#152B43'] as string[],
  gradientGold: ['#D4AF37', '#B8952A'] as string[],
  gradientCard: ['#152B43', '#1E3A56'] as string[],
  gradientHero: ['#070D18', '#0F172A', '#152B43'] as string[],
} as const;

export type ColorKey = keyof typeof Colors;
