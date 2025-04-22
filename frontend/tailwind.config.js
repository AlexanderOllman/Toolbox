/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // NeXTSTEP inspired colors
        primary: {
          50: '#e6f1ff',
          100: '#c7d9f2',
          200: '#9cb3e6',
          300: '#748dd9',
          400: '#4a67cc',
          500: '#3548b3', // Primary blue
          600: '#283a99',
          700: '#1c2c80',
          800: '#111e66',
          900: '#07104d',
          950: '#030a33',
        },
        nextstep: {
          background: '#1a1a1a',
          card: '#242424',
          border: '#333333',
          accent: '#3548b3',
          text: {
            primary: '#ffffff',
            secondary: '#b0b0b0',
            muted: '#808080',
          },
          button: {
            bg: '#3548b3',
            hover: '#283a99',
            text: '#ffffff',
          },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'nextstep-gradient': 'linear-gradient(to bottom, #242424, #1a1a1a)',
      },
      boxShadow: {
        'nextstep': '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2)',
        'nextstep-lg': '0 4px 6px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.3)',
        'nextstep-xl': '0 10px 15px rgba(0, 0, 0, 0.5), 0 4px 6px rgba(0, 0, 0, 0.4)',
      },
      fontFamily: {
        sans: ['Inter', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
} 