/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.{js,jsx,ts,tsx}', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
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
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
