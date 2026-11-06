/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        beige: { DEFAULT: '#f5f0e6', dark: '#e8dfcc', line: '#d9cfb8' },
        teal: { DEFAULT: '#1f3a3f', light: '#2f5a61', soft: '#5d7c80' },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"Source Sans 3"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
