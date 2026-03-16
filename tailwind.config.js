/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: '#080c14',
        surface: '#0d1424',
        card: '#111827',
        border: '#1e2d4a',
        accent: '#00d4ff',
        safe: '#00ff88',
        warning: '#ff9500',
        danger: '#ff3b5c',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}